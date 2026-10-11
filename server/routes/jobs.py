"""Job polling endpoints."""
from fastapi import APIRouter

from .. import db

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _job_public(j: dict) -> dict:
    return {
        "id": j["id"],
        "song_id": j["song_id"],
        "job_group_id": j["job_group_id"],
        "type": j["type"],
        "status": j["status"],
        "progress": j["progress"],
        "message": j["message"],
        "created_at": j["created_at"],
        "updated_at": j["updated_at"],
    }


@router.get("")
def list_jobs(group: str | None = None):
    if group:
        rows = db.query_all(
            "SELECT * FROM jobs WHERE job_group_id = ? ORDER BY created_at ASC", (group,)
        )
    else:
        rows = db.query_all("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100")
    return [_job_public(j) for j in rows]


@router.get("/active")
def active_jobs():
    rows = db.query_all(
        "SELECT * FROM jobs WHERE status IN ('queued', 'running') ORDER BY created_at ASC"
    )
    return [_job_public(j) for j in rows]
