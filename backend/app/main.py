import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

from app import config, interview, problems, voice
from app import session_state as state


@asynccontextmanager
async def lifespan(app: FastAPI):
    await voice.start_runner()
    yield
    await voice.stop_runner()


app = FastAPI(title="DryRunAI backend", lifespan=lifespan)

# Single source of truth for both CORS (HTTP fetch/XHR) and the WebSocket route below --
# CORSMiddleware does NOT cover WebSocket upgrade handshakes (browsers don't enforce the same
# origin policy on them the way they do for fetch/XHR), so /ws/voice needs its own explicit check
# against the same allowed origin rather than relying on this middleware to protect it too.
ALLOWED_ORIGINS = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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
    """Topic/difficulty/persona/length choices for the pre-session selection screen."""
    return {
        "topics": problems.TOPICS,
        "difficulties": problems.DIFFICULTY_ORDER,
        "personas": list(interview.PERSONAS.keys()),
        "plan_sizes": list(range(1, voice.MAX_PLAN_SIZE + 1)),
        "default_plan_size": voice.DEFAULT_PLAN_SIZE,
    }


class CreateSessionRequest(BaseModel):
    topic: str
    difficulty: str
    persona: str
    plan_size: int = voice.DEFAULT_PLAN_SIZE


@app.post("/api/sessions")
def create_session(req: CreateSessionRequest):
    """Selects the first problem upfront so the frontend can render it as text before the voice
    WebSocket even connects -- see PENDING_SESSIONS in voice.py for why.

    Only the *first* problem is chosen here. Later ones are picked at the moment the interview
    moves on (so they can adapt to how the candidate did) and pushed to the browser over the
    voice WebSocket, which keeps the "pick once, pass the result" rule intact.
    """
    if req.topic not in problems.TOPICS:
        raise HTTPException(status_code=400, detail=f"Unknown topic: {req.topic}")
    if req.difficulty not in problems.DIFFICULTY_ORDER:
        raise HTTPException(status_code=400, detail=f"Unknown difficulty: {req.difficulty}")
    if req.persona not in interview.PERSONAS:
        raise HTTPException(status_code=400, detail=f"Unknown persona: {req.persona}")

    plan_size = voice.coerce_plan_size(req.plan_size)
    problem = problems.select_problem(req.topic, req.difficulty)
    session_id = str(uuid.uuid4())
    voice.PENDING_SESSIONS[session_id] = {
        "problem": problem,
        "persona": req.persona,
        "plan_size": plan_size,
    }
    return {
        "session_id": session_id,
        "problem": problems.public_problem(problem),
        "plan_size": plan_size,
    }


class CodeSnapshot(BaseModel):
    code: str


@app.post("/api/sessions/{session_id}/code")
def submit_code_snapshot(session_id: str, snapshot: CodeSnapshot):
    session = voice.ACTIVE_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="No active session with that id")
    state.record_code_snapshot(session, snapshot.code)
    return {"status": "ok"}


@app.post("/api/sessions/{session_id}/end")
async def end_session(session_id: str):
    """The "End interview" button. Scores the interview and returns the report directly.

    Separate from the interviewer's own end_interview tool because the candidate has to be able
    to stop without the AI's cooperation -- a real session had the candidate say "let's end this
    interview" twice with nothing happening, because closing the tab was the only way out and
    the scorecard was generated somewhere they'd never see it.
    """
    session = voice.ACTIVE_SESSIONS.get(session_id)
    if session is None:
        record = voice.COMPLETED_SESSIONS.get(session_id)
        if record is not None:
            return record
        raise HTTPException(status_code=404, detail="No active session with that id")
    session["end_reason"] = "candidate ended the interview"
    record = await voice.finalize_session(session, session.get("worker"))
    return record


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    """The report screen's source of truth.

    The scorecard is also pushed down the voice WebSocket as it's generated, but a push can be
    lost to a socket that's already tearing down, and the report page may be opened fresh (or
    reloaded) long after. This is the reliable path.
    """
    record = voice.COMPLETED_SESSIONS.get(session_id)
    if record is not None:
        return record
    if session_id in voice.ACTIVE_SESSIONS:
        raise HTTPException(status_code=409, detail="Session is still in progress")
    raise HTTPException(status_code=404, detail="No session with that id")


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    # CORSMiddleware above does not protect WebSocket upgrade handshakes -- browsers don't apply
    # the same-origin policy to them the way they do fetch/XHR, so without this check any page
    # (opened in another tab) could open a WebSocket straight to this route from its own
    # JavaScript. Reject before accept() -- the standard pattern for a pre-accept handshake
    # rejection, not something that requires accepting the connection first.
    origin = websocket.headers.get("origin")
    if origin not in ALLOWED_ORIGINS:
        logger.warning(f"Rejected /ws/voice connection from disallowed origin: {origin!r}")
        await websocket.close(code=1008)
        return
    await websocket.accept()
    await voice.handle_voice_websocket(websocket)
