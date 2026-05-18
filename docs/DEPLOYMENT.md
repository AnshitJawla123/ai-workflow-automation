# 🚀 Deployment

## Sizing recommendation

| Plan | vCPU | RAM | Disk | Concurrent users | Notes |
|---|---|---|---|---|---|
| **Minimum** | 1 | 1 GB | 10 GB | 1-2 | Vision consensus disabled (only 1 provider at a time) |
| **Recommended** | 2 | 2 GB | 20 GB | 5-10 | 3-provider consensus, full RAG |
| **Comfort** | 4 | 4 GB | 50 GB | 20-30 | + local embeddings; lots of headroom |

> The runtime is mostly I/O-bound (waiting for LLM APIs). CPU spikes only during image upscaling and Chroma embeddings.

---

## 1️⃣ Docker (any machine with Docker)

```bash
cp .env.example .env       # set GEMINI_API_KEY / GROQ_API_KEY / OPENROUTER_API_KEY
docker compose up -d --build
# wait ~6 min for first build
curl http://localhost:8000/api/v1/health
```

The compose file mounts `./data` so SQLite + Chroma persist across container restarts.

---

## 2️⃣ Render.com (free tier; one-click)

1. Push the repo to GitHub.
2. New → Web Service → connect repo → Render auto-detects `render.yaml` and `Dockerfile`.
3. In dashboard, set secrets: `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`.
4. Deploy. Health check passes at `/api/v1/health` automatically.
5. Visit the URL — it will show the live app.

**Cost:** $0 on starter plan; persistent disk = $0.25/GB/month.

---

## 3️⃣ Fly.io (free tier; one-click)

```bash
fly auth signup
fly launch --no-deploy --copy-config
fly volumes create app_data --size 1
fly secrets set \
  APP_SECRET_KEY=$(openssl rand -hex 32) \
  GEMINI_API_KEY=... \
  GROQ_API_KEY=... \
  OPENROUTER_API_KEY=...
fly deploy
```

`fly.toml` requests 2 vCPU / 2 GB. Bump to `cpus = 4, memory_mb = 4096` for heavier load.

---

## 4️⃣ Bare metal / VPS

```bash
# Ubuntu 22.04+
sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv tesseract-ocr poppler-utils libgl1 libglib2.0-0
git clone <repo> && cd ai-workflow-automation
cp .env.example .env && nano .env
make install
nohup .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

Put **nginx** in front for TLS:
```nginx
server {
    server_name example.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        client_max_body_size 25M;
    }
}
```

---

## Env vars (required)

| Var | Required | Default |
|---|---|---|
| `APP_SECRET_KEY` | **yes** (for cookie signing + JWT) | dev fallback (replace!) |
| One of: `GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` | **yes** for extraction accuracy | — |
| `DATABASE_URL` | no | `sqlite:///./data/app.db` |
| `ALLOW_ANONYMOUS` | no | `true` |
| `WORKSPACE_DOC_LIMIT` | no | 50 |
| `WORKSPACE_STORAGE_BYTES` | no | 52428800 |
| `CORS_ORIGINS` | no | `http://localhost:3000,http://localhost:8000` |

Full list in `.env.example`.

---

## Observability

- `GET /api/v1/health` → JSON status + LLM provider count + consensus active
- `GET /api/v1/ready` → readiness gate (fails if no LLM provider)
- `GET /api/v1/metrics` → Prometheus text format

Scrape `/api/v1/metrics` from Grafana Cloud or Datadog if needed.

---

## Backups

Everything lives in `./data/`:
```
./data/
├── app.db              # main relational store
├── cache.db            # LLM response cache (safe to drop)
├── chroma/             # vector store
├── graph/              # JSON triples
└── uploads/<uuid>/     # original files
```

A nightly `tar -czf backup.tgz ./data` is enough. Restore = untar and start.
