"""FastAPI app: mounts static UI + /files data dir, includes API routers."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config, db, queue
from .routes import health, jobs, settings, songs

logging.basicConfig(level=logging.INFO)


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

# Serve generated audio/covers from the data dir.
config.ensure_dirs()
app.mount("/files", StaticFiles(directory=str(config.DATA_DIR)), name="files")

# Serve the placeholder UI last (so /api wins).
_static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
