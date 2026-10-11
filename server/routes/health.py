"""Health and config endpoints."""
import httpx
from fastapi import APIRouter

from .. import config, llm, music

router = APIRouter(tags=["meta"])


@router.get("/api/health")
async def health():
    import asyncio

    localai, llm_status = await asyncio.gather(
        music.check_health(), llm.check_health()
    )
    return {"localai": localai, "llm": llm_status}


@router.get("/api/config")
def get_config():
    return {
        "music_model": config.MUSIC_MODEL,
        "image_model": config.IMAGE_MODEL,
        "llm_model": config.LLM_MODEL,
        "endpoints": {"localai": config.LOCALAI_URL, "llm": config.LLM_URL},
        "supports_extend": config.SUPPORTS_EXTEND,
    }
