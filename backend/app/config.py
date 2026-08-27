from pathlib import Path

from dotenv import load_dotenv
import os

# Single .env lives at the repo root, not inside backend/ — load it explicitly
# so this works regardless of the working directory uvicorn is started from.
#
# override=True because this file really is the single source of truth for a local-only dev app:
# without it, a stale value exported in the developer's shell silently wins over the .env, and
# you get confusing 404s from a provider about a model the .env no longer names.
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env", override=True)

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

SESSIONS_DIR = ROOT_DIR / "sessions"
