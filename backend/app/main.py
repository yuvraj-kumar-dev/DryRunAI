from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app import config, voice


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


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    await voice.handle_voice_websocket(websocket)
