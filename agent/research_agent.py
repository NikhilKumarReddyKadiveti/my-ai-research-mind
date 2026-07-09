import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urlparse

class ResearchAgent:
    """
    ResearchMind Research Agent.
    Capabilities:
    - Web Search (DuckDuckGo)
    - Webpage Scraping
    - Content Summarization (simplified for now)
    - Source ranking and citation generation
    """
    def __init__(self, max_results=5):
        self.max_results = max_results
        self.ddgs = None
        self.blocked_domains = {
            "roblox.com",
            "store.steampowered.com",
            "epicgames.com",
            "play.google.com",
            "apps.apple.com",
            "xbox.com",
            "playstation.com",
            "nintendo.com",
            "itch.io",
        }
        self.learning_domains = {
            "coursera.org",
            "edx.org",
            "kaggle.com",
            "freecodecamp.org",
            "fast.ai",
            "deeplearning.ai",
            "developers.google.com",
            "learn.microsoft.com",
            "github.com",
            "huggingface.co",
            "pytorch.org",
            "tensorflow.org",
            "w3schools.com",
            "geeksforgeeks.org",
            "realpython.com",
            "python.org",
            "youtube.com",
        }

    def search(self, query):
        """Search the web for a given query."""
        query = self._normalize_learning_query(query)
        print(f"Searching for: {query}")
        results = []
        try:
            if self.ddgs is None:
                from duckduckgo_search import DDGS

                try:
                    self.ddgs = DDGS(timeout=8)
                except TypeError:
                    self.ddgs = DDGS()
            ddg_results = self.ddgs.text(query, max_results=max(self.max_results, 8))
            for r in ddg_results:
                result = {
                    "title": r['title'],
                    "link": r['href'],
                    "snippet": r['body']
                }
                if self._is_relevant_result(query, result):
                    results.append(result)
                if len(results) >= self.max_results:
                    break
        except Exception as e:
            print(f"Error during search: {e}")
        if not results:
            results = self._search_duckduckgo_html(query)
        if not results:
            results = self._curated_learning_results(query)
        return results[: self.max_results]

    def _search_duckduckgo_html(self, query):
        results = []
        try:
            response = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                timeout=8,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
                    )
                },
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for item in soup.select(".result")[: self.max_results * 3]:
                link = item.select_one(".result__a")
                snippet = item.select_one(".result__snippet")
                if not link:
                    continue
                result = {
                    "title": link.get_text(" ", strip=True),
                    "link": link.get("href", ""),
                    "snippet": snippet.get_text(" ", strip=True) if snippet else "",
                }
                if self._is_relevant_result(query, result):
                    results.append(result)
                if len(results) >= self.max_results:
                    break
        except Exception as exc:
            print(f"HTML search fallback failed: {exc}")
        return results

    def _normalize_learning_query(self, query):
        clean = " ".join((query or "").split())
        clean = re.sub(
            r"^(research|find|search|look up|give me|show me)\s+",
            "",
            clean,
            flags=re.IGNORECASE,
        )
        clean = re.sub(
            r"\b(and\s+)?(give|include|show)\s+(me\s+)?(source\s+links|sources|links)\b\.?",
            "",
            clean,
            flags=re.IGNORECASE,
        )
        clean = re.sub(r"\s+", " ", clean).strip(" .,:;-")
        lowered = clean.lower()
        if any(word in lowered for word in ["learn", "tutorial", "course", "resource", "beginner"]):
            return f"{clean} free course tutorial beginner educational"
        return f"{clean} free learning resources tutorial course beginner educational"

    def _is_relevant_result(self, query, result):
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        url = result.get("link", "")
        host = urlparse(url).netloc.lower().removeprefix("www.")
        text = f"{title} {snippet} {url}".lower()

        if any(host == domain or host.endswith(f".{domain}") for domain in self.blocked_domains):
            return False

        junk_words = ["game", "gaming", "play now", "download game", "apk", "casino", "betting"]
        if any(word in text for word in junk_words) and not any(word in text for word in ["course", "learn", "tutorial"]):
            return False

        query_terms = [
            term
            for term in re.findall(r"[a-zA-Z0-9+#.]+", query.lower())
            if (len(term) > 2 or term in {"ai", "ml", "c#", "c++"})
            and term not in {"research", "find", "search", "give", "show", "source", "sources", "links", "free", "best", "resources", "resource", "learn", "learning", "tutorial", "course", "educational"}
        ]
        has_topic_match = not query_terms or any(term in text for term in query_terms)
        has_learning_signal = any(word in text for word in ["learn", "course", "tutorial", "guide", "lesson", "documentation", "docs", "training", "education"])
        trusted_learning_site = any(host == domain or host.endswith(f".{domain}") for domain in self.learning_domains)
        return has_topic_match and (has_learning_signal or trusted_learning_site)

    def _curated_learning_results(self, query):
        text = query.lower()
        if "python" in text and ("data science" in text or "data" in text):
            return [
                {
                    "title": "Kaggle Learn: Python",
                    "link": "https://www.kaggle.com/learn/python",
                    "snippet": "Free hands-on Python lessons for data science beginners.",
                    "curated": True,
                },
                {
                    "title": "Kaggle Learn: Pandas",
                    "link": "https://www.kaggle.com/learn/pandas",
                    "snippet": "Free practical lessons for working with tables and datasets in Python.",
                    "curated": True,
                },
                {
                    "title": "freeCodeCamp: Data Analysis with Python",
                    "link": "https://www.freecodecamp.org/learn/data-analysis-with-python/",
                    "snippet": "Free structured course with projects for Python data analysis.",
                    "curated": True,
                },
            ]

        if "ai" in text or "artificial intelligence" in text or "machine learning" in text:
            return [
                {
                    "title": "Google Machine Learning Crash Course",
                    "link": "https://developers.google.com/machine-learning/crash-course",
                    "snippet": "Free beginner-friendly machine learning course from Google.",
                    "curated": True,
                },
                {
                    "title": "Kaggle Learn: Intro to Machine Learning",
                    "link": "https://www.kaggle.com/learn/intro-to-machine-learning",
                    "snippet": "Free hands-on machine learning lessons for beginners.",
                    "curated": True,
                },
                {
                    "title": "fast.ai: Practical Deep Learning",
                    "link": "https://course.fast.ai/",
                    "snippet": "Free practical deep learning course with notebooks and examples.",
                    "curated": True,
                },
                {
                    "title": "Hugging Face Learn",
                    "link": "https://huggingface.co/learn",
                    "snippet": "Free AI, NLP, and transformer learning material.",
                    "curated": True,
                },
                {
                    "title": "Elements of AI",
                    "link": "https://www.elementsofai.com/",
                    "snippet": "Free beginner-friendly AI course that explains concepts without heavy math.",
                    "curated": True,
                },
            ]

        return []

    def scrape(self, url):
        """Extract text content from a webpage."""
        print(f"Scraping: {url}")
        try:
            response = requests.get(url, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                
                text = soup.get_text()
                
                # Break into lines and remove leading/trailing whitespace
                lines = (line.strip() for line in text.splitlines())
                # Break multi-headlines into a line each
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                # Drop blank lines
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                # Return first 2000 characters for now to keep it manageable
                return text[:1400]
            else:
                return f"Failed to scrape. Status code: {response.status_code}"
        except Exception as e:
            return f"Error during scraping: {e}"

    def research_topic(self, topic):
        """Perform a full research cycle on a topic."""
        print(f"Starting research on: {topic}")
        search_results = self.search(topic)
        
        full_report = {
            "topic": topic,
            "sources": [],
            "combined_content": ""
        }
        
        for i, res in enumerate(search_results):
            content = res.get("snippet", "") if res.get("curated") else self.scrape(res['link'])
            source_info = {
                "id": i + 1,
                "title": res['title'],
                "url": res['link'],
                "content": content
            }
            full_report["sources"].append(source_info)
            full_report["combined_content"] += f"\n--- Source {i+1}: {res['title']} ---\n{content}\n"
            
            if not res.get("curated") and i >= 1: # Limit live scraping to top 2 for speed in website tests
                break
                
        return full_report

if __name__ == "__main__":
    # Quick test
    agent = ResearchAgent(max_results=3)
    # result = agent.search("latest news about AI models")
    # print(json.dumps(result, indent=2))
    
    report = agent.research_topic("How to build a transformer from scratch in PyTorch")
    with open("research_report_test.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Research complete. Report saved.")
