#!/usr/bin/env bash
# One-shot bare-metal installer for any Linux/macOS server.
set -euo pipefail

cd "$(dirname "$0")/.."
echo "==> Creating Python venv"
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -U pip wheel
pip install -r backend/requirements.txt

echo "==> Building frontend (optional, requires node)"
if command -v npm >/dev/null 2>&1; then
  (cd frontend && npm install && npm run build)
  rm -rf backend/app/static
  mkdir -p backend/app/static
  cp -r frontend/out/* backend/app/static/ 2>/dev/null || true
else
  echo "Node not found — frontend skipped. Install Node 20+ to build the UI."
fi

echo "==> Copying .env"
[ -f .env ] || cp .env.example .env

echo "==> Done. Start with: ./scripts/run.sh"
