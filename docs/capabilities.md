# Songsmith — Capability Probe Results

Probed 2026-10-11. All endpoints tested with real requests; nothing assumed.

## Endpoint 1: LocalAI — `http://127.0.0.1:7777`

OpenAI-compatible API. Models dir `~/.localai/models`, backends in `~/.localai/backends`.

### Pre-installed models
| Model | Backend | Verified how |
|---|---|---|
| `Z-Image-Turbo` | metal-stablediffusion-ggml | present in `/v1/models` |
| `flux.2-klein-4b` | metal-stablediffusion-ggml | present in `/v1/models` |
| `flux.2-klein-9b` | metal-stablediffusion-ggml | present in `/v1/models` |
| `wan-2.1-flf2v-14b-720p-ggml` | metal-stablediffusion-ggml | present in `/v1/models` |
| `wan-2.1-i2v-14b-720p-ggml` | metal-stablediffusion-ggml | present in `/v1/models` |

### Installed during this project (via `POST /models/apply` → gallery `localai@ace-step-turbo`)
| Model | Backend | Why | Verified how |
|---|---|---|---|
| `ace-step-turbo` | `ace-step` (native Metal, `quay.io/go-skynet/local-ai-backends:latest-metal-darwin-arm64-ace-step`, 591 MiB backend image) | Suno-style text+lyrics → full song with vocals; supports instrumental, duration, seed, BPM/key metadata | `GET /v1/models` lists it; live generation test: **pending** (running, first call loads the model) |

Gallery install notes:
- `{"id": "ace-step@ace-step-turbo"}` **fails** ("no model found"); the working id is `{"id": "localai@ace-step-turbo"}` (gallery name `localai`).
- Backend pulled for `darwin-arm64` with `metal` in the tag → Apple Silicon native, no CUDA dependency.
- Config written to `~/.localai/models/ace-step-turbo.yaml`: `backend: ace-step`, `known_usecases: [sound_generation]`, options include `device:auto`, `use_flash_attention:true`, `inference_steps:8` (turbo), `batch_size:1`.

### API shape (verified with real requests)
- `GET /v1/models` → OpenAI model list.
- `POST /models/available` → 2085 gallery entries; music-relevant ones found: `ace-step-turbo` (music+lyrics→song), `audioldm2` (sound effects/music via diffusers), `audio-cpp-stable-audio-sfx` (SFX only), TTS: `kokoro`, `qwen3-tts-cpp-*`, `vits-piper-*`, `pocket-tts`, `lfm2.5-audio-*`; ASR: `whisper*`, `whisperx-*`.
- **`POST /v1/sound-generation`** — confirmed working for ACE-Step:
  - Request fields used: `{"model": "ace-step-turbo", "prompt": "<style text>", "lyrics": "<[verse]/[chorus] tagged text>", "duration_seconds": N, "seed": N}`.
  - Response: **HTTP 200, raw audio bytes — FLAC format** (`fLaC` magic, 24-bit, 48 kHz stereo), *not* WAV as initially assumed. ~1.5 MB per 10 s of audio.
  - First call took **7m40s** (model cold-load onto Metal + 10 s generation); steady-state timing being measured.
  - Instrumental test: prompt-only, no `lyrics` field → pure music. Vocal test with tagged lyrics: running.
- `POST /v1/images/generations` — used for cover art (flux.2-klein-4b).
- `POST /models/apply` + `GET /models/jobs/<uuid>` — install pipeline works (poll returns progress %).

## M4 generation timing (measured, final)
| Test | Duration requested | Wall time | Notes |
|---|---|---|---|
| Instrumental, cold model load | 10 s audio | 7m40s | includes ACE-Step 1.5 first-load onto Metal |
| Vocal (tagged lyrics), warm | 15 s audio | **35 s** | ~2.3× realtime; a 150 s song ≈ 6 min |
| Instrumental pair (2 variations) e2e via app | 2 × 20 s audio + 2 covers | ~10 min | includes GLM title call + 2 music gens + 2 covers |
| Vocal pair (auto-lyrics) e2e via app | 2 × 25 s audio + 2 covers | ~10–14 min | LLM latency on shared server is the variable part |
| Cover art (flux.2-klein-4b), warm | 1 image | 35 s | returns URL, downloaded to data/covers/ |
| GLM chat (LLM server responsive) | tiny prompt | 0.3–3 s | shared server; under load can queue minutes |

### LLM server reliability note
`127.0.0.1:18888` (GLM-5.3-Flash-EXL3) exhibited multi-minute queue stalls and
transient connect failures during testing. The app handles this: distinct
"LLM busy (timeout)" vs "LLM unreachable" errors are stored per song/job and
surfaced in the UI; failed jobs can be retried. A 900 s LLM timeout is set.

## Vertical-slice conclusion — PASSED
ACE-Step 1.5 Turbo via LocalAI on Metal is viable as the end-to-end song model.
**Verified end to end through the finished app** (prompt → lyrics → audio →
cover → plays in browser):
- Vocal: GLM auto-lyrics + ACE-Step vocals ("Shake the Ground", 2 variations, 25 s, covers + WAV)
- Instrumental: prompt-only ("Drifting Through Silent Stars", 2 variations, 20 s, covers + WAV)
- Audio served as `audio/x-wav` (ffmpeg-transcoded from LocalAI's FLAC), covers as PNG.
- `make dev` boots the full stack; UI at http://127.0.0.1:8788.

## Extend/continue
Gated on `supports_extend` (MUSIC_MODEL == ace-step-turbo); the endpoint and UI
button are wired. Actual audio-continuation quality was not evaluated in this
session (would need additional generation runs); the mechanism generates a new
longer piece from the parent's prompt/lyrics/seed rather than splicing audio.

## Endpoint 2: LLM — `http://127.0.0.1:18888`

OpenAI-compatible (note: task description said `ai:8888`; actual reachable address is `127.0.0.1:18888`).

- `GET /v1/models` → `GLM-5.3-Flash-EXL3` (1M context).
- `POST /v1/chat/completions` verified: `{"messages":[{"role":"user","content":"Reply with exactly: PONG"}]}` → `"PONG"`. Decode sub-second; first call queued ~50s on shared server (other tenants). The app must use long enough timeouts and surface "LLM busy/unreachable" distinctly.

## Routing (final)
| Task | Endpoint | Model |
|---|---|---|
| Lyrics, titles, structure tags | `127.0.0.1:18888` | `GLM-5.3-Flash-EXL3` |
| Music + vocals | LocalAI `127.0.0.1:7777` | `ace-step-turbo` (`/v1/sound-generation`) |
| Cover art | LocalAI | `flux.2-klein-4b` |
| Lyric alignment (optional, stretch) | LocalAI | `whisper`/`whisperx` (not installed yet) |
| Video loop (stretch) | LocalAI | `wan-2.1-*` (already installed, not wired) |

## Open items
1. Confirm exact `/v1/sound-generation` request/response fields for ACE-Step (test running; result will be recorded here and in `server/music.py`).
2. Extend/continue support: to be confirmed against ACE-Step 1.5 audio-continuation capability; the extend button is gated on `MUSIC_MODEL == ace-step-turbo` until verified.
