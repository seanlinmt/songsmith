"""Curated + user-saved styles for the generation form.

STYLES mirrors Suno's `generate/get_recommend_styles/` (static curated list);
saved styles mirror `prompts/v2` (persisted user styles, SQLite-backed).
"""
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import db

router = APIRouter(prefix="/api/styles", tags=["styles"])

# Curated style presets: short tag lists + a rich one-line ACE-Step style
# description each.
STYLES: list[dict] = [
    {
        "name": "Hip Hop",
        "tags": ["hip hop", "boom bap", "rap"],
        "prompt": "Classic boom-bap hip hop with dusty sampled drums, deep upright bass, vinyl crackle and a confident rap vocal flow",
    },
    {
        "name": "Pop",
        "tags": ["pop", "catchy", "radio"],
        "prompt": "Bright modern pop with punchy drums, glossy synth layers, infectious hooks and a polished lead vocal",
    },
    {
        "name": "Rock",
        "tags": ["rock", "guitar", "energetic"],
        "prompt": "Driving alternative rock with overdriven electric guitars, thunderous live drums and an anthemic vocal delivery",
    },
    {
        "name": "R&B",
        "tags": ["r&b", "soulful", "smooth"],
        "prompt": "Smooth contemporary R&B with silky electric piano, laid-back groove, warm bass and an expressive soulful vocal",
    },
    {
        "name": "Jazz",
        "tags": ["jazz", "swing", "improvisation"],
        "prompt": "Late-night jazz with brushed drums, walking double bass, warm saxophone lead and sophisticated swing feel",
    },
    {
        "name": "Country",
        "tags": ["country", "acoustic", "storytelling"],
        "prompt": "Heartfelt country with acoustic strumming, pedal steel swells, steady train-beat drums and a warm storytelling vocal",
    },
    {
        "name": "Electronic",
        "tags": ["electronic", "dance", "synths"],
        "prompt": "Energetic electronic dance music with four-on-the-floor kick, soaring supersaw synths, sidechained bass and bright vocal chops",
    },
    {
        "name": "Ambient",
        "tags": ["ambient", "atmospheric", "calm"],
        "prompt": "Sparse ambient soundscapes with evolving analog pads, soft drones, distant textures and a slow meditative pulse",
    },
    {
        "name": "Metal",
        "tags": ["metal", "heavy", "distorted"],
        "prompt": "Aggressive metal with downtuned rhythm guitars, double-kick drumming, piercing lead lines and a powerful raw vocal",
    },
    {
        "name": "Folk",
        "tags": ["folk", "acoustic", "intimate"],
        "prompt": "Intimate folk with fingerpicked acoustic guitar, gentle mandolin, soft brushed percussion and a close honest vocal",
    },
    {
        "name": "Funk",
        "tags": ["funk", "groove", "bass"],
        "prompt": "Tight funk with slap bass, clipped rhythm guitar, punchy horn stabs and an energetic call-and-response vocal",
    },
    {
        "name": "Disco",
        "tags": ["disco", "dance", "strings"],
        "prompt": "Glamorous disco with four-on-the-floor groove, lush string section, funky rhythm guitar and a sparkling falsetto vocal",
    },
    {
        "name": "Lo-fi",
        "tags": ["lo-fi", "chill", "beats"],
        "prompt": "Chill lo-fi beats with muffled dusty drums, warm Rhodes chords, soft vinyl hiss and a sleepy unhurried groove",
    },
    {
        "name": "Synthwave",
        "tags": ["synthwave", "retro", "80s"],
        "prompt": "Retro 80s synthwave with gated-reverb drums, analog arpeggios, neon pads and a nostalgic driving bassline",
    },
    {
        "name": "Gospel",
        "tags": ["gospel", "choir", "uplifting"],
        "prompt": "Uplifting gospel with powerful Hammond organ, hand-clap groove, soaring choir harmonies and a passionate lead vocal",
    },
    {
        "name": "Bossa Nova",
        "tags": ["bossa nova", "latin", "jazzy"],
        "prompt": "Breezy bossa nova with nylon-string guitar, subtle latin percussion, jazzy seventh chords and a soft hushed vocal",
    },
]


class StyleCreate(BaseModel):
    name: str
    tags: list[str] = Field(default_factory=list)
    prompt: str


@router.get("")
def get_styles():
    return {"styles": STYLES, "saved": db.list_styles()}


@router.post("")
def save_style(req: StyleCreate):
    name = req.name.strip()
    if not name:
        raise HTTPException(400, "name must not be empty")
    existing = {s["name"].casefold() for s in db.list_styles()}
    if name.casefold() in existing:
        raise HTTPException(409, f"style '{name}' already exists")
    style_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO styles (id, name, tags, prompt, created_at) VALUES (?, ?, ?, ?, ?)",
        (style_id, name, json.dumps(req.tags), req.prompt, now),
    )
    return db.get_style(style_id)


@router.delete("/{style_id}")
def delete_style(style_id: str):
    style = db.get_style(style_id)
    if style is None:
        raise HTTPException(404, "style not found")
    db.execute("DELETE FROM styles WHERE id = ?", (style_id,))
    return {"ok": True}
