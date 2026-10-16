#!/usr/bin/env bash
set -euo pipefail

# Songsmith development server launcher
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment overrides if present
if [ -f .env ]; then
  # Export non-comment lines
  export $(grep -v '^#' .env | xargs -0 2>/dev/null) || true
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8788}"

echo "==> Checking port ${PORT}..."
STALE_PIDS=$(lsof -ti ":${PORT}" 2>/dev/null || true)

if [ -n "${STALE_PIDS}" ]; then
  echo "Found existing process on port ${PORT} (PID: ${STALE_PIDS}). Killing..."
  echo "${STALE_PIDS}" | xargs kill -15 2>/dev/null || true
  sleep 1

  # Check if still running, force kill if needed
  REMAINING_PIDS=$(lsof -ti ":${PORT}" 2>/dev/null || true)
  if [ -n "${REMAINING_PIDS}" ]; then
    echo "Force killing PID: ${REMAINING_PIDS}..."
    echo "${REMAINING_PIDS}" | xargs kill -9 2>/dev/null || true
    sleep 0.5
  fi
  echo "Port ${PORT} cleared."
fi

# Ensure virtualenv exists
if [ ! -d ".venv" ]; then
  echo "==> Creating virtual environment (.venv)..."
  python3 -m venv .venv
fi

# Install dependencies if requirements changed or not installed
echo "==> Verifying dependencies..."
.venv/bin/pip install -q -r requirements.txt

# Build the Svelte SPA into server/web/ (skipped if npm is unavailable;
# server/web/ is gitignored, so this must run at least once after clone).
if command -v npm >/dev/null 2>&1 && [ -d frontend ]; then
  echo "==> Building frontend (server/web/)..."
  (cd frontend && npm install --no-audit --no-fund && npm run build)
else
  echo "==> npm not found — skipping frontend build (UI at / will 404)."
fi

echo "==> Starting Songsmith at http://${HOST}:${PORT}..."
exec .venv/bin/uvicorn server.main:app --host "${HOST}" --port "${PORT}" --reload
