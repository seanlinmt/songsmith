"""Health and config endpoints."""
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import config, llm, music

router = APIRouter(tags=["meta"])


class SettingsUpdate(BaseModel):
    """PATCH /api/config body. Absent keys are left unchanged; null clears."""

    localai_url: str | None = None
    llm_url: str | None = None
    llm_model: str | None = None
    music_model: str | None = None
    image_model: str | None = None
    supports_extend: bool | None = None


@router.get("/api/health")
async def health():
    import asyncio

    localai, llm_status = await asyncio.gather(
        music.check_health(), llm.check_health()
    )
    return {"localai": localai, "llm": llm_status}


def _config_payload() -> dict:
    return {
        "music_model": config.MUSIC_MODEL,
        "image_model": config.IMAGE_MODEL,
        "llm_model": config.LLM_MODEL,
        "endpoints": {"localai": config.LOCALAI_URL, "llm": config.LLM_URL},
        "supports_extend": config.supports_extend(),
    }


@router.get("/api/config")
def get_config():
    return _config_payload()


@router.patch("/api/config")
def update_config(req: SettingsUpdate):
    """Persist settings overrides and apply them to the live module."""
    merged = config.load_overrides()

    for key in ("localai_url", "llm_url"):
        if key in req.model_fields_set:
            value = getattr(req, key)
            if value is not None and not value.startswith(("http://", "https://")):
                raise HTTPException(422, f"{key} must start with http:// or https://")
            merged[key] = value.rstrip("/") if value is not None else None

    for key in ("llm_model", "music_model", "image_model"):
        if key in req.model_fields_set:
            value = getattr(req, key)
            merged[key] = value.strip() if value is not None else None

    if "supports_extend" in req.model_fields_set:
        merged["supports_extend"] = req.supports_extend

    config.save_overrides(merged)
    config._apply_overrides(merged)
    return _config_payload()
