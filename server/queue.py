"""In-process asyncio job runner with the per-variation generation pipeline.

Jobs are persisted in the DB so state survives page reloads.
- A small pool (max 2 concurrent) of worker tasks polls the jobs table.
- On startup, any 'running' job left over from a previous process is marked
  'error' with message 'interrupted by restart' (no in-process resume).
"""
import asyncio
import json
import logging
import random
import sys
import uuid
from datetime import datetime, timezone

from . import config, db, image, llm, music

log = logging.getLogger("songsmith.queue")

MAX_CONCURRENCY = 2
_POLL_INTERVAL = 0.5  # seconds between DB polls for queued jobs

_tasks: list[asyncio.Task] = []
_running: set[str] = set()  # job ids currently being processed


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _update_job(job_id: str, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = utcnow()
    sets = ", ".join(f"{k} = ?" for k in fields)
    db.execute(f"UPDATE jobs SET {sets} WHERE id = ?", (*fields.values(), job_id))


def _set_song(song_id: str, **fields) -> None:
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    db.execute(f"UPDATE songs SET {sets} WHERE id = ?", (*fields.values(), song_id))


def create_job(song_id: str, job_group_id: str, job_type: str) -> str:
    """Insert a queued job; returns job id."""
    job_id = str(uuid.uuid4())
    now = utcnow()
    db.execute(
        "INSERT INTO jobs (id, song_id, job_group_id, type, status, progress, message, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, 'queued', 0, NULL, ?, ?)",
        (job_id, song_id, job_group_id, job_type, now, now),
    )
    return job_id


def mark_interrupted_jobs() -> None:
    """On startup, fail jobs left 'running' by a previous process."""
    rows = db.query_all("SELECT id, song_id FROM jobs WHERE status = 'running'")
    for row in rows:
        db.execute(
            "UPDATE jobs SET status = 'error', message = 'interrupted by restart', updated_at = ? WHERE id = ?",
            (utcnow(), row["id"]),
        )
        db.execute(
            "UPDATE songs SET status = 'error', error = 'interrupted by restart' WHERE id = ?",
            (row["song_id"],),
        )
    if rows:
        log.warning("marked %d stale job(s) as interrupted", len(rows))


async def _run_generation(job: dict) -> None:
    """Full pipeline for one song variation."""
    job_id = job["id"]
    song = db.get_song(job["song_id"])
    if song is None:
        raise RuntimeError(f"song {job['song_id']} not found")

    song_id = song["id"]
    prompt = song["prompt"] or "music"
    lyrics = song["lyrics"] or ""
    instrumental = song["instrumental"]
    duration = song["duration_seconds"] or 60
    seed = song["seed"]

    # 1. Lyrics via LLM if needed (also yields a title in the same call)
    llm_title: str | None = None
    tags = song.get("tags") or []
    if not instrumental and not lyrics:
        _update_job(job_id, progress=0.1, message="writing lyrics")
        lyrics, llm_title = await llm.generate_lyrics(prompt, tags=tags)
        if not lyrics:
            raise RuntimeError("LLM returned empty lyrics; provide lyrics or mark instrumental")
        _set_song(song_id, lyrics=lyrics)

    # 2. Title: reuse the one from the lyrics call; separate call only as fallback
    _update_job(job_id, progress=0.2, message="naming song")
    if not song.get("title"):
        title = llm_title
        if not title:
            title = await llm.generate_title(prompt, lyrics, tags=tags)
        if not title:
            title = f"Untitled {datetime.now().strftime('%Y-%m-%d')}"
        _set_song(song_id, title=title)

    # 2.5. Style expansion: enrich short tags into a full style description
    #      plus negative tags (styles to avoid). Best-effort / cached on row.
    style_prompt: str | None = song.get("style_prompt")
    negative_tags: list[str] = song.get("negative_tags") or []
    if tags:
        _update_job(job_id, progress=0.25, message="expanding style")
        style, neg = await llm.expand_style(prompt, tags)
        style_prompt = style
        negative_tags = neg
        _set_song(song_id, style_prompt=style, negative_tags=json.dumps(neg))

    # 3. Music generation (FLAC master + optional wav transcode inside music.py)
    _update_job(job_id, progress=0.3, message="generating music")
    result = await music.generate(
        song_id=song_id,
        prompt=prompt,
        lyrics=lyrics,
        instrumental=instrumental,
        duration=duration,
        seed=seed,
        style_prompt=style_prompt,
        negative_tags=negative_tags,
    )

    # 4. Update song row (audio done)
    _set_song(
        song_id,
        status="done",
        audio_path=result["audio_path"],
        duration_seconds=result["duration_seconds"] or duration,
    )

    # 5. Cover art — separate, best-effort, non-blocking for audio
    _update_job(job_id, progress=0.8, message="generating cover art")
    try:
        await image.generate_cover(
            db.cover_file_path(song_id),
            title=(song.get("title") or llm_title),
            tags=tags,
            lyrics=lyrics,
            prompt=prompt,
        )
        _set_song(song_id, cover_path=f"covers/{song_id}.png")
    except Exception:
        log.exception("cover generation failed for song %s (audio is fine)", song_id)


async def _run_extend(job: dict) -> None:
    """Extended version of a parent song."""
    job_id = job["id"]
    song = db.get_song(job["song_id"])
    if song is None:
        raise RuntimeError(f"song {job['song_id']} not found")
    parent = db.get_song(song["parent_id"]) if song.get("parent_id") else None
    if parent is None:
        raise RuntimeError("parent song not found")

    song_id = song["id"]
    duration = song["duration_seconds"] or (parent.get("duration_seconds") or 60) * 2
    seed = song["seed"]

    _update_job(job_id, progress=0.2, message="extending song")
    parent_neg = parent.get("negative_tags")
    if isinstance(parent_neg, str):
        try:
            parent_neg = json.loads(parent_neg)
        except (TypeError, json.JSONDecodeError):
            parent_neg = []
    result = await music.generate(
        song_id=song_id,
        prompt=parent["prompt"] or "music",
        lyrics=parent["lyrics"] or "",
        instrumental=parent["instrumental"],
        duration=duration,
        seed=seed,
        style_prompt=parent.get("style_prompt"),
        negative_tags=parent_neg or [],
    )
    _set_song(
        song_id,
        status="done",
        audio_path=result["audio_path"],
        duration_seconds=result["duration_seconds"] or duration,
        title=parent.get("title", "") + " (extended)" if parent.get("title") else "Extended",
    )


async def _process_job(job: dict) -> None:
    _update_job(job_id=job["id"], status="running", progress=0.0, message="starting")
    try:
        if job["type"] == "extend":
            await _run_extend(job)
        else:  # 'generate' | 'regenerate'
            await _run_generation(job)
        _update_job(job_id=job["id"], status="done", progress=1.0, message="done")
    except Exception as exc:  # noqa: BLE001 - any failure fails the job
        log.exception("job %s failed", job["id"])
        msg = str(exc) or type(exc).__name__
        _update_job(job_id=job["id"], status="error", message=msg)
        _set_song(job["song_id"], status="error", error=msg)


async def _worker() -> None:
    while True:
        try:
            claimed = None
            if len(_running) < MAX_CONCURRENCY:
                rows = db.query_all(
                    "SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT ?",
                    (MAX_CONCURRENCY - len(_running),),
                )
                for row in rows:
                    if row["id"] in _running:
                        continue
                    claimed = row
                    break
            if claimed is None:
                await asyncio.sleep(_POLL_INTERVAL)
                continue
            _running.add(claimed["id"])
            task = asyncio.create_task(_process_job(claimed))
            task.add_done_callback(lambda t, jid=claimed["id"]: _running.discard(jid))
            await asyncio.sleep(0)
        except asyncio.CancelledError:
            raise
        except Exception:  # keep the worker alive on unexpected DB errors
            log.exception("worker loop error")
            await asyncio.sleep(1)


def start_workers() -> None:
    mark_interrupted_jobs()
    for _ in range(MAX_CONCURRENCY):
        _tasks.append(asyncio.create_task(_worker()))
    print(f"[queue] started {MAX_CONCURRENCY} job worker(s)", file=sys.stderr)


async def stop_workers() -> None:
    for t in _tasks:
        t.cancel()
    if _tasks:
        await asyncio.gather(*_tasks, return_exceptions=True)
    _tasks.clear()
