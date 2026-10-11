"""Song CRUD + create/regenerate/extend endpoints."""
import asyncio
import json
import random
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .. import config, db, image
from ..queue import create_job

router = APIRouter(prefix="/api/songs", tags=["songs"])

# Suno clip status lifecycle; `status` field stays as-is for backward compat.
STATUS_MAP = {
    "queued": "queued",
    "running": "streaming",
    "done": "complete",
    "error": "error",
}


def _song_public(song: dict) -> dict:
    out = {k: song[k] for k in (
        "id", "created_at", "title", "prompt", "lyrics", "tags",
        "instrumental", "model", "seed", "duration_seconds", "status",
        "error", "job_group_id", "parent_id", "kind", "style_prompt",
        "vocal_gender", "style_influence", "weirdness", "variety",
        "continue_at",
    ) if k in song}
    out["negative_tags"] = song.get("negative_tags") or []
    out["suno_status"] = STATUS_MAP.get(song.get("status"), song.get("status"))
    out["audio_url"] = f"/files/{song['audio_path']}" if song.get("audio_path") else None
    cover_url = f"/files/{song['cover_path']}" if song.get("cover_path") else None
    if cover_url:
        # Cache-bust: cover file is overwritten in place on regeneration, so
        # append mtime so browsers refetch instead of serving the stale image.
        p = config.DATA_DIR / song["cover_path"]
        try:
            cover_url = f"{cover_url}?v={int(p.stat().st_mtime)}"
        except OSError:
            pass
    out["cover_url"] = cover_url
    return out


class SongCreate(BaseModel):
    prompt: str
    lyrics: str = ""
    tags: list[str] = Field(default_factory=list)
    negative_tags: list[str] = Field(default_factory=list)
    instrumental: bool = False
    make_instrumental: bool | None = None
    duration_seconds: int = 60
    batch_size: int = 1
    title: str = ""
    vocal_gender: str | None = None
    style_influence: float | None = None
    weirdness: float | None = None
    variety: int | None = None


class ExtendRequest(BaseModel):
    duration_seconds: int
    continue_at: int | None = None  # seconds into the parent to continue from
    infill_start_s: int | None = None
    infill_end_s: int | None = None


@router.post("")
def create_song(req: SongCreate):
    group_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    instrumental = bool(req.instrumental or (req.make_instrumental or False))
    created = []
    for _ in range(max(1, min(req.batch_size, 4))):  # cap 4 per request
        song_id = str(uuid.uuid4())
        seed = random.randint(0, 2**31 - 1)
        db.execute(
            "INSERT INTO songs (id, created_at, title, prompt, lyrics, tags, negative_tags,"
            " style_prompt, vocal_gender, style_influence, weirdness, variety, continue_at,"
            " instrumental, model, seed, duration_seconds, status,"
            " audio_path, cover_path, error, job_group_id, parent_id, kind)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, NULL, ?, ?, ?, ?, 'queued', NULL, NULL, NULL, ?, NULL, 'song')",
            (song_id, now, req.title or '', req.prompt, req.lyrics,
             json.dumps(req.tags), json.dumps(req.negative_tags),
             req.vocal_gender, req.style_influence, req.weirdness, req.variety,
             int(instrumental),
             config.MUSIC_MODEL, seed, req.duration_seconds, group_id),
        )
        create_job(song_id, group_id, "generate")
        created.append({"id": song_id, "job_group_id": group_id, "status": "queued"})
    return {"job_group_id": group_id, "songs": created}


@router.get("")
def list_songs():
    return [_song_public(s) for s in db.list_songs()]


@router.get("/{song_id}")
def get_song(song_id: str):
    song = db.get_song(song_id)
    if song is None:
        raise HTTPException(404, "song not found")
    return _song_public(song)


@router.delete("/{song_id}")
def delete_song(song_id: str):
    song = db.get_song(song_id)
    if song is None:
        raise HTTPException(404, "song not found")
    db.execute("DELETE FROM jobs WHERE song_id = ?", (song_id,))
    db.execute("DELETE FROM songs WHERE id = ?", (song_id,))
    for name in (f"audio/{song_id}.wav", f"audio/{song_id}.flac", f"audio/{song_id}.mp3",
                  f"covers/{song_id}.png"):
        p = config.DATA_DIR / name
        if p.exists():
            p.unlink()
    return {"ok": True}


@router.post("/{song_id}/regenerate")
def regenerate_song(song_id: str):
    src = db.get_song(song_id)
    if src is None:
        raise HTTPException(404, "song not found")
    group_id = str(uuid.uuid4())
    new_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    seed = random.randint(0, 2**31 - 1)
    db.execute(
        "INSERT INTO songs (id, created_at, title, prompt, lyrics, tags, negative_tags,"
        " style_prompt, vocal_gender, style_influence, weirdness, variety, continue_at,"
        " instrumental, model, seed, duration_seconds, status,"
        " audio_path, cover_path, error, job_group_id, parent_id, kind)"
        " VALUES (?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, 'queued', NULL, NULL, NULL, ?, NULL, 'song')",
        (new_id, now, src["prompt"], src["lyrics"], json.dumps(src["tags"]),
         json.dumps(src.get("negative_tags") or []), src.get("style_prompt"),
         src.get("vocal_gender"), src.get("style_influence"),
         src.get("weirdness"), src.get("variety"),
         int(src["instrumental"]), src.get("model") or config.MUSIC_MODEL,
         seed, src.get("duration_seconds") or 60, group_id),
    )
    create_job(new_id, group_id, "regenerate")
    return {"job_group_id": group_id, "songs": [{"id": new_id, "job_group_id": group_id, "status": "queued"}]}


@router.post("/{song_id}/extend")
def extend_song(song_id: str, req: ExtendRequest):
    if not config.SUPPORTS_EXTEND:
        raise HTTPException(400, "extend not supported by model")
    src = db.get_song(song_id)
    if src is None:
        raise HTTPException(404, "song not found")
    group_id = str(uuid.uuid4())
    new_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    seed = random.randint(0, 2**31 - 1)
    db.execute(
        "INSERT INTO songs (id, created_at, title, prompt, lyrics, tags, negative_tags,"
        " style_prompt, vocal_gender, style_influence, weirdness, variety, continue_at,"
        " instrumental, model, seed, duration_seconds, status,"
        " audio_path, cover_path, error, job_group_id, parent_id, kind)"
        " VALUES (?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', NULL, NULL, NULL, ?, ?, 'extended')",
        (new_id, now, src["prompt"], src["lyrics"], json.dumps(src["tags"]),
         json.dumps(src.get("negative_tags") or []), src.get("style_prompt"),
         src.get("vocal_gender"), src.get("style_influence"),
         src.get("weirdness"), src.get("variety"),
         req.continue_at if req.continue_at is not None else src.get("continue_at"),
         int(src["instrumental"]), src.get("model") or config.MUSIC_MODEL,
         seed, req.duration_seconds, group_id, song_id),
    )
    create_job(new_id, group_id, "extend")
    return {"job_group_id": group_id, "songs": [{"id": new_id, "job_group_id": group_id, "status": "queued"}]}


@router.post("/{song_id}/cover")
async def regenerate_cover(song_id: str):
    """Regenerate cover art only — audio and job state are untouched."""
    song = db.get_song(song_id)
    if song is None:
        raise HTTPException(404, "song not found")
    try:
        await image.generate_cover(
            db.cover_file_path(song_id),
            title=song.get("title") or None,
            tags=song.get("tags") or [],
            lyrics=song.get("lyrics") or None,
            prompt=song.get("prompt") or None,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced as 502
        raise HTTPException(502, f"cover generation failed: {exc}") from exc
    db.execute("UPDATE songs SET cover_path = ? WHERE id = ?",
               (f"covers/{song_id}.png", song_id))
    return _song_public(db.get_song(song_id))


# ---- lyrics: structured read + inline edit (word-level timing comes later) ----

_SECTION_HEADER_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_KNOWN_SECTIONS = {"intro", "verse", "pre-chorus", "chorus", "bridge", "hook", "outro"}


def _parse_sections(lyrics: str) -> list[dict]:
    """Split lyrics on [tag] headers into {'tag', 'lines'} sections.

    Known section tags are lowercased; unknown tags are kept as-is.
    Lines before the first header are ignored.
    """
    sections: list[dict] = []
    current: dict | None = None
    for line in lyrics.splitlines():
        m = _SECTION_HEADER_RE.match(line)
        if m:
            raw = m.group(1).strip()
            tag = raw.casefold() if raw.casefold() in _KNOWN_SECTIONS else raw
            current = {"tag": tag, "lines": []}
            sections.append(current)
        elif current is not None and line.strip():
            current["lines"].append(line)
    return sections


@router.get("/{song_id}/lyrics")
def get_song_lyrics(song_id: str):
    song = db.get_song(song_id)
    if song is None:
        raise HTTPException(404, "song not found")
    lyrics = song.get("lyrics") or ""
    return {"id": song_id, "lyrics": lyrics, "sections": _parse_sections(lyrics)}


class LyricsUpdate(BaseModel):
    lyrics: str


@router.post("/{song_id}/lyrics")
def update_song_lyrics(song_id: str, req: LyricsUpdate):
    song = db.get_song(song_id)
    if song is None:
        raise HTTPException(404, "song not found")
    db.execute("UPDATE songs SET lyrics = ? WHERE id = ?", (req.lyrics, song_id))
    return _song_public(db.get_song(song_id))


def _mp3_filename(song: dict) -> str:
    base = re.sub(r"[^\w\s-]", "", song.get("title") or "").strip()
    if not base:
        base = song["id"]
    return f"{base}.mp3"


@router.get("/{song_id}/mp3")
async def download_song_mp3(song_id: str):
    """Serve an MP3 transcode of the song, caching the result in data/audio."""
    song = db.get_song(song_id)
    if song is None:
        raise HTTPException(404, "song not found")

    audio_dir = config.DATA_DIR / "audio"
    mp3_path = audio_dir / f"{song_id}.mp3"

    if not mp3_path.exists():
        wav = audio_dir / f"{song_id}.wav"
        flac = audio_dir / f"{song_id}.flac"
        src = wav if wav.exists() else (flac if flac.exists() else None)
        if src is None:
            # fall back to whatever the db row points at (e.g. another extension)
            rel = song.get("audio_path")
            if rel:
                cand = config.DATA_DIR / rel
                if cand.exists() and cand != wav and cand != flac:
                    src = cand
        if src is None:
            raise HTTPException(404, "no audio file for song")

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(src),
            "-codec:a", "libmp3lame", "-qscale:a", "2", str(mp3_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode != 0 or not mp3_path.exists():
            mp3_path.unlink(missing_ok=True)
            raise HTTPException(500, "ffmpeg transcode failed")

    return FileResponse(mp3_path, media_type="audio/mpeg", filename=_mp3_filename(song))
