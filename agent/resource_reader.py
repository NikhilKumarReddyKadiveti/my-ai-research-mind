import re
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup


class ResourceReader:
    """
    Reads public learning resources from pages, PDFs, and YouTube transcripts.

    The reader returns bounded text so the tutor can summarize quickly without
    storing whole documents or videos by default.
    """

    def __init__(self, timeout: int = 12, max_chars: int = 6000):
        self.timeout = timeout
        self.max_chars = max_chars
        self.headers = {
            "User-Agent": "ResearchMindAI/1.0 educational resource reader"
        }

    def read(self, url: str) -> Dict[str, Optional[str]]:
        resource_type = self.detect_type(url)
        if resource_type == "video":
            return self._read_youtube(url)
        if resource_type == "document":
            return self._read_pdf(url)
        return self._read_page(url)

    def detect_type(self, url: str) -> str:
        lower = url.lower()
        if "youtube.com/watch" in lower or "youtu.be/" in lower:
            return "video"
        if lower.endswith(".pdf"):
            return "document"
        return "page"

    def _read_page(self, url: str) -> Dict[str, Optional[str]]:
        response = requests.get(url, timeout=self.timeout, headers=self.headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for node in soup(["script", "style", "noscript", "svg"]):
            node.extract()

        title = soup.title.string.strip() if soup.title and soup.title.string else url
        text = soup.get_text("\n")
        text = self._clean_text(text)
        return {
            "resource_type": "page",
            "title": title,
            "content": text[: self.max_chars],
            "read_status": "read",
        }

    def _read_pdf(self, url: str) -> Dict[str, Optional[str]]:
        try:
            from io import BytesIO

            from pypdf import PdfReader
        except ImportError:
            return {
                "resource_type": "document",
                "title": url,
                "content": None,
                "read_status": "missing_pypdf_dependency",
            }

        response = requests.get(url, timeout=self.timeout, headers=self.headers)
        response.raise_for_status()
        reader = PdfReader(BytesIO(response.content))
        chunks = []
        for page in reader.pages[:8]:
            chunks.append(page.extract_text() or "")

        return {
            "resource_type": "document",
            "title": url.split("/")[-1] or url,
            "content": self._clean_text("\n".join(chunks))[: self.max_chars],
            "read_status": "read",
        }

    def _read_youtube(self, url: str) -> Dict[str, Optional[str]]:
        video_id = self._youtube_id(url)
        if not video_id:
            return {
                "resource_type": "video",
                "title": url,
                "content": None,
                "read_status": "missing_video_id",
            }

        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            return {
                "resource_type": "video",
                "title": url,
                "content": None,
                "read_status": "missing_youtube_transcript_dependency",
            }

        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-IN"])
        text = " ".join(item.get("text", "") for item in transcript)
        return {
            "resource_type": "video",
            "title": f"YouTube video {video_id}",
            "content": self._clean_text(text)[: self.max_chars],
            "read_status": "read",
        }

    def _youtube_id(self, url: str) -> Optional[str]:
        parsed = urlparse(url)
        if parsed.netloc.endswith("youtu.be"):
            return parsed.path.strip("/") or None
        if "youtube.com" in parsed.netloc:
            return parse_qs(parsed.query).get("v", [None])[0]
        return None

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text or "")
        return text.strip()
