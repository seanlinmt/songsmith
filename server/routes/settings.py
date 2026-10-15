"""Standalone lyric generation + settings endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import config, llm
from .styles import STYLES

router = APIRouter(tags=["settings"])


class LyricsRequest(BaseModel):
    prompt: str
    tags: list[str] = []


class EnhancePromptRequest(BaseModel):
    prompt: str
    tags: list[str] = []


class TitleRequest(BaseModel):
    prompt: str
    lyrics: str | None = None
    tags: list[str] = []


class ExpandStyleRequest(BaseModel):
    prompt: str
    tags: list[str] = []


@router.post("/api/lyrics")
async def write_lyrics(req: LyricsRequest):
    try:
        lyrics, _title = await llm.generate_lyrics(req.prompt, req.tags)
    except Exception as exc:
        raise HTTPException(502, f"LLM unavailable: {exc}") from exc
    if not lyrics:
        raise HTTPException(502, "LLM returned empty lyrics")
    return {"lyrics": lyrics}


@router.post("/api/enhance-prompt")
async def enhance_prompt(req: EnhancePromptRequest):
    try:
        enhanced = await llm.enhance_description(req.prompt, req.tags)
    except Exception as exc:
        raise HTTPException(502, f"LLM unavailable: {exc}") from exc
    if not enhanced:
        raise HTTPException(502, "LLM returned empty result")
    return {"prompt": enhanced}


@router.post("/api/title")
async def generate_title(req: TitleRequest):
    title = await llm.generate_title(req.prompt, req.lyrics or "", tags=req.tags)
    # generate_title swallows errors and returns None by design; the frontend
    # treats an empty title as failure, so don't 502 here.
    return {"title": title or ""}


@router.post("/api/expand-style")
async def expand_style(req: ExpandStyleRequest):
    style, avoid = await llm.expand_style(req.prompt, req.tags)
    return {"style": style, "avoid": avoid}


@router.get("/api/settings")
def get_settings():
    return {
        "llm_model": config.LLM_MODEL,
        "music_model": config.MUSIC_MODEL,
        "image_model": config.IMAGE_MODEL,
        "endpoints": {"music": config.MUSIC_URL, "image": config.IMAGE_URL, "llm": config.LLM_URL},
        "api_keys": {"music": config.MUSIC_API_KEY, "image": config.IMAGE_API_KEY, "llm": config.LLM_API_KEY},
        "recommended_styles": STYLES,
    }
