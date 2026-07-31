import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import config, interview, problems, voice

# Fields shown to the candidate on screen. Deliberately excludes hints (for the AI to use
# verbally if needed, not for the candidate to read), follow_up_questions, source_reference, and
# prep_sheets_seen_on (internal/attribution metadata, not interview content).
PROBLEM_PUBLIC_FIELDS = [
    "id",
    "title",
    "topic",
    "difficulty",
    "problem_statement",
    "constraints",
    "examples",
]


def _public_problem(problem: dict) -> dict:
    return {k: problem[k] for k in PROBLEM_PUBLIC_FIELDS}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await voice.start_runner()
    yield
    await voice.stop_runner()


app = FastAPI(title="DryRunAI backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/config/status")
def config_status():
    """Reports which API keys are present, never their values — a quick Setup sanity check."""
    return {
        "deepgram_api_key_set": bool(config.DEEPGRAM_API_KEY),
        "groq_api_key_set": bool(config.GROQ_API_KEY),
        "anthropic_api_key_set": bool(config.ANTHROPIC_API_KEY),
        "groq_model": config.GROQ_MODEL,
    }


@app.get("/api/session-options")
def session_options():
    """Topic/difficulty/persona choices for the pre-session selection screen."""
    return {
        "topics": problems.TOPICS,
        "difficulties": problems.DIFFICULTY_ORDER,
        "personas": list(interview.PERSONAS.keys()),
    }


class CreateSessionRequest(BaseModel):
    topic: str
    difficulty: str
    persona: str


@app.post("/api/sessions")
def create_session(req: CreateSessionRequest):
    """Selects the problem upfront so the frontend can render it as text before the voice
    WebSocket even connects -- see PENDING_SESSIONS in voice.py for why.
    """
    if req.topic not in problems.TOPICS:
        raise HTTPException(status_code=400, detail=f"Unknown topic: {req.topic}")
    if req.difficulty not in problems.DIFFICULTY_ORDER:
        raise HTTPException(status_code=400, detail=f"Unknown difficulty: {req.difficulty}")
    if req.persona not in interview.PERSONAS:
        raise HTTPException(status_code=400, detail=f"Unknown persona: {req.persona}")

    problem = problems.select_problem(req.topic, req.difficulty)
    session_id = str(uuid.uuid4())
    voice.PENDING_SESSIONS[session_id] = {"problem": problem, "persona": req.persona}
    return {"session_id": session_id, "problem": _public_problem(problem)}


class CodeSnapshot(BaseModel):
    code: str


@app.post("/api/sessions/{session_id}/code")
def submit_code_snapshot(session_id: str, snapshot: CodeSnapshot):
    session = voice.ACTIVE_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="No active session with that id")
    session["latest_code"] = snapshot.code
    session["code_snapshots"].append({"timestamp": time.time(), "code": snapshot.code})
    return {"status": "ok"}


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    await voice.handle_voice_websocket(websocket)
