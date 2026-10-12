# AGENTS.md

Suno-style local song generation: FastAPI + SQLite + asyncio job queue, backed
by LocalAI (ACE-Step music, Flux covers) and a GLM LLM for lyrics/titles.
Single app, ~3.4k lines, no tests/CI/lint config — verification is manual.

## Run

```
make dev   # creates .venv, installs requirements, builds frontend, starts uvicorn --reload on 127.0.0.1:8788
```

- UI: http://127.0.0.1:8788 · API health: `GET /api/health` · config: `GET /api/config`
- `server/web/` (gitignored) holds the built Svelte SPA; the launcher builds it
  (`npm install && npm run build` in `frontend/`) and skips gracefully if npm is
  missing. For UI iteration run `npm run dev` in `frontend/` (Vite on :5173,
  proxies `/api` + `/files` to :8788).
- Config lives in `.env` (copy `.env.example`). `server/config.py` loads it from
  the project root; defaults exist for everything, so the app boots without it.
- `data/` (gitignored) holds `songsmith.db` (WAL), `audio/`, `covers/`; served
  at `/files`. Generated files are named `<song_id>.{wav,flac,png}`.

## External services (generation fails without them; app still boots)

- LocalAI `http://127.0.0.1:7777` — music (`ace-step-turbo` via
  `POST /v1/sound-generation`) and cover art (`flux.2-klein-4b`).
- LLM `http://127.0.0.1:18888` (`GLM-5.3-Flash-EXL3`) — lyrics, titles, style
  expansion. Shared server: can stall for minutes. The 900s LLM timeout is
  intentional — do not shorten it.
- `POST /v1/sound-generation` returns **raw FLAC bytes, not WAV**. For
  instrumental, omit the `lyrics` key entirely (don't send empty). `ffmpeg`
  transcodes to wav and `ffprobe` reads duration; without ffmpeg on PATH the
  flac master is served instead. Exact request/response contract:
  `docs/api-notes.md` (verified against live LocalAI — trust it over assumptions).

## Architecture

- `server/main.py` — entrypoint. Mounts API routers, `/files` static dir, then
  the built Svelte SPA (`server/web/`) at `/` **last** so `/api` routes win.
- `server/queue.py` — the pipeline. In-process asyncio workers
  (`MAX_CONCURRENCY = 2`) poll the `jobs` table every 0.5s. Jobs are persisted,
  so state survives reloads, but there is **no in-process resume**: on startup
  any `running` job is marked `error: "interrupted by restart"`.
- Pipeline order (all in `_run_generation`): lyrics+title (one LLM call) →
  style expansion (cached on the song row) → music gen → cover art
  (best-effort; failure doesn't fail the job).
- `server/db.py` — raw sqlite3, one connection per call, WAL mode. Tables:
  `songs`, `jobs`, `styles`.
- `server/routes/songs.py` — request models use Suno's snake_case
  `GenParamsSpec` wire names (`tags`, `negative_tags`, `make_instrumental`,
  `batch_size`, …). Keep that contract.
- Extend is gated on `config.SUPPORTS_EXTEND` (`MUSIC_MODEL == ace-step-turbo`)
  and currently does full-clip re-extension, not splicing; `continue_at` is
  persisted but not yet sent to ACE-Step.

## Docs

`docs/` holds hard-won, verified probe results — read `api-notes.md` and
`capabilities.md` before touching `music.py`/`llm.py`. `todo-suno-parity.md`
tracks feature parity work derived from `suno-apk-analysis.md` (Suno APK
reverse engineering).
