"""Configuration loaded from .env via python-dotenv."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (parent of server/).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _get(key: str, default: str) -> str:
    return os.environ.get(key, default).strip()


LOCALAI_URL = _get("LOCALAI_URL", "http://127.0.0.1:7777").rstrip("/")
LLM_URL = _get("LLM_URL", "http://127.0.0.1:18888").rstrip("/")
LLM_MODEL = _get("LLM_MODEL", "GLM-5.3-Flash-EXL3")
MUSIC_MODEL = _get("MUSIC_MODEL", "ace-step-turbo")
IMAGE_MODEL = _get("IMAGE_MODEL", "flux.2-klein-4b")
DATA_DIR = Path(_get("DATA_DIR", "data"))
if not DATA_DIR.is_absolute():
    DATA_DIR = _PROJECT_ROOT / DATA_DIR

HOST = _get("HOST", "127.0.0.1")
PORT = int(_get("PORT", "8788"))


def ensure_dirs() -> None:
    """Create data/ subdirectories on startup."""
    (DATA_DIR / "audio").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "covers").mkdir(parents=True, exist_ok=True)


SUPPORTS_EXTEND = MUSIC_MODEL == "ace-step-turbo"
