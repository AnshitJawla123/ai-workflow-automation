#!/usr/bin/env bash
# Clean all build artefacts so the folder is tiny (~3 MB) for git push.
# All deleted items are rebuildable: venv from requirements.txt, data dir on first run.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Before: $(du -sh . | cut -f1)"

# 1. Virtual env (1.4 GB)
rm -rf backend/.venv backend/venv .venv venv

# 2. Runtime data (DBs, uploads, vectors, exports)
rm -rf backend/data data/uploads data/exports data/chroma data/graph
rm -f backend/data/*.db backend/data/*.db-* 2>/dev/null || true

# 3. Python caches
find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type d -name ".pytest_cache" -prune -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".mypy_cache" -prune -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".ruff_cache" -prune -exec rm -rf {} + 2>/dev/null || true

# 4. Logs
rm -f *.log backend/*.log /tmp/awa_server.log 2>/dev/null || true

# 5. OS junk
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "Thumbs.db" -delete 2>/dev/null || true

# 6. Editor / IDE
rm -rf .vscode .idea

# 7. Old frontend build artefacts (we use static SPA only)
rm -rf frontend/node_modules frontend/.next frontend/out 2>/dev/null || true

echo "After:  $(du -sh . | cut -f1)"
echo
echo "✅ Clean. Now safe to: git add . && git push"
echo "   To re-run locally: make install && make run"
