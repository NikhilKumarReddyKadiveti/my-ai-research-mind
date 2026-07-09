from typing import Dict, List

from agent.resource_reader import ResourceReader
from agent.research_agent import ResearchAgent
from backend.app.services.ai_service import get_ai_service


class TutorAgent:
    """
    Research-first tutor agent.

    It finds free learning resources, reads public pages/documents/videos when
    possible, then returns a practical learning path with summaries and steps.
    """

    def __init__(self, max_results: int = 6):
        self.research_agent = ResearchAgent(max_results=max_results)
        self.reader = ResourceReader()

    def build_learning_path(self, topic: str, level: str = "beginner") -> Dict:
        query = f"best free {level} tutorial course to learn {topic}"
        results = self.research_agent.search(query)
        resources = []

        for result in results[:6]:
            url = result.get("link", "")
            read_data = self._safe_read(url)
            content = read_data.get("content") or result.get("snippet", "")
            resources.append(
                {
                    "title": read_data.get("title") or result.get("title", url),
                    "url": url,
                    "resource_type": read_data.get("resource_type", "page"),
                    "read_status": read_data.get("read_status", "snippet_only"),
                    "free": True,
                    "summary": self._summarize(content),
                    "why_useful": self._why_useful(content, topic),
                }
            )

        lesson = get_ai_service().tutor_lesson(topic, level)
        steps = self._build_steps(topic, level, resources)
        return {
            "topic": topic,
            "level": level,
            "resources": resources,
            "steps": steps,
            "study_plan": lesson,
        }

    def _safe_read(self, url: str) -> Dict:
        try:
            return self.reader.read(url)
        except Exception:
            return {
                "resource_type": self.reader.detect_type(url),
                "title": url,
                "content": None,
                "read_status": "read_failed",
            }

    def _summarize(self, text: str) -> str:
        clean = " ".join((text or "").split())
        if not clean:
            return "No readable text was available, but the link may still be useful."
        sentences = clean.split(". ")
        return ". ".join(sentences[:3])[:700]

    def _why_useful(self, text: str, topic: str) -> str:
        lowered = (text or "").lower()
        if "project" in lowered or "example" in lowered:
            return f"Good for practicing {topic} with examples or projects."
        if "course" in lowered or "tutorial" in lowered:
            return f"Good for structured learning in {topic}."
        if "documentation" in lowered or "docs" in lowered:
            return f"Good as a reference while solving {topic} problems."
        return f"Useful supporting material for learning {topic}."

    def _build_steps(self, topic: str, level: str, resources: List[Dict]) -> List[Dict]:
        return [
            {
                "order_index": 1,
                "title": f"Tiny first idea in {topic}",
                "goal": "Understand one small concept before moving forward.",
                "task": "Read the tutor explanation, then explain the tiny idea in one simple sentence.",
            },
            {
                "order_index": 2,
                "title": "See one easy example",
                "goal": "Connect the idea to something concrete.",
                "task": "Copy the example in the lesson and change one small thing.",
            },
            {
                "order_index": 3,
                "title": "Try with help",
                "goal": "Practice without feeling lost.",
                "task": "Do the mini exercise. If you are stuck, ask ResearchMind to give one hint, not the full answer.",
            },
            {
                "order_index": 4,
                "title": "Move to the next tiny topic",
                "goal": "Learn topic by topic like small steps on stairs.",
                "task": f"Ask: 'Teach me the next tiny topic in {topic} like I am a nursery kid.'",
            },
        ]

    def _study_plan(self, topic: str, level: str) -> str:
        return (
            f"For {level} level {topic}, spend 25 minutes reading, 25 minutes practicing, "
            "and 10 minutes writing what you learned. Repeat daily and keep one mini project."
        )
