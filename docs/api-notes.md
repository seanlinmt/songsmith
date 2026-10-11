# Verified API notes for server/music.py (from live LocalAI tests)

## Music generation — CONFIRMED working
POST {LOCALAI_URL}/v1/sound-generation
Request JSON:
```json
{
  "model": "ace-step-turbo",
  "prompt": "dreamy synth-pop, female vocals, airy pads, 110 bpm",
  "lyrics": "[verse]\nNeon lights...\n[chorus]\nHold the night...",
  "duration_seconds": 15,
  "seed": 7
}
```
- For instrumental: **omit the `lyrics` key entirely** (prompt-only).
- Response: HTTP 200, raw **FLAC bytes** (`fLaC` magic, 24-bit, 48 kHz stereo). NOT wav.
- Measured: 10 s audio cold = 7m40s (model load); 15 s audio warm = 35 s (~2.3× realtime).

## Handling (implementation contract)
1. Save raw response to `data/audio/<song_id>.flac` (master copy).
2. If `ffmpeg` is on PATH (`shutil.which("ffmpeg")`), transcode:
   `ffmpeg -y -i <in>.flac <out>.wav` → prefer `.wav` as `audio_path`; keep `.flac` as master.
3. Duration: `ffprobe -v error -show_entries format=duration -of csv=p=0 <file>`.
4. Do NOT use stdlib `wave` — the response is FLAC.
5. The `/v1/audio/generation` fallback from the original brief is unnecessary — `/v1/sound-generation` is confirmed (HTTP 200). Keep `request_ace_step()` as a single small function.

## Cover art — CONFIRMED working
POST {LOCALAI_URL}/v1/images/generations
Request: `{"model": "flux.2-klein-4b", "prompt": "...", "n": 1, "size": "512x512"}`
Response: `{"data": [{"url": "http://127.0.0.1:7777/generated-images/<id>.png"}]}`
- URL field, not b64. May be absolute (as above) or relative to LOCALAI_URL — handle both.
- Measured: 35 s warm. Download the PNG bytes and save to `data/covers/<song_id>.png`.

## LLM (127.0.0.1:18888) — CONFIRMED
- `/v1/chat/completions`, model `GLM-5.3-Flash-EXL3`. Sub-second decode but can queue ~50 s under load. Use long timeouts (≥120 s) and surface busy vs unreachable distinctly in job errors.
