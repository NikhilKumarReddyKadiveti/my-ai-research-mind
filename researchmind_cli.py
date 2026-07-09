import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
TRAIN_DATA_PATH = ROOT / "model" / "data" / "train_data.txt"


LOGO = r"""
ResearchMind
  ____  __  __
 |  _ \|  \/  |  local + Gemini + your training data
 | |_) | |\/| |
 |  _ <| |  | |
 |_| \_\_|  |_|
"""


def load_environment(provider: str | None, model: str | None) -> None:
    load_dotenv(ROOT / "backend" / ".env")
    if provider:
        os.environ["AI_PROVIDER"] = provider
    if model:
        if os.environ.get("AI_PROVIDER", "").lower() in {"ollama", "local"}:
            os.environ["OLLAMA_MODEL"] = model
        elif os.environ.get("AI_PROVIDER", "").lower() == "gemini":
            os.environ["GEMINI_MODEL"] = model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="researchmind",
        description="ResearchMind AI CLI for chat, tutoring, research, and coding.",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "gemini", "ollama", "local"],
        help="AI provider to use. auto tries Gemini, then local Ollama, then fallback.",
    )
    parser.add_argument("--model", help="Provider model, such as gemini-2.5-flash or qwen2.5-coder:3b.")

    sub = parser.add_subparsers(dest="command", required=True)

    chat = sub.add_parser("chat", help="Ask the assistant anything.")
    chat.add_argument("prompt", nargs="*", help="Prompt text. Omit for interactive mode.")

    tutor = sub.add_parser("tutor", help="Get a step-by-step tutoring lesson.")
    tutor.add_argument("topic", nargs="+")
    tutor.add_argument("--level", default="beginner")

    code = sub.add_parser("code", help="Ask for coding help.")
    code.add_argument("prompt", nargs="+")

    research = sub.add_parser("research", help="Search accessible web resources and produce a report.")
    research.add_argument("query", nargs="+")

    ingest = sub.add_parser("ingest-training", help="Append exported website chats to model/data/train_data.txt.")
    ingest.add_argument("files", nargs="+", help="JSON exports from the website Settings page.")

    pull = sub.add_parser("pull-training", help="Pull Supabase chat, tutor, and resource rows into model/data/train_data.txt.")
    pull.add_argument("--access-token", required=True, help="Current Supabase user access token.")
    pull.add_argument("--limit", type=int, default=500, help="Maximum messages to pull.")

    train = sub.add_parser("train-local", help="Train the ResearchMind scratch SLM on model/data/train_data.txt.")
    train.add_argument("--iters", type=int, default=500, help="Training iterations for this run.")

    return parser


def interactive_chat(service) -> None:
    print(LOGO)
    print("Type /exit to stop.")
    while True:
        prompt = input("\nYou: ").strip()
        if prompt.lower() in {"/exit", "exit", "quit"}:
            break
        if not prompt:
            continue
        print("\nResearchMind:\n" + service.chat(prompt))


def messages_to_training_text(messages: list[dict]) -> str:
    lines = []
    for message in messages:
        role = message.get("role", "user")
        content = " ".join(str(message.get("content", "")).split())
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def append_training_text(text: str) -> None:
    TRAIN_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TRAIN_DATA_PATH.open("a", encoding="utf-8") as file:
        file.write("\n\n--- ResearchMind conversation training sample ---\n")
        file.write(text.strip())
        file.write("\n")


def ingest_training_exports(paths: list[str]) -> None:
    added = 0
    for path_text in paths:
        path = Path(path_text).expanduser()
        data = json.loads(path.read_text(encoding="utf-8"))
        conversations = data.get("conversations", data if isinstance(data, list) else [])
        for conversation in conversations:
            text = messages_to_training_text(conversation.get("messages", []))
            if text:
                append_training_text(text)
                added += 1
    print(f"Added {added} conversation training samples to {TRAIN_DATA_PATH}.")


def pull_supabase_training(access_token: str, limit: int) -> None:
    import httpx

    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_ANON_KEY", "")
    if not supabase_url or not supabase_key:
        raise SystemExit("SUPABASE_URL and SUPABASE_ANON_KEY must be set in backend/.env.")

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {access_token}",
    }
    message_url = f"{supabase_url}/rest/v1/messages"
    message_params = {
        "select": "conversation_id,role,content,created_at",
        "order": "created_at.asc",
        "limit": str(limit),
    }
    response = httpx.get(message_url, headers=headers, params=message_params, timeout=20)
    if response.status_code != 200:
        raise SystemExit(f"Supabase pull failed: {response.status_code} {response.text}")

    grouped: dict[str, list[dict]] = {}
    for message in response.json():
        grouped.setdefault(message["conversation_id"], []).append(message)

    for messages in grouped.values():
        append_training_text(messages_to_training_text(messages))

    session_response = httpx.get(
        f"{supabase_url}/rest/v1/learning_sessions",
        headers=headers,
        params={"select": "topic,level,goal,study_plan,created_at", "order": "created_at.desc", "limit": str(limit)},
        timeout=20,
    )
    session_count = 0
    if session_response.status_code == 200:
        for item in session_response.json():
            append_training_text(
                "\n".join(
                    part
                    for part in [
                        f"topic: {item.get('topic', '')}",
                        f"level: {item.get('level', '')}",
                        f"goal: {item.get('goal', '')}",
                        f"study_plan: {item.get('study_plan', '')}",
                    ]
                    if part.strip()
                )
            )
            session_count += 1

    resource_response = httpx.get(
        f"{supabase_url}/rest/v1/learning_resources",
        headers=headers,
        params={"select": "title,url,resource_type,summary,why_useful,raw_excerpt,created_at", "order": "created_at.desc", "limit": str(limit)},
        timeout=20,
    )
    resource_count = 0
    if resource_response.status_code == 200:
        for item in resource_response.json():
            append_training_text(
                "\n".join(
                    part
                    for part in [
                        f"resource: {item.get('title', '')}",
                        f"url: {item.get('url', '')}",
                        f"type: {item.get('resource_type', '')}",
                        f"summary: {item.get('summary', '')}",
                        f"why_useful: {item.get('why_useful', '')}",
                        f"excerpt: {item.get('raw_excerpt', '')}",
                    ]
                    if part.strip()
                )
            )
            resource_count += 1

    step_response = httpx.get(
        f"{supabase_url}/rest/v1/learning_steps",
        headers=headers,
        params={"select": "title,goal,task,is_completed,created_at", "order": "created_at.desc", "limit": str(limit)},
        timeout=20,
    )
    step_count = 0
    if step_response.status_code == 200:
        for item in step_response.json():
            append_training_text(
                "\n".join(
                    part
                    for part in [
                        f"learning_step: {item.get('title', '')}",
                        f"goal: {item.get('goal', '')}",
                        f"task: {item.get('task', '')}",
                        f"completed: {item.get('is_completed', False)}",
                    ]
                    if part.strip()
                )
            )
            step_count += 1

    progress_response = httpx.get(
        f"{supabase_url}/rest/v1/user_progress",
        headers=headers,
        params={"select": "progress_type,notes,created_at", "order": "created_at.desc", "limit": str(limit)},
        timeout=20,
    )
    progress_count = 0
    if progress_response.status_code == 200:
        for item in progress_response.json():
            append_training_text(f"progress: {item.get('progress_type', '')}\nnotes: {item.get('notes', '')}")
            progress_count += 1

    feedback_response = httpx.get(
        f"{supabase_url}/rest/v1/feedback_events",
        headers=headers,
        params={"select": "rating,feedback,created_at", "order": "created_at.desc", "limit": str(limit)},
        timeout=20,
    )
    feedback_count = 0
    if feedback_response.status_code == 200:
        for item in feedback_response.json():
            append_training_text(f"feedback_rating: {item.get('rating', '')}\nfeedback: {item.get('feedback', '')}")
            feedback_count += 1

    message_count = sum(len(items) for items in grouped.values())
    print(
        f"Pulled {message_count} messages, {session_count} learning sessions, "
        f"{step_count} steps, {resource_count} resources, {progress_count} progress rows, "
        f"and {feedback_count} feedback events into {TRAIN_DATA_PATH}."
    )


def train_local_model(iters: int) -> None:
    env = os.environ.copy()
    env["RESEARCHMIND_MAX_ITERS"] = str(iters)
    print(LOGO)
    print(f"Training local SLM for {iters} iterations on {TRAIN_DATA_PATH}.")
    subprocess.run([sys.executable, str(ROOT / "model" / "train.py")], cwd=str(ROOT), env=env, check=True)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    load_environment(args.provider, args.model)

    from backend.app.services.ai_service import AIService

    service = AIService()

    if args.command == "chat":
        if args.prompt:
            print(service.chat(" ".join(args.prompt)))
        else:
            interactive_chat(service)
        return

    if args.command == "tutor":
        print(service.tutor_lesson(" ".join(args.topic), args.level))
        return

    if args.command == "code":
        print(service.code_help(" ".join(args.prompt)))
        return

    if args.command == "research":
        from agent.research_agent import ResearchAgent

        query = " ".join(args.query)
        agent = ResearchAgent(max_results=5)
        report = agent.research_topic(query)
        print(service.research_summary(query, report["sources"]))
        print("\nSources:")
        for index, source in enumerate(report["sources"], start=1):
            print(f"{index}. {source['title']}\n   {source['url']}")
        return

    if args.command == "ingest-training":
        ingest_training_exports(args.files)
        return

    if args.command == "pull-training":
        pull_supabase_training(args.access_token, args.limit)
        return

    if args.command == "train-local":
        train_local_model(args.iters)
        return


if __name__ == "__main__":
    main()
