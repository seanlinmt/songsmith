"""Standalone lyric generation + settings endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import config, llm

router = APIRouter(tags=["settings"])


class LyricsRequest(BaseModel):
    prompt: str


@router.post("/api/lyrics")
async def write_lyrics(req: LyricsRequest):
    try:
        lyrics = await generate_lyrics(req.prompt)
    except Exception as exc:
        raise HTTPException(502, f"LLM unavailable: {exc}") from exc
    if not lyrics:
        raise HTTPException(502, "LLM returned empty lyrics")
    return {"lyrics": lyrics}


@router.get("/api/settings")
def get_settings():
    return {
        "llm_model": config.LLM_MODEL,
        "music_model": config.MUSIC_MODEL,
        "image_model": config.IMAGE_MODEL,
        "endpoints": {"localai": config.LOCALAI_URL, "llm": config.LLM_URL},
    }
