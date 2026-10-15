"""Configuration: code defaults + data/settings.json overrides.

All service settings (endpoints, models, API keys, capabilities) are edited
via the Settings page (PATCH /api/config) and persisted to
DATA_DIR/"settings.json". Only process-bootstrap values (HOST, PORT,
DATA_DIR) still come from the environment — they are needed before the
server (and therefore the Settings page) can run.
"""
import json
import os
from pathlib import Path

# Bootstrap (not exposed on the Settings page — the server must be running
# to serve it). Plain environment variables; .env is no longer auto-loaded.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _get(key: str, default: str) -> str:
    return os.environ.get(key, default).strip()


DATA_DIR = Path(_get("DATA_DIR", "data"))
if not DATA_DIR.is_absolute():
    DATA_DIR = _PROJECT_ROOT / DATA_DIR


def _strip_url(url: str) -> str:
    return url.strip().rstrip("/")


# ---- code defaults (settings.json takes precedence) ----
DEFAULTS = {
    "localai_url": "http://127.0.0.1:7777",
    "llm_url": "http://127.0.0.1:18888",
    "llm_model": "GLM-5.3-Flash-EXL3",
    "music_model": "ace-step-turbo",
    "image_model": "flux.2-klein-4b",
}

# Live module state, seeded from DEFAULTS then overlaid with settings.json.
LOCALAI_URL = DEFAULTS["localai_url"]
# Per-service endpoints fall back to the shared LocalAI URL when unset.
MUSIC_URL = LOCALAI_URL
IMAGE_URL = LOCALAI_URL
LLM_URL = DEFAULTS["llm_url"]
LLM_MODEL = DEFAULTS["llm_model"]
MUSIC_MODEL = DEFAULTS["music_model"]
IMAGE_MODEL = DEFAULTS["image_model"]
# API keys: music/image fall back to the shared LocalAI key when unset.
LOCALAI_API_KEY = ""
MUSIC_API_KEY = ""
IMAGE_API_KEY = ""
LLM_API_KEY = ""

HOST = _get("HOST", "127.0.0.1")
PORT = int(_get("PORT", "8788"))


def _apply_overrides(settings: dict) -> None:
    """Overlay settings.json values onto module state. Null/missing = default."""
    global LOCALAI_URL, MUSIC_URL, IMAGE_URL, LLM_URL
    global LLM_MODEL, MUSIC_MODEL, IMAGE_MODEL
    global LOCALAI_API_KEY, MUSIC_API_KEY, IMAGE_API_KEY, LLM_API_KEY
    global _SUPPORTS_EXTEND_OVERRIDE

    def _pick(key: str, default: str) -> str:
        value = settings.get(key)
        return _strip_url(str(value)) if value else default

    LOCALAI_URL = _pick("localai_url", DEFAULTS["localai_url"])
    MUSIC_URL = _pick("music_url", LOCALAI_URL)
    IMAGE_URL = _pick("image_url", LOCALAI_URL)
    LLM_URL = _pick("llm_url", DEFAULTS["llm_url"])

    LLM_MODEL = str(settings.get("llm_model") or DEFAULTS["llm_model"]).strip()
    MUSIC_MODEL = str(settings.get("music_model") or DEFAULTS["music_model"]).strip()
    IMAGE_MODEL = str(settings.get("image_model") or DEFAULTS["image_model"]).strip()

    LOCALAI_API_KEY = str(settings.get("localai_api_key") or "").strip()
    MUSIC_API_KEY = str(settings.get("music_api_key") or LOCALAI_API_KEY).strip()
    IMAGE_API_KEY = str(settings.get("image_api_key") or LOCALAI_API_KEY).strip()
    LLM_API_KEY = str(settings.get("llm_api_key") or "").strip()

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
