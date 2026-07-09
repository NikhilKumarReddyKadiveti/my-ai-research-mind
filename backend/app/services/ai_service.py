import os
import json
import datetime
from functools import lru_cache

import httpx
from openai import OpenAI


class AIService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        self.gemini_key = gemini_key if gemini_key and not gemini_key.startswith("replace_with") else None
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.ai_provider = os.getenv("AI_PROVIDER", "auto").lower()
        self.ollama_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
        self.local_mode = not api_key or api_key.startswith("replace_with")
        self.client = None if self.local_mode else OpenAI(api_key=api_key, timeout=12, max_retries=0)
        self.model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        self.openai_disabled_reason = None

    def chat(self, message: str, history: list[dict] | None = None) -> str:
        if self.ai_provider in ("auto", "gemini") and self.gemini_key:
            gemini_reply = self._gemini_generate(
                system_instruction=(
                    "You are ResearchMind, an original AI assistant inside a website. "
                    "Think through the user's request and give the best practical answer. "
                    "Use the conversation history to stay consistent. "
                    "Do not say your answer is predefined. Be specific, helpful, and concise."
                ),
                prompt=message,
                history=history,
            )
            if gemini_reply:
                return self._sanitize_reply(gemini_reply)

        if self.ai_provider in ("auto", "ollama", "local"):
            ollama_reply = self._ollama_generate(
                system_instruction=(
                    "You are ResearchMind Local AI. Think carefully and answer originally. "
                    "For coding, give clean, production-minded code and explain important tradeoffs."
                ),
                prompt=message,
                history=history,
            )
            if ollama_reply:
                return self._sanitize_reply(ollama_reply)

        if self.local_mode or self.openai_disabled_reason:
            return self._local_reply(message)

        if self.client is None:
            return self._local_reply(message)

        try:
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are ResearchMind, a privacy-first AI assistant. "
                            "Help with research, reasoning, navigation planning, and "
                            "safe device-action preparation. Do not claim to send "
                            "messages, place calls, or operate apps without user confirmation."
                        ),
                    },
                    {"role": "user", "content": message},
                ],
            )
            return self._sanitize_reply(response.output_text)
        except Exception as exc:
            self.openai_disabled_reason = exc.__class__.__name__
            return self._local_reply(message)

    def tutor_lesson(self, topic: str, level: str = "beginner", history: list[dict] | None = None) -> str:
        prompt = (
            f"Current learner message: {topic}\n"
            f"Learner level: {level}\n\n"
            "Teach directly as an ongoing human tutor. If the learner says next, continue from the last "
            "concept in the conversation. If they ask to learn Python, build a path and start at the right "
            "level. Do not restart the same intro. Do not use a fixed six-part template unless it fits. "
            "Give one clear concept, one short example, and one small practice question. Keep the tone natural."
        )

        if self.ai_provider in ("auto", "gemini") and self.gemini_key:
            gemini_reply = self._gemini_generate(
                system_instruction=(
                    "You are ResearchMind Tutor, a warm but serious teacher inside a learning website. "
                    "You remember the conversation and move forward topic by topic. "
                    "Never claim to be Gemini, Alibaba, Qwen, OpenAI, or any provider. "
                    "Never say the answer is predefined. Avoid canned lesson templates. "
                    "For Python learners, teach by writing tiny runnable examples and asking one check question. "
                    "Do not ask if the learner is ready; start teaching immediately."
                ),
                prompt=prompt,
                history=history,
            )
            if gemini_reply:
                cleaned = self._sanitize_reply(gemini_reply)
                if not self._is_weak_tutor_reply(cleaned):
                    return cleaned

        if self.ai_provider in ("auto", "ollama", "local"):
            ollama_reply = self._ollama_generate(
                system_instruction=(
                    "You are ResearchMind Tutor. Do not mention the underlying model or provider. "
                    "Continue the lesson from the conversation history. Teach naturally, one concept at a time, "
                    "with a tiny example and a small question."
                ),
                prompt=prompt,
                history=history,
            )
            if ollama_reply:
                cleaned = self._sanitize_reply(ollama_reply)
                if not self._is_weak_tutor_reply(cleaned):
                    return cleaned

        if self.local_mode or self.client is None or self.openai_disabled_reason:
            return self._local_tutor_lesson(topic, level, history=history)

        try:
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are ResearchMind Tutor. You teach slowly, warmly, and directly. "
                            "You explain one tiny concept at a time with examples and practice. "
                            "Never give only a list of links or tell the learner to self-study."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            return self._sanitize_reply(response.output_text)
        except Exception:
            self.openai_disabled_reason = "tutor_openai_failed"
            return self._local_tutor_lesson(topic, level, history=history)

    def research_summary(self, query: str, sources: list[dict]) -> str:
        source_text = "\n".join(
            f"{index + 1}. {source.get('title')} - {source.get('url')}\n{source.get('content', '')[:500]}"
            for index, source in enumerate(sources[:6])
        )
        prompt = (
            f"User research request: {query}\n\n"
            f"Sources found:\n{source_text}\n\n"
            f"Current date: {datetime.date.today().isoformat()}\n\n"
            "Think like a research assistant. Explain what the user should learn from these sources, "
            "why these sources are relevant, and a good next step. Be honest if sources are weak. "
            "Do not invent dates, author names, or source details that are not provided."
        )
        if self.ai_provider in ("auto", "gemini") and self.gemini_key:
            gemini_reply = self._gemini_generate(
                system_instruction=(
                    "You are ResearchMind Researcher. Use only the provided source notes. "
                    "Write an original research report with findings, comparison, recommendation, "
                    "and limitations. Do not invent sources, dates, authors, or metadata."
                ),
                prompt=prompt,
            )
            if gemini_reply:
                return gemini_reply

        if self.ai_provider in ("auto", "ollama", "local"):
            ollama_reply = self._ollama_generate(
                system_instruction=(
                    "You are ResearchMind Local Researcher. Use only the provided source notes. "
                    "Write a useful original report with findings, limitations, and source links."
                ),
                prompt=prompt,
            )
            if ollama_reply:
                return ollama_reply

        if self.local_mode or self.client is None or self.openai_disabled_reason:
            return self._local_research_summary(query, sources)

        try:
            result = self.chat(prompt)
            if self.openai_disabled_reason or result.startswith("I understood: User research request"):
                return self._local_research_summary(query, sources)
            return result
        except Exception:
            return self._local_research_summary(query, sources)

    def interpret_voice_action(self, command: str) -> dict:
        prompt = (
            "Convert this user voice command into JSON for one safe client action. "
            "Allowed action_type values: open_browser, phone_call, whatsapp_chat, unknown. "
            "Return only JSON with keys: action_type, target, phone_number, message.\n\n"
            f"Command: {command}"
        )
        text = self.chat(prompt).strip()
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(text[start : end + 1])
        except Exception:
            pass
        return {"action_type": "unknown", "target": command, "phone_number": None, "message": None}

    def code_help(self, prompt: str) -> str:
        system = (
            "You are ResearchMind Code AI. Write high-quality, readable code. "
            "Ask for missing requirements only when absolutely necessary. "
            "Prefer simple, maintainable solutions and include commands/tests when useful."
        )
        if self.ai_provider in ("auto", "gemini") and self.gemini_key:
            reply = self._gemini_generate(system, prompt)
            if reply:
                return reply
        if self.ai_provider in ("auto", "ollama", "local"):
            reply = self._ollama_generate(system, prompt)
            if reply:
                return reply
        return self._local_reply(f"Help me code this: {prompt}")

    def chat_with_image(
        self,
        message: str,
        image_data: str,
        mime_type: str = "image/png",
        history: list[dict] | None = None,
    ) -> str:
        if self.ai_provider in ("auto", "gemini") and self.gemini_key:
            reply = self._gemini_generate(
                system_instruction=(
                    "You are ResearchMind Vision Tutor. Inspect the image carefully and answer the user's "
                    "question. If they ask to learn, teach step by step. If they ask to research, explain "
                    "what the image contains and what to search next."
                ),
                prompt=message,
                history=history,
                image_data=image_data,
                mime_type=mime_type,
            )
            if reply:
                return reply
        return self.chat(
            f"The user uploaded an image, but image reasoning is unavailable. Answer from text only: {message}",
            history=history,
        )

    def _gemini_generate(
        self,
        system_instruction: str,
        prompt: str,
        history: list[dict] | None = None,
        image_data: str | None = None,
        mime_type: str = "image/png",
    ) -> str | None:
        if not self.gemini_key:
            return None

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model}:generateContent"
        )
        contents = []
        for item in (history or [])[-16:]:
            role = "model" if item.get("role") in {"assistant", "model"} else "user"
            content = (item.get("content") or "").strip()
            if content:
                contents.append({"role": role, "parts": [{"text": content[:4000]}]})
        user_parts = [{"text": prompt}]
        if image_data:
            user_parts.append(
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": image_data.split(",", 1)[-1],
                    }
                }
            )
        contents.append({"role": "user", "parts": user_parts})

        payload = {
            "systemInstruction": {
                "parts": [{"text": system_instruction}],
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.95,
                "maxOutputTokens": 2048,
            },
        }
        try:
            response = httpx.post(
                url,
                headers={
                    "x-goog-api-key": self.gemini_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=18,
            )
            response.raise_for_status()
            data = response.json()
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            text = "".join(part.get("text", "") for part in parts).strip()
            return text or None
        except Exception as exc:
            print(f"Gemini request failed: {exc}")
            return None

    def _ollama_generate(self, system_instruction: str, prompt: str, history: list[dict] | None = None) -> str | None:
        history_text = "\n".join(
            f"{item.get('role', 'user')}: {(item.get('content') or '').strip()}"
            for item in (history or [])[-12:]
            if (item.get("content") or "").strip()
        )
        full_prompt = f"{system_instruction}\n\nConversation so far:\n{history_text}\n\nUser request:\n{prompt}"
        try:
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.55,
                        "num_ctx": 4096,
                    },
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            text = (data.get("response") or "").strip()
            return self._sanitize_reply(text) or None
        except Exception as exc:
            if self.ai_provider in ("ollama", "local"):
                print(f"Ollama request failed: {exc}")
            return None

    def _local_reply(self, message: str) -> str:
        topic = message.strip() or "your idea"
        lowered = topic.lower()
        if "connected" in lowered or "backend" in lowered:
            return (
                "ResearchMind is connected to the local backend and can answer through its built-in reasoning mode.\n"
                "The external OpenAI key currently has no usable quota, so local mode is handling this chat."
            )
        if lowered.startswith(("teach ", "explain ", "learn ")):
            clean = topic.split(" ", 1)[1] if " " in topic else topic
            return self._local_tutor_lesson(clean, "beginner")
        return (
            f"I am with you. For **{topic}**, I would start by turning it into one clear next action.\n\n"
            "Tell me what outcome you want, and I will either explain it, research it, write code for it, "
            "or break it into a small plan."
        )

    def _local_tutor_lesson(self, topic: str, level: str, history: list[dict] | None = None) -> str:
        clean_topic = topic.strip() or "this topic"
        clean_topic = clean_topic.replace("pyhtone", "python").replace("pythone", "python")
        lowered = clean_topic.lower()
        history_text = " ".join((item.get("content") or "").lower() for item in (history or [])[-8:])
        if lowered in {"next", "continue", "go on", "ok next", "okay next"} and "python" in history_text:
            return (
                "Good, next we move from **values** to **variables**.\n\n"
                "A variable is a name that points to a value. Think of it like a label on a box.\n\n"
                "```python\n"
                "age = 18\n"
                "name = \"Sam\"\n"
                "print(name, age)\n"
                "```\n\n"
                "Here, `age` remembers `18`, and `name` remembers `Sam`.\n\n"
                "Tiny practice: make a variable called `score` and store the number `95` in it."
            )
        if "python" in lowered and ("data" in lowered or "science" in lowered):
            return (
                "Let us learn Python for data science like tiny building blocks.\n\n"
                "Data science starts with **data**: numbers, names, dates, marks, prices, or any information we want to understand.\n\n"
                "Tiny Python example:\n"
                "```python\n"
                "marks = [80, 70, 90]\n"
                "average = sum(marks) / len(marks)\n"
                "print(average)\n"
                "```\n\n"
                "This stores marks, adds them, divides by how many marks there are, and prints the average.\n\n"
                "Small question: what do you think `len(marks)` means here?"
            )
        if "python" in lowered:
            return (
                "Absolutely. I will help you learn Python properly, not by throwing random topics at you.\n\n"
                "Let us first check your level with one tiny idea: Python stores information as **values**.\n"
                "A value can be a number, text, a list, or something more advanced later.\n\n"
                "```python\n"
                "print(10)\n"
                "print(\"hello\")\n"
                "```\n\n"
                "The first line prints a number. The second prints text.\n\n"
                "Small question: have you already used variables like `name = \"Alex\"`, or should I teach that next?"
            )
        return (
            f"Let us learn **{clean_topic}** in a real way.\n\n"
            "First, I will identify the smallest useful idea, show one example, then ask you to try one tiny step. "
            "After your answer, I will continue from there instead of restarting.\n\n"
            f"Tiny first step: what do you already know about {clean_topic}?"
        )

    def _sanitize_reply(self, text: str) -> str:
        cleaned = (text or "").strip()
        replacements = {
            "As an AI language model created by Alibaba Cloud,": "I am ResearchMind,",
            "As an AI language model developed by Alibaba Cloud,": "I am ResearchMind,",
            "created by Alibaba Cloud": "inside ResearchMind",
            "developed by Alibaba Cloud": "inside ResearchMind",
            "Qwen": "ResearchMind",
            "Alibaba Cloud": "ResearchMind",
        }
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        return cleaned

    def _is_weak_tutor_reply(self, text: str) -> bool:
        lowered = (text or "").lower()
        if len(lowered.split()) < 30:
            return True
        weak_phrases = ["are you ready", "how can i help", "what would you like to learn"]
        return any(phrase in lowered for phrase in weak_phrases)

    def _local_research_summary(self, query: str, sources: list[dict]) -> str:
        if not sources:
            return (
                f"I searched for '{query}', but I could not collect good readable sources yet. "
                "Try a more specific topic, for example 'beginner AI course with Python examples'."
            )

        lines = [
            f"Research report for: {query}",
            "",
            "What I found:",
        ]
        for index, source in enumerate(sources[:5], start=1):
            title = source.get("title", "Untitled source")
            content = " ".join((source.get("content") or "").split())[:260]
            lines.append(f"{index}. {title}")
            if content:
                lines.append(f"   Key point: {content}")

        lines.extend(
            [
                "",
                "Best way to use these:",
                "Start with the most beginner-friendly source, take notes in your own words, then practice one tiny example before moving to the next source.",
            ]
        )
        return "\n".join(lines)


@lru_cache
def get_ai_service() -> AIService:
    return AIService()
