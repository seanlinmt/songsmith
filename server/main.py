"""FastAPI app: mounts static UI + /files data dir, includes API routers."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config, db, logbuf, queue
from .routes import health, jobs, settings, songs, styles

logging.basicConfig(level=logging.INFO)
# Health-poll and log-poll spam isn't useful in the UI log panel.
for _noisy in ("uvicorn.access", "httpx", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)
logbuf.install()


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_dirs()
    db.init_db()
    queue.start_workers()
    yield
    await queue.stop_workers()


app = FastAPI(title="Songsmith", lifespan=lifespan)

app.include_router(songs.router)
app.include_router(jobs.router)
app.include_router(health.router)
app.include_router(settings.router)
app.include_router(styles.router)
app.include_router(logbuf.router)

# Serve generated audio/covers from the data dir.
config.ensure_dirs()
app.mount("/files", StaticFiles(directory=str(config.DATA_DIR)), name="files")

# Serve the built Svelte SPA last (so /api wins).
_web_dir = Path(__file__).parent / "web"
app.mount("/", StaticFiles(directory=str(_web_dir), html=True), name="web")
