.PHONY: help install dev backend frontend build run docker docker-up docker-down test seed clean

help:
	@echo "AI Workflow Automation — make targets:"
	@echo "  install      Install backend + frontend deps"
	@echo "  dev          Run backend (8000) + frontend (3000) in dev mode"
	@echo "  backend      Run only backend (uvicorn, reload)"
	@echo "  frontend     Run only frontend (next dev)"
	@echo "  build        Build frontend static into backend/app/static"
	@echo "  run          Build then run production server (single port 8000)"
	@echo "  docker       Build single-image Docker"
	@echo "  docker-up    docker compose up -d"
	@echo "  docker-down  docker compose down"
	@echo "  test         Run pytest"
	@echo "  seed         Load sample documents"
	@echo "  clean        Remove build artifacts + data"

install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r requirements.txt
	cd frontend && npm install

dev:
	@(cd backend && . .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload) & \
	(cd frontend && npm run dev) ; wait

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm run dev

build:
	cd frontend && npm run build && npm run export || true
	rm -rf backend/app/static
	mkdir -p backend/app/static
	cp -r frontend/out/* backend/app/static/ 2>/dev/null || cp -r frontend/.next/static backend/app/static/

run: build
	cd backend && . .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000

docker:
	docker build -t ai-workflow:latest .

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

test:
	cd backend && . .venv/bin/activate && pytest -q

seed:
	cd backend && . .venv/bin/activate && python -m app.scripts.seed

clean:
	rm -rf backend/.venv backend/app/static frontend/node_modules frontend/.next frontend/out data
