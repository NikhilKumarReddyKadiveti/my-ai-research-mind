import os
import re
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
from app.schemas.research import (
    AIChatRequest,
    AIChatResponse,
    AIImageChatRequest,
    TutorResearchRequest,
    TutorResearchResponse,
    ResearchQuery,
    ResearchResponse,
    MapRequest,
    MapResponse,
    VoiceActionRequest,
    VoiceActionResponse,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from agent.safety_policy import SafetyPolicy
from agent.action_agent import ActionAgent
from app.services.ai_service import get_ai_service
from app.services.supabase_auth import AuthUser, require_user
import datetime
import httpx

if load_dotenv:
    load_dotenv()

app = FastAPI(title="ResearchMind AI API")

allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:8081,http://localhost:19006").split(",")
    if origin.strip()
]

# Enable CORS for frontend and Expo web
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

safety_policy = SafetyPolicy()
action_agent = ActionAgent()
research_agent = None
rag_system = None
maps_agent = None
tutor_agent = None

def get_research_agent():
    global research_agent
    if research_agent is None:
        from agent.research_agent import ResearchAgent

        research_agent = ResearchAgent()
    return research_agent

def get_rag_system():
    global rag_system
    if rag_system is None:
        from agent.rag_system import RAGSystem

        rag_system = RAGSystem()
    return rag_system

def get_maps_agent():
    global maps_agent
    if maps_agent is None:
        from agent.maps_agent import MapsAgent

        maps_agent = MapsAgent()
    return maps_agent

def get_tutor_agent():
    global tutor_agent
    if tutor_agent is None:
        from agent.tutor_agent import TutorAgent

        tutor_agent = TutorAgent()
    return tutor_agent

FRONTEND_INDEX = PROJECT_ROOT / "frontend" / "index.html"
FRONTEND_VENDOR = PROJECT_ROOT / "frontend" / "vendor"
FRONTEND_ASSETS = PROJECT_ROOT / "frontend" / "assets"

if FRONTEND_VENDOR.exists():
    app.mount("/vendor", StaticFiles(directory=FRONTEND_VENDOR), name="vendor")

if FRONTEND_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS), name="assets")

@app.get("/")
def serve_website():
    if FRONTEND_INDEX.exists():
        return FileResponse(
            FRONTEND_INDEX,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return {"message": "Welcome to ResearchMind AI API"}

@app.get("/api/health")
def read_root():
    return {"message": "Welcome to ResearchMind AI API"}

@app.get("/api/config")
def public_config():
    gemini_model = os.getenv("GEMINI_MODEL", "")
    return {
        "apiBase": "",
        "supabaseUrl": os.getenv("SUPABASE_URL", ""),
        "supabaseAnonKey": os.getenv("SUPABASE_ANON_KEY", ""),
        "openaiModel": os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        "aiProvider": "Gemini" if os.getenv("GEMINI_API_KEY") else "OpenAI/local",
        "geminiModel": gemini_model,
        "ollamaModel": os.getenv("OLLAMA_MODEL", ""),
    }

@app.get("/me")
async def read_me(user: AuthUser = Depends(require_user)):
    return {"id": user.id, "email": user.email}

@app.post("/assistant/chat", response_model=AIChatResponse)
async def assistant_chat(request: AIChatRequest):
    if not safety_policy.is_safe(request.message):
        raise HTTPException(status_code=400, detail=safety_policy.get_refusal_message())

    message = request.message.strip()
    lowered = message.lower()
    mode = (request.mode or "chat").lower()
    history = [item.model_dump() for item in request.history][-16:]

    wants_research = (
        mode == "research"
        or re.search(r"\b(research|resources|websites|sources)\b", lowered)
        or "find sources" in lowered
        or "report on" in lowered
    )
    wants_tutor = (
        mode == "tutor"
        or re.search(r"\b(teach|tutor|learn|lesson)\b", lowered)
        or "explain like" in lowered
    )

    if wants_research:
        report = get_research_agent().research_topic(message)
        summary = get_ai_service().research_summary(
            message,
            report["sources"],
            provider=request.provider,
            api_key=request.api_key,
        )
        links = "\n".join(
            f"{index + 1}. {source['title']}\n   {source['url']}"
            for index, source in enumerate(report["sources"], start=1)
        )
        return {"reply": f"{summary}\n\nSources:\n{links}", "success": True}

    if wants_tutor:
        reply = get_ai_service().tutor_lesson(
            message,
            "beginner",
            history=history,
            provider=request.provider,
            api_key=request.api_key,
        )
        return {"reply": reply, "success": True}

    reply = get_ai_service().chat(
        message,
        history=history,
        provider=request.provider,
        api_key=request.api_key,
    )
    return {"reply": reply, "success": True}

@app.post("/assistant/image", response_model=AIChatResponse)
async def assistant_image_chat(request: AIImageChatRequest):
    if not safety_policy.is_safe(request.message):
        raise HTTPException(status_code=400, detail=safety_policy.get_refusal_message())

    reply = get_ai_service().chat_with_image(
        request.message,
        request.image_data,
        request.mime_type,
        history=[item.model_dump() for item in request.history][-16:],
        provider=request.provider,
        api_key=request.api_key,
    )
    return {"reply": reply, "success": True}

@app.post("/db/check")
async def check_database(user: AuthUser = Depends(require_user)):
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    if not supabase_url or not supabase_anon_key:
        raise HTTPException(status_code=500, detail="Supabase is not configured in backend/.env.")

    rest_url = f"{supabase_url.rstrip('/')}/rest/v1/conversations"
    title = f"ResearchMind backend database test {datetime.datetime.utcnow().isoformat()}"
    headers = {
        "apikey": supabase_anon_key,
        "Authorization": f"Bearer {user.access_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        insert_response = await client.post(
            rest_url,
            headers={**headers, "Prefer": "return=representation"},
            params={"select": "id,title"},
            json={"user_id": user.id, "title": title},
        )

        if insert_response.status_code not in (200, 201):
            raise HTTPException(
                status_code=500,
                detail=format_supabase_error("insert into conversations", insert_response),
            )

        rows = insert_response.json()
        if not rows:
            raise HTTPException(status_code=500, detail="Supabase insert succeeded but returned no row.")

        row_id = rows[0]["id"]
        read_response = await client.get(
            rest_url,
            headers=headers,
            params={"id": f"eq.{row_id}", "select": "id,title"},
        )

        if read_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=format_supabase_error("read from conversations", read_response),
            )

        read_rows = read_response.json()
        if not read_rows:
            raise HTTPException(status_code=500, detail="Inserted row could not be read back. Check RLS select policy.")

        delete_response = await client.delete(
            rest_url,
            headers=headers,
            params={"id": f"eq.{row_id}"},
        )

        if delete_response.status_code not in (200, 204):
            raise HTTPException(
                status_code=500,
                detail=format_supabase_error("delete from conversations", delete_response),
            )

    return {
        "success": True,
        "message": "Database insert, read, and delete worked through Supabase RLS.",
        "table": "conversations",
        "title": read_rows[0]["title"],
        "user_id": user.id,
    }

def format_supabase_error(action: str, response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {"message": response.text}

    message = payload.get("message") or payload.get("msg") or str(payload)
    hint = payload.get("hint")
    code = payload.get("code")
    detail = f"Could not {action}: {message}"
    if code:
        detail += f" (code {code})"
    if hint:
        detail += f" Hint: {hint}"
    if response.status_code == 404:
        detail += " Make sure supabase/schema.sql has been run in your Supabase SQL editor."
    if response.status_code in (401, 403):
        detail += " Check your Supabase anon key and RLS policies."
    return detail

@app.post("/ai/chat", response_model=AIChatResponse)
async def ai_chat(request: AIChatRequest, user: AuthUser = Depends(require_user)):
    if not safety_policy.is_safe(request.message):
        raise HTTPException(status_code=400, detail=safety_policy.get_refusal_message())

    try:
        reply = get_ai_service().chat(
            request.message,
            history=[item.model_dump() for item in request.history][-16:],
            provider=request.provider,
            api_key=request.api_key,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"reply": reply, "success": True}

@app.post("/tutor/research", response_model=TutorResearchResponse)
async def tutor_research(
    request: TutorResearchRequest,
    user: AuthUser = Depends(require_user),
):
    if not safety_policy.is_safe(request.topic):
        raise HTTPException(status_code=400, detail=safety_policy.get_refusal_message())

    path = get_tutor_agent().build_learning_path(request.topic, request.level)
    return {**path, "success": True}

@app.post("/research", response_model=ResearchResponse)
async def perform_research(request: ResearchQuery):
    # 1. Safety Check
    if not safety_policy.is_safe(request.query):
        raise HTTPException(status_code=400, detail=safety_policy.get_refusal_message())
    
    # 2. Web Research
    print(f"Starting {request.mode} on: {request.query}")
    report = get_research_agent().research_topic(request.query)
    
    # 3. RAG Storage can be enabled later. Keep website research fast and
    # avoid blocking the UI while local embedding models load.
    if os.getenv("ENABLE_RAG_STORAGE", "false").lower() == "true":
        try:
            documents = [s['content'] for s in report['sources']]
            metadatas = [{"title": s['title'], "url": s['url']} for s in report['sources']]
            get_rag_system().add_documents(documents, metadatas)
        except Exception as exc:
            print(f"RAG storage skipped: {exc}")
    
    # 4. AI reasoning over the sources.
    summary = get_ai_service().research_summary(request.query, report["sources"])
    
    return {
        "query": request.query,
        "summary": summary,
        "sources": report['sources'],
        "created_at": datetime.datetime.utcnow()
    }

@app.post("/navigate", response_model=MapResponse)
async def navigate_to(request: MapRequest):
    # 1. Safety Check
    if not safety_policy.is_safe(request.destination):
        raise HTTPException(status_code=400, detail=safety_policy.get_refusal_message())
    
    # 2. Map Guidance
    print(f"Guiding user to: {request.destination}")
    guidance = get_maps_agent().guide_me(request.destination, request.current_location)
    
    return guidance

@app.post("/voice-action", response_model=VoiceActionResponse)
async def create_voice_action(
    request: VoiceActionRequest,
    user: AuthUser = Depends(require_user),
):
    # 1. Safety Check
    if not safety_policy.is_safe(request.command):
        raise HTTPException(status_code=400, detail=safety_policy.get_refusal_message())

    # 2. Let AI interpret the one-time command, then keep deterministic link
    # building as a safety rail. Do not log the command, phone number, message,
    # or contact name.
    # Do not log the command, phone number, message, or contact name.
    try:
        ai_action = get_ai_service().interpret_voice_action(request.command)
        interpreted_command = request.command
        interpreted_phone = request.phone_number or ai_action.get("phone_number")
        interpreted_message = request.message or ai_action.get("message")
        interpreted_target = ai_action.get("target")

        if ai_action.get("action_type") == "open_browser" and interpreted_target:
            interpreted_command = f"open {interpreted_target}"
        elif ai_action.get("action_type") == "phone_call" and interpreted_phone:
            interpreted_command = f"call {interpreted_phone}"
        elif ai_action.get("action_type") == "whatsapp_chat" and interpreted_phone:
            interpreted_command = f"whatsapp {interpreted_phone}"
            if interpreted_message:
                interpreted_command += f" saying {interpreted_message}"

        action = action_agent.handle_voice_command(
            command=interpreted_command,
            phone_number=interpreted_phone,
            message=interpreted_message,
            contact_name=request.contact_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "action_type": action.action_type,
        "target": action.target,
        "link": action.link,
        "message": action.message,
        "requires_user_confirmation": action.requires_user_confirmation,
        "privacy_note": action.privacy_note,
        "success": True,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
