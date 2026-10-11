"""Small synchronous sqlite3 helper layer.

One connection per call site is fine for this app's write volume; WAL mode
keeps readers (API) from blocking the queue writer.
"""
import json
import sqlite3
import threading
from pathlib import Path

from . import config

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS songs (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    prompt TEXT NOT NULL DEFAULT '',
    lyrics TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    instrumental INTEGER NOT NULL DEFAULT 0,
    model TEXT NOT NULL DEFAULT '',
    seed INTEGER,
    duration_seconds INTEGER,
    status TEXT NOT NULL DEFAULT 'queued',
    audio_path TEXT,
    cover_path TEXT,
    error TEXT,
    job_group_id TEXT NOT NULL,
    parent_id TEXT,
    kind TEXT NOT NULL DEFAULT 'song',
    style_prompt TEXT,
    negative_tags TEXT
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    song_id TEXT NOT NULL,
    job_group_id TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    progress REAL NOT NULL DEFAULT 0,
    message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_jobs_group ON jobs(job_group_id);
CREATE INDEX IF NOT EXISTS idx_songs_group ON songs(job_group_id);
"""


def _connect() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        db_path = config.DATA_DIR / "songsmith.db"
        config.ensure_dirs()
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


def init_db() -> None:
    conn = _connect()
    conn.executescript(SCHEMA)
    # Migrations for pre-existing DBs created before style fields existed.
    for col in ("style_prompt", "negative_tags"):
        try:
            conn.execute(f"ALTER TABLE songs ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()


def execute(sql: str, params: tuple = ()) -> None:
    conn = _connect()
    with conn:
        conn.execute(sql, params)


def query_all(sql: str, params: tuple = ()) -> list[dict]:
    conn = _connect()
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    rows = query_all(sql, params)
    return rows[0] if rows else None


# ---- row<->dict helpers (json decode tags) ----

def song_row_to_dict(row: dict) -> dict:
    out = dict(row)
    try:
        out["tags"] = json.loads(out.get("tags") or "[]")
    except (TypeError, json.JSONDecodeError):
        out["tags"] = []
    try:
        out["negative_tags"] = json.loads(out.get("negative_tags") or "[]")
    except (TypeError, json.JSONDecodeError):
        out["negative_tags"] = []
    out["instrumental"] = bool(out.get("instrumental"))
    return out


def get_song(song_id: str) -> dict | None:
    row = query_one("SELECT * FROM songs WHERE id = ?", (song_id,))
    return song_row_to_dict(row) if row else None


def list_songs() -> list[dict]:
    rows = query_all("SELECT * FROM songs ORDER BY created_at DESC, id DESC")
    return [song_row_to_dict(r) for r in rows]


def audio_file_path(song_id: str) -> Path:
    return config.DATA_DIR / "audio" / f"{song_id}.wav"


def cover_file_path(song_id: str) -> Path:
    return config.DATA_DIR / "covers" / f"{song_id}.png"
