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
  (identity derives from env/addr, not container), so its sticky `vram_budget: 21GB` carried over. Total/available VRAM in the UI is still bogus (ghw reads NUMA RAM as
  VRAM on this host: 377.8 GB / 2 sockets ≈ 188.8 GB); the budget is what the
  scheduler uses. `amd`'s 8GB-report is correct; `tiny` (Apple metal) reports RAM.
- VRAM misreport FIXED 2026-10-16 via docker launch params. `TotalAvailableVRAM()`
  prefers ghw and returns early (`pkg/xsysinfo/gpu.go`), so nvidia-smi's true
  22528 MiB never gets a turn while `/usr/share/misc/pci.ids` parses. Worker
  container recreated with `--mount type=tmpfs,destination=/usr/share/misc`
  (masks pci.ids → ghw errors → falls through to nvidia-smi) and
  `-e LOCALAI_VRAM_BUDGET=22528MiB` (worker-reported budget; caps
  `available_vram` server-side). Also added `--init` (upstream: without it
  `nvidia-smi` intermittently fails with `waitid: no child processes`).
  Verified: node now reports `total_vram: 23622320128` (22 GiB) at
  registration; UI bar reads real numbers. Note: the API `PUT
  /api/nodes/<id>/vram-budget` takes `{"value":"22GB"}` (not `{"vram_budget":…}`);
  a sticky DB override beats the worker's env — `DELETE` the endpoint to let
  `LOCALAI_VRAM_BUDGET` win again. An EMPTY pci.ids file is not enough (ghw
  parses it fine) — the file must be ABSENT, hence the tmpfs mount over the dir.
  Old containers kept as `local-ai-prev2` (stopped) and inspect backup at
  `/tmp/local-ai-inspect-backup-2026-10-16.json`.
- Rollback: `local-ai-prev` on takahe holds the old worker container. Tiny's manager was
  demoted 2026-10-16: LocalAI.app launcher quit, `auto_start_server`/`start_on_boot` set
  false in `~/.localai/launcher.json`; the tiny *worker* still runs via launchd
  (`localai.cluster.worker`, now registering to `192.168.20.228:6767`). Songsmith's
  `data/settings.json` `localai_url` points at `http://192.168.20.228:6767`.
- Model YAML configs are per-frontend disk state (not in the shared DB) — the Mac's
  configs (`~/.localai/models/*.yaml`, kilobytes) were copied into the manager's `/models`
  volume on takahe; `/v1/models` needs a manager restart after adding configs.

### foundation-sec-8b-q8_0 load failure + fix (verified 2026-10-16)
- Symptom: `POST /v1/chat/completions` → 500 `stale model config revision (request carries
  da6978…, controller holds 60d64952…)`; `amd` node showed `model_count: 0` and repeated
  unload-to-load churn. Fixed by `docker restart localai-manager` (controller re-reads
  config revisions from its `/models` volume; node identity/budgets survive).
- Second failure after restart: `llama_model_load_from_file_impl: exactly one out
  metadata, path_model, and file must be defined` == the llama.cpp server got an EMPTY
  model path (cf. ggml-org/llama.cpp discussion #27095). Gallery import had written
  `parameters.model: foundation-sec-8b-reasoning` (a name, not a path) while the GGUF
  sits at `llama-cpp/models/foundation-sec-8b-q8_0/foundation-sec-8b-q8_0.gguf`.
- Rule: `parameters.model` must be a path **prefixed with the gallery-backend dir**,
  same as flux.2-klein-4b (`stablediffusion-cpp/models/…`). Fixed YAML now has
  `parameters.model: llama-cpp/models/foundation-sec-8b-q8_0/foundation-sec-8b-q8_0.gguf`
  with `backend: rocm-turboquant`.
- Verified: model loads on node `amd` (RX 6800, `rocm-turboquant` backend) and answers
  chat completions through the manager. Not an AMD/ROCm issue — never was.
- Renamed 2026-10-16: served model id is now `foundation-sec-8b-reasoning` (config
  `name:` changed; artifact path unchanged, still under `llama-cpp/models/foundation-sec-8b-q8_0/`).
  Gotcha: scheduling rules live in the shared DB (`model_scheduling_configs`) keyed by
  model NAME — renaming a model silently drops its node pin. The old name had
  `{"gpu.vendor":"amd"}`; without it the scheduler cold-loaded onto takahe (no rocm
  backend) with `no backend found with name "rocm-turboquant"`. Fix: update
  `model_name`/`target_model` in that table to the new name, restart manager.
  Also: distributed artifacts live at `models/<model-name>/<parameters.model>` on each
  worker, so renaming the model requires renaming that dir on the worker too
  (`mv /models/foundation-sec-8b-q8_0 /models/foundation-sec-8b-reasoning` on amd).
- Caveat: model is Llama-3.1-based; if load ever OOMs on 16GB, pin a context size in the
  YAML (default-ctx KV cache is the suspect, not weights: Q8_0 is 8.5 GB).

### glm-5.3-flash-exl3 "stale config revision" + `api_key_env unset` (fixed 2026-10-16)
- Symptom in chat UI: `failed to route model with internal loader: … stale model config
  revision (request carries 9bfba…, controller holds e4ec6…)`. First fix is the standing
  rule above: `docker restart localai-manager`.
- After the manager restart the error became `localai-proxy: api_key_env "LLM_API_KEY" is
  unset` on cold load — the model YAML is a `localai-proxy` passthrough to the tensorfold
  EXL3 server (`192.168.20.63:8888`, `upstream_model: GLM-5.3-Flash-EXL3`) and requires
  `LLM_API_KEY` in the env of whichever node loads it (it landed on `amd`, whose worker
  container predated the proxy config and had no `LLM_API_KEY`).
- Fix: recreated the `amd` worker container (`local-ai` on 192.168.20.16) with the same
  run config plus `-e LLM_API_KEY=sk-spark-…` (same key songsmith stores in
  `data/settings.json` as `llm_api_key` — the upstream 401s without it). Old container
  kept as `local-ai-prev-key`. Gotcha: the `/configuration` mount is a bind of a volume
  subdir with `rslave`; `-v <vol>:/configuration:rslave` fails, must bind
  `/var/lib/docker/volumes/<id>/_data:/configuration:rslave` explicitly.
- Verified: `POST /v1/chat/completions` model `glm-5.3-flash-exl3` returns completions
  through the manager (reasoning-style output; `max_tokens` counts reasoning too).
- HTTPS for the manager UI/API: the manager (0.0.0.0:6767) is plain HTTP only —
  `https://takahe:6767` fails with `tlsv1 alert protocol version`. Added nginx vhost
  `localai-manager` listening **7779 ssl** (same LE cert as `localai`) proxying to
  `127.0.0.1:6767`. Use `https://takahe.clearpixels.org:7779/app/chat`. Note :7778
  TLS-proxies the *standalone* `local-ai` on 127.0.0.1:7777, which does not serve
  glm-5.3-flash-exl3.

### P2P Federation (verified 2026-10-15; superseded 2026-10-16 by topology above)
- Mac (`127.0.0.1:7777`) and takahe (`takahe:6767`) are linked via LocalAI P2P & Federated mode (`--p2p --federated`) using a shared EdgeVPN token.
- Mac config: `~/.localai/launcher.json` (environment variables `LOCALAI_P2P`, `LOCALAI_FEDERATED`, `LOCALAI_P2P_TOKEN`) and `~/.localai/configuration/runtime_settings.json`.
- Takahe config: Container runs with `--net host` and `LOCALAI_ADDRESS=0.0.0.0:6767`, with UFW `6767/tcp` allowed on the host.
- Verified: Both nodes discover each other over mDNS/DHT and appear in `/api/p2p` under `federated_nodes`.

### acestep-xl — ACE-Step v1.5 XL Turbo on takahe (installed 2026-10-17; working)
- Goal: better string instruments than the 2B turbo. Installed `ACE-Step/acestep-v15-xl-turbo`
  (4B DiT, 8-step distilled, ~19 GB bf16, no upstream gallery entry — see upstream issue #12721).
- Working config: `/models/acestep-xl.yaml` on takahe (both `localai-server` and `local-ai`
  share the `/mnt/xfs2/localai/models` mount): `backend: ace-step`,
  `parameters.model: acestep-v15-xl-turbo`, `offload_to_cpu: true`, `inference_steps: 8`,
  `lm_model_path: acestep-5Hz-lm-0.6B`. Repo copy: `gallery/ace-step-xl-turbo.yaml` on branch
  `gallery/ace-step-xl-turbo` (needs rename to `acestep-xl.yaml` to match the live name).
- Weight layout on the worker (critical — the stager and backend.py disagree on paths):
  - `/models/acestep-xl/checkpoints/acestep-xl/` — what backend.py's `LoadModel` reads
    (`checkpoint_dir = <ModelPath>/checkpoints/<config_path>`).
  - `/models/acestep-v15-xl-turbo/` — hardlinks to the same files; what the distributed
    file stager uploads (`staging /models/<parameters.model>`). A **symlink here breaks
    staging** with `read ...: is a directory`; real dir + hardlinks works (same xfs2 fs).
- Scheduling: rows in `model_scheduling_configs` (`{"gpu.vendor":"nvidia"}`) for
  `acestep-xl`, `ace-step-xl-turbo`, AND `ace-step-turbo`. `tiny` is an Apple-Silicon
  node (metal, 8 GB) that can never install `cuda13-ace-step` — without a pin, the
  idle-first cold scheduler picks it and every load dies with
  `no backend found with name "cuda13-ace-step"`.
- Gotchas hit along the way:
  - `POST /models/apply` with `config_url` alone failed (`unsupported protocol scheme`);
    the `url` + `name` + `overrides` form worked but wrote a **stripped 3-line yaml**
    (options/parameters dropped) — write the full yaml into the models dir instead.
  - Worker readiness probe is a hardcoded 30 s (`readinessTimeout` in
    `core/services/worker/supervisor.go`, no env knob). `import backend` alone takes
    ~22 s warm; cold page cache ⇒ readiness race lost. If a load fails with
    `did not become ready within 30s`, retry while the page cache is hot.
  - Watchdog (`runtime_settings.json`: `watchdog_idle_timeout: 15m`) kills idle
    backends, so the first request after 15 idle minutes pays the cold load again.
  - A stuck `unloading` replica row in `node_models` (cleanup_error: address mismatch,
    71 retries) blocked the family — deleted the row to clear it.
- Verified live: warm `POST /v1/sound-generation` model `acestep-xl` → 10 s audio in
  **5.9 s** (24-bit 48 kHz FLAC); first-load 8 s audio in ~30 s. Strings quality
  noticeably better than 2B turbo (subjective, user to confirm).
- Original 2B `ace-step-turbo` on takahe still broken cold (its yaml pins concrete
  `backend: cuda13-ace-step`; needs the same scheduling pin — added — plus the backend
  image resolving again). `acestep-cpp-turbo` unaffected (different backend family).

### takahe worker recreated with `--gpus all` + `PYTHON_GRPC_MAX_WORKERS=4` (fixed 2026-10-18)
- Symptom: `ace-step-xl-turbo` "stuck loading" — generation requests hung 5–15 min;
  frontend logged `Model backend unhealthy after consecutive misses (misses=3)` every
  few minutes, deregistering the backend mid-generation.
- Root cause chain:
  1. The ace-step backend sets `MAX_WORKERS = PYTHON_GRPC_MAX_WORKERS` (default **1**).
     While a generation ran (~2 min), the single gRPC thread was busy → `Health()`
     queued behind it → 3 consecutive health misses → frontend removed the replica →
     next request took the cold path again (readiness race, re-staging).
  2. My first worker recreation **forgot `--gpus all`**: the container started fine but
     `torch.cuda.is_available() == False`, the 0.6B LM silently ran on CPU, and Phase 1
     CoT hung for 15+ min at 550% CPU with GPU at 0%. The old container's
     `HostConfig.DeviceRequests` (`[{"Capabilities":[["gpu"]]}]`) was the missing piece.
- Fix: recreated `local-ai` with `--gpus all` (plus `NVIDIA_VISIBLE_DEVICES=all`,
  `NVIDIA_DRIVER_CAPABILITIES=compute,utility`, already present) and
  `PYTHON_GRPC_MAX_WORKERS=4`. Note: `--network host` means the old container must be
  stopped before the new one binds :50050–50051.
- Verified: `acestep-xl` warm in 27 s; `ace-step-xl-turbo` warm in **6.7 s**; zero
  `unhealthy` warnings after fix. Baseline per generation with `offload_to_cpu:true`:
  LM CoT phase ~15–60 s + diffusion ~5–30 s + VAE ~10 s.
- Lesson: when recreating ANY worker container on takahe, copy
  `docker inspect` `HostConfig.DeviceRequests` (or pass `--gpus all`) — `nvidia-smi`
  works on the host but the container silently falls back to CPU without it.

### shift=3.0 for turbo checkpoints (fixed 2026-10-19) — likely the "synthetic strings" culprit
- Per upstream issue #1114 (root-caused Aug 2026): `shift` is **per-checkpoint** —
  turbo variants require `shift=3.0`, base/sft require `shift=1.0`. A wrong `shift`
  produces **pitched-instrument timbre drift and segmented phrasing** — i.e. exactly
  "cello that doesn't sound like a cello". `guidance_scale` is auto-corrected for
  turbo (7.0 → 1.0, seen in logs), but `shift` is **not** auto-corrected on this path.
- LocalAI's `backend.py` reads `shift` from `payload.get("shift", 1.0)` (line 238) —
  the hardcoded default 1.0 was silently wrong for turbo. Verified via
  `_generate_audio_sync`: LoadModel options DO merge into the payload
  (`for key, value in opts.items(): if key not in payload`) — so a yaml option works.
- Fix: added `- shift:3.0` to both `/models/acestep-xl.yaml` and
  `/models/ace-step-xl-turbo.yaml` on takahe (backend restarted; LoadModel log now
  includes `shift` in options). Repo copy updated too.
- Also relevant: the 0.6B LM CoT phase runs per generation; prompts naming the
  instrument in the caption AND `[section - instrument]` lyric tags are the
  officially documented way to steer timbre. VAE tiled-decode chunk_size 128 with
  reduced overlap 32 (seen in logs) is known-upstream (ComfyUI #12253 raised 128→256);
  worth trying chunk 256+ if boundary artifacts appear. The ScragVAE decoder swap
  (ACESTEP_VAE_CHECKPOINT=scragvae, upstream v0.1.7+) addresses HF attenuation
  directly but is unverified through LocalAI's backend.

