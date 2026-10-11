HOST ?= 127.0.0.1
PORT ?= 8788

dev:
	HOST=$(HOST) PORT=$(PORT) ./launcher.sh

stop:
	@lsof -ti :$(PORT) | xargs kill -9 2>/dev/null || true

restart: stop dev

.PHONY: dev stop restart

