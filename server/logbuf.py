"""In-memory server log buffer, exposed for the debug panel.

A logging.Handler keeps the last N formatted lines (since process boot) with
monotonic sequence numbers. GET /api/logs?since=<seq> returns everything after
that cursor, so the UI can poll cheaply and never miss or re-read lines.
"""
import logging
import time
from collections import deque

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/logs", tags=["logs"])

MAX_LINES = 5000
_buf = deque(maxlen=MAX_LINES)  # list of {"seq","ts","level","name","msg"}
_seq = 0


class _RingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        global _seq
        _seq += 1
        _buf.append({
            "seq": _seq,
            "ts": time.strftime("%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "name": record.name,
            "msg": self.format(record),
        })


def install() -> None:
    """Attach the ring buffer to the root logger and the uvicorn loggers."""
    handler = _RingHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.addHandler(handler)


@router.get("")
def get_logs(since: int = Query(default=0, ge=0),
             limit: int = Query(default=1000, ge=1, le=MAX_LINES)):
    """Lines after `since` cursor; since=0 returns the tail (last `limit`)."""
    with_buf = list(_buf)
    if since <= 0:
        rows = with_buf[-limit:]
    else:
        rows = [r for r in with_buf if r["seq"] > since][:limit]
    next_seq = rows[-1]["seq"] if rows else max(since, _seq)
    return {"lines": rows, "next": next_seq, "buffered": len(with_buf)}
