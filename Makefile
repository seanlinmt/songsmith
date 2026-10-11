HOST ?= 127.0.0.1
PORT ?= 8788

dev:
	python3 -m venv .venv 2>/dev/null || true
	.venv/bin/pip install -q -r requirements.txt
	.venv/bin/uvicorn server.main:app --host $(HOST) --port $(PORT) --reload

.PHONY: dev
