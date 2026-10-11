"""ACE-Step music generation via LocalAI.

Verified contract (docs/api-notes.md):
- POST /v1/sound-generation, HTTP 200, raw FLAC bytes (24-bit, 48 kHz stereo).
- For instrumental songs the `lyrics` key is OMITTED entirely (prompt-only).
- Save FLAC master to data/audio/<song_id>.flac; if ffmpeg is on PATH,
  transcode to wav and prefer the wav as audio_path (flac kept as master).
- Duration via ffprobe; do NOT use stdlib `wave` (response is FLAC).

`request_ace_step()` is kept as a single small function so the request
format stays trivial to correct.
"""
import asyncio
import logging
import shutil

import httpx

from . import config

log = logging.getLogger("songsmith.music")

# Cold model load measured at 7m40s; warm ~2.3x realtime.
_TIMEOUT = httpx.Timeout(900.0, connect=10.0)


async def check_health() -> dict:
    """Cheap liveness probe for /api/health: does LocalAI answer /v1/models?"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{config.LOCALAI_URL}/v1/models", timeout=httpx.Timeout(3.0)
            )
            resp.raise_for_status()
            models = [m.get("id") for m in resp.json().get("data", [])]
            return {"up": True, "models": models}
    except Exception as exc:
        return {"up": False, "error": f"{type(exc).__name__}: {exc}"}


async def request_ace_step(
    prompt: str, lyrics: str, instrumental: bool,
    duration: int, seed: int | None,
    style_prompt: str | None = None,
    negative_tags: list[str] | None = None,
) -> bytes:
    """Single point of truth for the ACE-Step request format.

    Returns the raw response bytes (FLAC).
    """
    payload = {
        "model": config.MUSIC_MODEL,
        # style_prompt is a richer replacement for the raw prompt
        "prompt": style_prompt or prompt,
        "duration_seconds": duration,
        "seed": seed,
    }
    if not instrumental:
        payload["lyrics"] = lyrics  # omitted entirely when instrumental
    if negative_tags:
        payload["negative_prompt"] = ", ".join(negative_tags)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{config.LOCALAI_URL}/v1/sound-generation",
                json=payload,
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            if "negative_prompt" not in payload:
                raise
            # Older builds may reject the unknown field: retry once without it.
            log.warning("sound-generation rejected negative_prompt; retrying without it")
            payload.pop("negative_prompt")
            resp = await client.post(
                f"{config.LOCALAI_URL}/v1/sound-generation",
                json=payload,
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
        content = resp.content
        if not content.startswith(b"fLaC"):
            log.warning("sound-generation response lacks fLaC magic (%d bytes)", len(content))
        return content


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


async def _transcode_to_wav(flac_path, wav_path) -> bool:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", str(flac_path), str(wav_path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    return proc.returncode == 0 and wav_path.exists()


async def _probe_duration(path) -> int | None:
    if shutil.which("ffprobe") is None:
        return None
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        return int(float(out.decode().strip()))
    except Exception:
        log.exception("ffprobe duration failed for %s", path)
        return None


async def generate(
    song_id: str, prompt: str, lyrics: str, instrumental: bool,
    duration: int, seed: int | None,
    style_prompt: str | None = None,
    negative_tags: list[str] | None = None,
) -> dict:
    """Generate music for a song and persist it.

    Returns {"audio_path": "audio/<id>.wav"|".flac", "duration_seconds": int|None}.
    The .flac master is always kept; .wav (when ffmpeg is available) is the
    preferred playback copy.
    """
    flac_bytes = await request_ace_step(
        prompt, lyrics, instrumental, duration, seed,
        style_prompt=style_prompt, negative_tags=negative_tags,
    )

    flac_path = config.DATA_DIR / "audio" / f"{song_id}.flac"
    flac_path.parent.mkdir(parents=True, exist_ok=True)
    flac_path.write_bytes(flac_bytes)

    audio_path = f"audio/{song_id}.flac"
    if _ffmpeg_available():
        wav_path = config.DATA_DIR / "audio" / f"{song_id}.wav"
        if await _transcode_to_wav(flac_path, wav_path):
            audio_path = f"audio/{song_id}.wav"
        else:
            log.warning("ffmpeg transcode failed for %s; serving flac master", song_id)
            wav_path.unlink(missing_ok=True)
    else:
        log.warning("ffmpeg not on PATH; keeping flac master only for %s", song_id)

    duration_seconds = await _probe_duration(
        config.DATA_DIR / audio_path.replace("/", "/")
    )
    return {"audio_path": audio_path, "duration_seconds": duration_seconds}
