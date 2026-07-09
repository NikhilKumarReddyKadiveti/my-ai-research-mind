import torch
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from model import ResearchMindModel
from tokenizer import BPETokenizer
import os
import time
from pathlib import Path

# Hyperparameters
BATCH_SIZE = 16
BLOCK_SIZE = 128
LEARNING_RATE = 3e-4
MAX_ITERS = int(os.getenv("RESEARCHMIND_MAX_ITERS", "5000"))
EVAL_INTERVAL = 500
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "model" / "data" / "train_data.txt"
CHECKPOINT_DIR = ROOT / "model" / "checkpoints"
TOKENIZER_PATH = CHECKPOINT_DIR / "tokenizer.json"

class TextDataset(Dataset):
    def __init__(self, data_path, tokenizer, block_size):
        with open(data_path, 'r', encoding='utf-8') as f:
            text = f.read()
        self.tokenizer = tokenizer
        self.block_size = block_size
        self.tokens = torch.tensor(tokenizer.encode(text), dtype=torch.long)

    def __len__(self):
        return len(self.tokens) - self.block_size

    def __getitem__(self, idx):
        chunk = self.tokens[idx : idx + self.block_size + 1]
        x = chunk[:-1]
        y = chunk[1:]
        return x, y

def train():
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    # 1. Load Tokenizer
    tokenizer = BPETokenizer(vocab_size=5000)
    if TOKENIZER_PATH.exists():
        tokenizer.load(str(TOKENIZER_PATH))
    else:
        # Pre-train tokenizer on the training data if not exists
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            text = f.read()
        tokenizer.train(text)
        tokenizer.save(str(TOKENIZER_PATH))

    # 2. Prepare Data
    dataset = TextDataset(str(DATA_PATH), tokenizer, BLOCK_SIZE)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    # 3. Initialize Model
    model = ResearchMindModel(vocab_size=len(tokenizer.vocab)).to(DEVICE)
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE)

    # 4. Training Loop
    model.train()
    start_time = time.time()
    
    dataloader_iter = iter(dataloader)
    for step in range(MAX_ITERS):
        try:
            x, y = next(dataloader_iter)
        except:
            # Refresh dataloader if it runs out (though it shouldn't with shuffle=True)
            dataloader_iter = iter(dataloader)
            x, y = next(dataloader_iter)
            
        x, y = x.to(DEVICE), y.to(DEVICE)
        
        logits, loss = model(x, y)
        
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        
        if step % EVAL_INTERVAL == 0:
            end_time = time.time()
            print(f"Iteration {step}: Loss {loss.item():.4f}, Time {end_time - start_time:.2f}s")
            torch.save(model.state_dict(), CHECKPOINT_DIR / f"model_iter_{step}.pt")
            start_time = time.time()

    torch.save(model.state_dict(), CHECKPOINT_DIR / "model_final.pt")
    print("Training complete!")

if __name__ == "__main__":
    # Ensure data exists before training
    if not DATA_PATH.exists():
        print("Data not found. Please run data_collection.py and data_cleaning.py first.")
    else:
        train()
