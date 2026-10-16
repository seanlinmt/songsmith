# Songsmith

Songsmith is a local-first, Suno-style AI music generation studio and web UI. It provides an end-to-end pipeline for lyrics and title generation, style prompt expansion, music synthesis, and album cover art generation backed by an async job queue and SQLite persistence.

![Songsmith Creation Interface](docs/screenshots/create.png)

### Sample Output

<audio controls src="docs/samples/black-dress-dreams.mp3"></audio>

- [Listen: Black Dress Dreams (MP3)](docs/samples/black-dress-dreams.mp3)

---

## Features

- **Full Generation Pipeline**: Prompt-to-lyrics/title (LLM) → Style expansion → Music synthesis (ACE-Step) → Cover art (Flux).
- **Dual Variations**: Generates paired variations per prompt (Suno workflow) with independent seeds.
- **Extend & Regenerate**: Continue previous clips or roll new seeds with preserved prompt context.
- **Svelte 5 Audio Studio**: Web player with real-time job progress, track history, and audio preview.
- **In-App Settings**: Live configuration of endpoints, models, and API keys stored in `data/settings.json`.
- **Resilient Queue**: In-process SQLite-backed async worker queue.

---

## Prerequisites

- **Python**: 3.10+
- **ffmpeg** & **ffprobe**: Required for audio transcoding (FLAC to WAV) and duration probing.
- **Node.js** (optional): Node 18+ / npm to build the frontend (pre-built or auto-built by `./start.sh`).
- **Inference Backends**:
  - **Music & Images**: [LocalAI](https://localai.io) running `ace-step-turbo` and `flux.2-klein-4b` (or compatible endpoints).
  - **Lyrics & Styles**: Any OpenAI-compatible LLM endpoint (e.g., GLM, Ollama, vLLM, or LocalAI).

---

## Quickstart

```bash
./start.sh
```

`./start.sh` handles port cleanup, `.venv` setup, dependency installation, frontend build, and starts uvicorn with auto-reload at [http://127.0.0.1:8788](http://127.0.0.1:8788).

Custom host or port:
```bash
PORT=9000 HOST=0.0.0.0 ./start.sh
```

For frontend UI development with Vite HMR:
```bash
cd frontend && npm run dev   # Runs on http://localhost:5173 (proxies to :8788)
```

---

## Configuration

Service endpoints and model selections can be adjusted directly in the **Settings** view of the web UI or in `data/settings.json`:

| Setting | Default | Purpose |
|---|---|---|
| `localai_url` | `http://127.0.0.1:7777` | Default base endpoint for music and cover art |
| `llm_url` | `http://127.0.0.1:18888` | OpenAI-compatible endpoint for lyrics/styles |
| `llm_model` | `GLM-5.3-Flash-EXL3` | Model name for prompt expansion and lyric generation |
| `music_model` | `ace-step-turbo` | ACE-Step music synthesis model |
| `image_model` | `flux.2-klein-4b` | Cover art generation model |

Process bootstrap overrides (`HOST`, `PORT`, `DATA_DIR`) can be set in `.env` or passed via environment variables.

---

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/songs` | Submit generation job (creates 2 variations) |
| `GET` | `/api/songs` | List generated songs |
| `GET` | `/api/songs/{id}` | Fetch song metadata and audio URL |
| `DELETE` | `/api/songs/{id}` | Delete song and associated files |
| `POST` | `/api/songs/{id}/regenerate` | Queue new variation with a new seed |
| `POST` | `/api/songs/{id}/extend` | Extend track duration |
| `POST` | `/api/lyrics` | Generate title and lyrics from prompt |
| `GET` | `/api/styles` | List preset music styles |
| `POST` | `/api/styles/expand` | Expand a short style prompt into generation tags |
| `GET` | `/api/jobs` | Check generation queue status |
| `GET` | `/api/jobs/active` | Get currently running/queued jobs |
| `GET` | `/api/config` | View active configuration |
| `PATCH` | `/api/config` | Update service endpoints and models |
| `GET` | `/api/health` | Backend connectivity and system health checks |
