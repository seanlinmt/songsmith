# Songsmith

Local Suno-style song generation: FastAPI + SQLite + asyncio job queue, backed by
LocalAI (ACE-Step music, Flux cover art) and a GLM LLM for lyrics/titles.

## Run

```
make dev
```

Then open http://127.0.0.1:8788

## Config

Endpoints, models, host/port, and the data directory are configured in `.env`
(see `.env.example`). Generated audio, covers, and the SQLite database live in
`data/`.

## API (JSON)

- `POST /api/songs` — create 2 variations (async job group)
- `GET /api/songs`, `GET /api/songs/{id}`, `DELETE /api/songs/{id}`
- `POST /api/songs/{id}/regenerate` — new variation, new seed
- `POST /api/songs/{id}/extend` — extend (ace-step-turbo only)
- `GET /api/jobs?group=<id>`, `GET /api/jobs/active` — poll job progress
- `GET /api/health`, `GET /api/config`, `POST /api/lyrics`
