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

## Endpoint 3: takahe LocalAI docker — `http://takahe:6767`

LocalAI v4.11.0 (`localai/localai:latest-gpu-nvidia-cuda-13`), plain `docker run` on bridge
network, port 6767→8080, all state in anonymous volumes (`/models`, `/backends`,
`/configuration`, `/data`). RTX 2080 Ti 22 GB.

### Concurrency (verified 2026-10-14)
- Root cause of "one queue": concurrency knobs in v4.11 are **startup-time env/CLI only** —
  `runtime_settings.json` has NO parallel key, and the UI's "Parallel Backend Requests"
  toggle is a v2.x ghost that gets silently dropped on POST. Hardware auto-tuning forces
  `parallel="1"` per model unless overridden in model YAML.
- Fix applied: container recreated with `-e LOCALAI_PARALLEL_REQUESTS=true -e
  PYTHON_GRPC_MAX_WORKERS=2` (same volumes, zero re-downloads). Old container kept as `local-ai-old`.
- Verified: two concurrent `POST /v1/chat/completions` → wall ≈ max(7.3s, 7.7s) = 7.7s
  (was serialized before). Parallel frontend dispatch works.
- Piper (`voice-nl-nathalie-x-low`) still serializes: C++ backend, no parallel mode,
  `PYTHON_GRPC_MAX_WORKERS` doesn't apply. Two ~17s TTS jobs → 34.7s wall. Expected.
- ACE-Step (Python backend) now honors `PYTHON_GRPC_MAX_WORKERS=2` — concurrent music
  generations possible; VRAM-permitting on the 2080 Ti.
- llm `GLM-5.3-Flash-EXL3` here is a `localai-proxy` passthrough to `http://ai:8888/v1/chat/completions`
  (`request_timeout_seconds: 209`) — NOT the 127.0.0.1:18888 server.

### Generated-file serving (verified 2026-10-14, source-confirmed at tag v4.11.0)
- `POST /video` response is OpenAI-images-style: `data[0].url` (absolute URL) or
  `data[0].b64_json` if `response_format: "b64_json"`. **Read the URL from the response —
  never construct it from backend logs.**
- Served route: `/generated-videos/<basename>.mp4` (also `/generated-images`, `-audio`, `-3d`).
  There is NO `/generated/...` route — a URL built from the log path 404s.
- Generated-content dir was ephemeral (`/tmp/localai-0/generated/content`, wiped on restart);
  fixed by recreating the container with `-e LOCALAI_GENERATED_CONTENT_PATH=/data/generated`
  (persists on the `/data` volume). Verified: `/generated-videos/b642586812849.mp4` → 200
  `video/mp4` after restart+restore.
- Final container env: `LOCALAI_PARALLEL_REQUESTS=true`, `PYTHON_GRPC_MAX_WORKERS=2`,
  `LOCALAI_GENERATED_CONTENT_PATH=/data/generated`, `LOCALAI_P2P=true`, `LOCALAI_FEDERATED=true`,
  `LOCALAI_P2P_TOKEN=<shared_token>`, `LOCALAI_ADDRESS=0.0.0.0:6767`. Network: `--net host` (UFW `6767/tcp` allowed).

### Partial-download cleanup (verified 2026-10-16)
- Upstream only reaps stale `*.partial` (>24h) **at startup** (`CleanupStalePartialFiles`);
  no built-in cron. Partials live next to their target + under `/models/.artifacts/.partial/<64hex>.<16hex>/`.
- Hourly cron on takahe (root, `17 * * * *`): `/usr/local/bin/localai-cleanup.sh` — cleans
  `*.partial`/artifact trees >24h inside both `local-ai` and `localai-manager`; log at
  `/var/log/localai-cleanup.log`. Committed weights are never touched — reclaim those via
  the UI Cleanup review or `POST /api/nodes/<id>/models/delete`.

### Cluster topology (verified 2026-10-16): takahe is manager+worker
- takahe now runs the **distributed manager** (`localai-manager` container, port 6767,
  `--net host`, same image) plus its worker (`local-ai`, `worker` subcommand registering
  to `http://127.0.0.1:6767`). Shared postgres (:5433) + NATS (:4222) on takahe back it.
- Manager auth quirk: API keys are HMAC-hashed with a per-instance secret — the new
  manager needed the Mac's `~/.localai/data/.hmac_secret` copied into its `/data`
  volume (`docker cp` + restart) or every key 401s despite the shared DB.
- Mac frontend (`127.0.0.1:7777`, launcher.json) stays up for songsmith; it shares the
  same DB, so all frontends see the same node registry. P2P/federated env is gone —
  the cluster is pure distributed mode now.
- takahe node id `71867fde-ec5a-4b46-b3c4-5bf03b846750` survived re-registration
  (identity derives from env/addr, not container), so its sticky `vram_budget: 21GB`
  carried over. Total/available VRAM in the UI is still bogus (ghw reads NUMA RAM as
  VRAM on this host: 377.8 GB / 2 sockets ≈ 188.8 GB); the budget is what the
  scheduler uses. `amd`'s 8GB-report is correct; `tiny` (Apple metal) reports RAM.
- Rollback: `local-ai-prev` on takahe holds the old worker container. Tiny's manager was
  demoted 2026-10-16: LocalAI.app launcher quit, `auto_start_server`/`start_on_boot` set
  false in `~/.localai/launcher.json`; the tiny *worker* still runs via launchd
  (`localai.cluster.worker`, now registering to `192.168.20.228:6767`). Songsmith's
  `data/settings.json` `localai_url` points at `http://192.168.20.228:6767`.
- Model YAML configs are per-frontend disk state (not in the shared DB) — the Mac's
  configs (`~/.localai/models/*.yaml`, kilobytes) were copied into the manager's `/models`
  volume on takahe; `/v1/models` needs a manager restart after adding configs.

### P2P Federation (verified 2026-10-15; superseded 2026-10-16 by topology above)
- Mac (`127.0.0.1:7777`) and takahe (`takahe:6767`) are linked via LocalAI P2P & Federated mode (`--p2p --federated`) using a shared EdgeVPN token.
- Mac config: `~/.localai/launcher.json` (environment variables `LOCALAI_P2P`, `LOCALAI_FEDERATED`, `LOCALAI_P2P_TOKEN`) and `~/.localai/configuration/runtime_settings.json`.
- Takahe config: Container runs with `--net host` and `LOCALAI_ADDRESS=0.0.0.0:6767`, with UFW `6767/tcp` allowed on the host.
- Verified: Both nodes discover each other over mDNS/DHT and appear in `/api/p2p` under `federated_nodes`.

