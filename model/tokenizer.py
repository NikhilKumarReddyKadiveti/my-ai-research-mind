import json
import os
import re
from collections import Counter

class BPETokenizer:
    """
    A custom Byte-Pair Encoding (BPE) tokenizer built from scratch.
    It maps common chunks of characters to unique integers.
    """
    def __init__(self, vocab_size=5000):
        self.vocab_size = vocab_size
        self.vocab = {}  # token -> id
        self.inverse_vocab = {}  # id -> token
        self.merges = {}  # (token1, token2) -> merged_token
        
        # Special tokens
        self.special_tokens = ["<pad>", "<unk>", "<s>", "</s>"]
        for i, token in enumerate(self.special_tokens):
            self.vocab[token] = i
            self.inverse_vocab[i] = token

    def _get_stats(self, ids):
        """Count frequencies of adjacent pairs of tokens."""
        counts = Counter()
        for i in range(len(ids) - 1):
            counts[(ids[i], ids[i+1])] += 1
        return counts

    def _merge(self, ids, pair, new_id):
        """Replace all occurrences of a pair with a new merged token ID."""
        new_ids = []
        i = 0
        while i < len(ids):
            if i < len(ids) - 1 and (ids[i], ids[i+1]) == pair:
                new_ids.append(new_id)
                i += 2
            else:
                new_ids.append(ids[i])
                i += 1
        return new_ids

    def train(self, text):
        """Train the BPE tokenizer on a given text corpus."""
        # Initial vocabulary: individual characters
        # Ensure spaces and common punctuation are included
        flat_tokens = list(text.encode("utf-8"))
        
        # Unique bytes in text
        unique_bytes = sorted(list(set(flat_tokens)))
        for b in unique_bytes:
            char = bytes([b]).decode("utf-8", errors="replace")
            if char not in self.vocab:
                new_id = len(self.vocab)
                self.vocab[char] = new_id
                self.inverse_vocab[new_id] = char
        
        # Map bytes to our vocab IDs
        byte_to_id = {}
        for char, idx in self.vocab.items():
            if len(char) == 1:
                try:
                    b = char.encode("utf-8")
                    if len(b) == 1:
                        byte_to_id[b[0]] = idx
                except:
                    continue

        current_ids = [byte_to_id[b] for b in flat_tokens if b in byte_to_id]
        
        num_merges = self.vocab_size - len(self.vocab)
        for i in range(num_merges):
            stats = self._get_stats(current_ids)
            if not stats:
                break
            
            # Find the most frequent pair
            best_pair = max(stats, key=stats.get)
            new_id = len(self.vocab)
            
            # Create merged token
            t1 = self.inverse_vocab[best_pair[0]]
            t2 = self.inverse_vocab[best_pair[1]]
            merged_token = t1 + t2
            
            self.vocab[merged_token] = new_id
            self.inverse_vocab[new_id] = merged_token
            self.merges[best_pair] = new_id
            
            current_ids = self._merge(current_ids, best_pair, new_id)
            if (i+1) % 100 == 0:
                print(f"Merge {i+1}/{num_merges} completed...")

    def encode(self, text):
        """Encode text into token IDs."""
        # Start with individual characters
        ids = []
        for char in text:
            if char in self.vocab:
                ids.append(self.vocab[char])
            else:
                ids.append(self.vocab["<unk>"])
        
        # Iteratively apply merges
        while len(ids) >= 2:
            stats = self._get_stats(ids)
            # Find the pair in stats that appears in our merges and has the lowest merge rank
            # (In BPE, merges must be applied in the order they were learned)
            pair_to_merge = None
            for pair in self.merges:
                if pair in stats:
                    pair_to_merge = pair
                    break # merges dict is ordered in Python 3.7+
            
            if pair_to_merge is None:
                break
            
            ids = self._merge(ids, pair_to_merge, self.merges[pair_to_merge])
            
        return ids

    def decode(self, ids):
        """Decode token IDs back into text."""
        tokens = [self.inverse_vocab.get(idx, "<unk>") for idx in ids]
        return "".join(tokens)

    def save(self, path):
        """Save vocabulary and merges to a JSON file."""
        data = {
            "vocab": self.vocab,
            "merges": {f"{k[0]},{k[1]}": v for k, v in self.merges.items()}
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path):
        """Load vocabulary and merges from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.vocab = data["vocab"]
        self.inverse_vocab = {int(v): k for k, v in self.vocab.items()}
        self.merges = {tuple(map(int, k.split(","))): v for k, v in data["merges"].items()}

if __name__ == "__main__":
    # Quick test
    sample_text = "ResearchMind AI is learning to speak. This is a scratch-built tokenizer."
    tokenizer = BPETokenizer(vocab_size=300)
    print("Training tokenizer...")
    tokenizer.train(sample_text)
    
    encoded = tokenizer.encode("ResearchMind is AI.")
    print(f"Encoded: {encoded}")
    decoded = tokenizer.decode(encoded)
    print(f"Decoded: {decoded}")
    
    tokenizer.save("researchmind-ai/model/tokenizer_test.json")
    print("Tokenizer saved.")
