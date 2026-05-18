#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source backend/.venv/bin/activate
export $(grep -v '^#' .env | xargs) 2>/dev/null || true
exec uvicorn app.main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8000}" --app-dir backend
