from pathlib import Path

from dotenv import load_dotenv
import os

# Single .env lives at the repo root, not inside backend/ — load it explicitly
# so this works regardless of the working directory uvicorn is started from.
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

SESSIONS_DIR = ROOT_DIR / "sessions"
