import re

def clean_text(input_path, output_path):
    """
    Clean and normalize raw text for training.
    """
    print("Cleaning text...")
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()
        
    # Remove references like [1], [2], etc.
    text = re.sub(r"\[\d+\]", "", text)
    
    # Remove multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Normalize whitespace
    text = re.sub(r" +", " ", text)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Cleaned data saved to {output_path}")

if __name__ == "__main__":
    clean_text("researchmind-ai/model/data/raw_data.txt", "researchmind-ai/model/data/train_data.txt")
