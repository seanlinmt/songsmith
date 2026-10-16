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


def _localai_headers() -> dict:
    return {"Authorization": f"Bearer {config.MUSIC_API_KEY}"} if config.MUSIC_API_KEY else {}


async def check_health() -> dict:
    """Cheap liveness probe for /api/health: does LocalAI answer /v1/models?"""
    try:
        async with httpx.AsyncClient(headers=_localai_headers()) as client:
            resp = await client.get(
                f"{config.MUSIC_URL}/v1/models", timeout=httpx.Timeout(3.0)
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
    vocal_gender: str | None = None,
) -> bytes:
    """Single point of truth for the ACE-Step request format.

    Returns the raw response bytes (FLAC).
    """
    sent_prompt = style_prompt or prompt
    if vocal_gender:
        # ACE-Step has no verified vocal-gender field; hint it via the prompt.
        sent_prompt = f"{sent_prompt}, {vocal_gender} vocals"
    payload = {
        "model": config.MUSIC_MODEL,
        # style_prompt is a richer replacement for the raw prompt
        "prompt": sent_prompt,
        "duration_seconds": duration,
        "seed": seed,
    }
    if not instrumental:
        payload["lyrics"] = lyrics  # omitted entirely when instrumental
    if negative_tags:
        payload["negative_prompt"] = ", ".join(negative_tags)

    async def _post() -> httpx.Response:
        return await client.post(
            f"{config.MUSIC_URL}/v1/sound-generation",
            json=payload,
            timeout=_TIMEOUT,
        )

    def _err(resp: httpx.Response) -> RuntimeError:
        # The 500 body names the real cause (e.g. "Generation produced NaN or
        # Inf latents …" from the ACE-Step backend) — never discard it.
        return RuntimeError(
            f"sound-generation HTTP {resp.status_code}: {resp.text[:500]}"
        )

    async with httpx.AsyncClient(headers=_localai_headers()) as client:
        resp = await _post()
        if resp.status_code >= 400 and "negative_prompt" in payload:
            # Older builds may reject the unknown field: retry once without it.
            log.warning("sound-generation rejected negative_prompt (%d); retrying without it", resp.status_code)
            payload.pop("negative_prompt")
            resp = await _post()
        if resp.status_code == 500:
            # Remote ACE-Step can hit fp16 NaN latents for certain
            # (lyrics, seed) pairs; a fresh seed sometimes clears it.
            # NOTE: on hosts with the fp16 overflow the NaN rate for real
            # lyrics approaches 100% — the real fix is server-side
            # (ACESTEP_DTYPE=float32 or --backend pt). Keep this cheap: one
            # retry, so failed jobs surface the server error quickly.
            body = resp.text[:200]
            if "NaN" in body or "nan" in body:
                import random

                fresh = random.randrange(1, 2**31)
                log.warning(
                    "sound-generation NaN latents (seed=%s); retrying once with seed=%s",
                    payload.get("seed"), fresh,
                )
                payload["seed"] = fresh
                resp = await _post()
        if resp.status_code >= 400:
            raise _err(resp)
        content = resp.content
        if not (content.startswith(b"fLaC") or content.startswith(b"RIFF")):
            log.warning("sound-generation response lacks audio magic (%d bytes)", len(content))
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
    vocal_gender: str | None = None,
) -> dict:
    """Generate music for a song and persist it.

    Returns {"audio_path": "audio/<id>.wav"|".flac", "duration_seconds": int|None}.
    The .flac master is always kept; .wav (when ffmpeg is available) is the
    preferred playback copy.
    """
    flac_bytes = await request_ace_step(
        prompt, lyrics, instrumental, duration, seed,
        style_prompt=style_prompt, negative_tags=negative_tags,
        vocal_gender=vocal_gender,
    )

    if flac_bytes.startswith(b"RIFF"):
        wav_path = config.DATA_DIR / "audio" / f"{song_id}.wav"
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        wav_path.write_bytes(flac_bytes)
        audio_path = f"audio/{song_id}.wav"
    else:
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
    if duration_seconds is not None and abs(duration_seconds - duration) > 5:
        log.warning(
            "song %s: requested %ds but ACE-Step produced %ds",
            song_id, duration, duration_seconds,
        )
    else:
        log.info(
            "song %s: duration ok (requested %ds, got %s)",
            song_id, duration, duration_seconds,
        )
    return {"audio_path": audio_path, "duration_seconds": duration_seconds}
