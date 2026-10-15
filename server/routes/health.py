"""Health and config endpoints."""
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import config, image, llm, music

router = APIRouter(tags=["meta"])


class SettingsUpdate(BaseModel):
    """PATCH /api/config body. Absent keys are left unchanged; null clears."""

    localai_url: str | None = None
    music_url: str | None = None
    image_url: str | None = None
    llm_url: str | None = None
    llm_model: str | None = None
    music_model: str | None = None
    image_model: str | None = None
    localai_api_key: str | None = None
    music_api_key: str | None = None
    image_api_key: str | None = None
    llm_api_key: str | None = None
    supports_extend: bool | None = None


@router.get("/api/health")
async def health():
    import asyncio

    localai, image_status, llm_status = await asyncio.gather(
        music.check_health(), image.check_health(), llm.check_health()
    )
    return {"localai": localai, "image": image_status, "llm": llm_status}


def _config_payload() -> dict:
    return {
        "music_model": config.MUSIC_MODEL,
        "image_model": config.IMAGE_MODEL,
        "llm_model": config.LLM_MODEL,
        "endpoints": {"music": config.MUSIC_URL, "image": config.IMAGE_URL, "llm": config.LLM_URL},
        "api_keys": {
            "music": config.MUSIC_API_KEY,
            "image": config.IMAGE_API_KEY,
            "llm": config.LLM_API_KEY,
        },
        "supports_extend": config.supports_extend(),
    }


@router.get("/api/config")
def get_config():
    return _config_payload()


@router.patch("/api/config")
def update_config(req: SettingsUpdate):
    """Persist settings overrides and apply them to the live module."""
    merged = config.load_overrides()

    for key in ("localai_url", "music_url", "image_url", "llm_url"):
        if key in req.model_fields_set:
            value = getattr(req, key)
            if value is not None and not value.startswith(("http://", "https://")):
                raise HTTPException(422, f"{key} must start with http:// or https://")
            merged[key] = value.rstrip("/") if value is not None else None

    for key in ("llm_model", "music_model", "image_model"):
        if key in req.model_fields_set:
            value = getattr(req, key)
            merged[key] = value.strip() if value is not None else None

    for key in ("localai_api_key", "music_api_key", "image_api_key", "llm_api_key"):
        if key in req.model_fields_set:
            value = getattr(req, key)
            merged[key] = value.strip() if value else None

    if "supports_extend" in req.model_fields_set:
        merged["supports_extend"] = req.supports_extend

    config.save_overrides(merged)
    config._apply_overrides(merged)
    return _config_payload()
