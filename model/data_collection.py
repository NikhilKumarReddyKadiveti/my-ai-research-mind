import requests
import json
import os

def fetch_wikipedia_data(topics, save_path="researchmind-ai/model/data/raw_data.txt"):
    """
    Fetch text content from Wikipedia for a list of topics.
    """
    print(f"Fetching data for {len(topics)} topics...")
    all_text = ""
    
    for topic in topics:
        url = f"https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "titles": topic,
            "prop": "extracts",
            "explaintext": True,
        }
        
        try:
            headers = {
                "User-Agent": "ResearchMindAI/1.0 (contact: user@example.com)"
            }
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                extract = page_data.get("extract", "")
                if extract:
                    all_text += extract + "\n\n"
                    print(f"Successfully fetched: {topic}")
        except Exception as e:
            print(f"Error fetching {topic}: {e}")
            
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(all_text)
    print(f"Raw data saved to {save_path}")

if __name__ == "__main__":
    educational_topics = [
        "Artificial intelligence", "Machine learning", "Transformer (deep learning architecture)",
        "Neural network", "Python (programming language)", "History of science",
        "Mathematics", "Physics", "Philosophy", "Computer science"
    ]
    fetch_wikipedia_data(educational_topics)
