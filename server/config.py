"""Configuration loaded from .env via python-dotenv, with optional overrides.

Runtime overrides live in DATA_DIR/"settings.json" (written by PATCH /api/config).
They are applied at import and can be mutated live via the module attributes.
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (parent of server/).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _get(key: str, default: str) -> str:
    return os.environ.get(key, default).strip()


def _strip_url(url: str) -> str:
    return url.strip().rstrip("/")


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

# Keys that may be overridden via settings.json (supports_extend: bool | null).
_OVERRIDE_KEYS = ("localai_url", "llm_url", "llm_model", "music_model", "image_model")

# Cached supports_extend override: None means "no override, derive from model".
_SUPPORTS_EXTEND_OVERRIDE: bool | None = None


def _apply_overrides(settings: dict) -> None:
    """Overlay settings.json values onto module constants. Null/missing = no override."""
    global LOCALAI_URL, LLM_URL, LLM_MODEL, MUSIC_MODEL, IMAGE_MODEL
    global _SUPPORTS_EXTEND_OVERRIDE
    if "localai_url" in settings and settings["localai_url"] is not None:
        LOCALAI_URL = _strip_url(str(settings["localai_url"]))
    if "llm_url" in settings and settings["llm_url"] is not None:
        LLM_URL = _strip_url(str(settings["llm_url"]))
    if "llm_model" in settings and settings["llm_model"] is not None:
        LLM_MODEL = str(settings["llm_model"]).strip()
    if "music_model" in settings and settings["music_model"] is not None:
        MUSIC_MODEL = str(settings["music_model"]).strip()
    if "image_model" in settings and settings["image_model"] is not None:
        IMAGE_MODEL = str(settings["image_model"]).strip()
    if "supports_extend" in settings:
        value = settings["supports_extend"]
        _SUPPORTS_EXTEND_OVERRIDE = None if value is None else bool(value)


def _load_override_file() -> dict:
    """Read settings.json from the resolved DATA_DIR, if present."""
    path = DATA_DIR / "settings.json"
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_overrides() -> dict:
    """Load persisted overrides from DATA_DIR/"settings.json" (empty dict if none)."""
    return _load_override_file()


def save_overrides(settings: dict) -> None:
    """Persist the full overrides dict to DATA_DIR/"settings.json" atomically.

    Only keys actually set are written; supports_extend may be explicitly null
    to clear the override.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "settings.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(settings, indent=2) + "\n")
    os.replace(tmp, path)


# Apply any persisted overrides on import (settings.json lives in the resolved
# DATA_DIR, so this happens after DATA_DIR resolution above).
_apply_overrides(_load_override_file())


def ensure_dirs() -> None:
    """Create data/ subdirectories on startup."""
    (DATA_DIR / "audio").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "covers").mkdir(parents=True, exist_ok=True)


def supports_extend() -> bool:
    """Whether the current model supports extend, honoring any override."""
    if _SUPPORTS_EXTEND_OVERRIDE is not None:
        return _SUPPORTS_EXTEND_OVERRIDE
    return MUSIC_MODEL == "ace-step-turbo"
