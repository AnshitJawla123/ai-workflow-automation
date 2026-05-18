# Operations Runbook

Live operational procedures for an on-call engineer running AI Workflow Automation.

## 🚦 Health checks

| Endpoint | Expected |
|---|---|
| `GET /api/v1/health` | `{"status":"ok","db":true}` |
| `GET /api/v1/ready` | `{"ready":true}` |
| `GET /api/v1/metrics` | Prometheus format with `awa_documents_total`, `awa_records_total`, `awa_validation_issues_total` |

## 🟥 Common alerts & responses

### 1. `awa_documents_total` not growing
- Check `/api/v1/dashboard/recent-uploads` — are uploads coming in?
- Inspect logs: `grep '"logger":"main"' app.log | tail`
- Verify upload endpoint: `curl -X POST -F files=@sample.jpg http://host/api/v1/upload`

### 2. Documents stuck in `extracting`
**Root cause typically:** upstream LLM provider returning 429 or 5xx.
- `grep "429\|strategy=" app.log | tail`
- Confirm `.env` has `OPENROUTER_API_KEY`.
- Visit https://openrouter.ai/settings/integrations and add your own provider key to escape shared rate-limits.
- Restart the app: `pkill -f uvicorn && ./scripts/run.sh`

### 3. High `validation_issues` count
- Review the most common rule code: `GET /api/v1/dashboard/top-issues`
- Either fix the upstream OCR (more accurate model / clearer images), tune the rule, or disable it via `PATCH /api/v1/rules/{id}`.

### 4. Disk full
- Data lives in `./data/` (uploads + sqlite + chroma + graph + cache + exports).
- Clean up oldest uploads: `find data/uploads -mtime +30 -delete`
- Vacuum SQLite: `sqlite3 data/app.db 'VACUUM;'`

### 5. WebSocket disconnects
- Make sure your reverse proxy passes Upgrade headers (see `docs/DEPLOYMENT.md` nginx snippet).

## 🔄 Backup & restore

**Backup** (whole state):
```bash
tar czf awa-backup-$(date +%F).tar.gz data/
```

**Restore**:
```bash
docker compose down
tar xzf awa-backup-2026-05-18.tar.gz
docker compose up -d
```

## 🔑 Rotating credentials

```bash
# 1. Generate new admin password hash (one-liner)
python3 -c "from passlib.hash import bcrypt; print(bcrypt.using(rounds=12).hash('NEW-STRONG-PW'))"

# 2. Patch in DB
sqlite3 data/app.db "UPDATE users SET password_hash='<HASH>' WHERE email='admin@local.dev';"

# 3. Rotate JWT secret
sed -i '' 's/APP_SECRET_KEY=.*/APP_SECRET_KEY=$(openssl rand -hex 32)/' .env
# Restart app — all existing tokens invalidated.
```

## 📈 Capacity targets (Recommended 2 vCPU / 4 GB)

| Metric | Target |
|---|---|
| Concurrent active users | 10 |
| Documents processed/min | 4–8 |
| Records search latency | < 200ms |
| Dashboard load | < 500ms |

## 🚒 Disaster recovery

If the app process crashes:
- `JobRunner._requeue_pending` automatically re-queues any document stuck in non-terminal status on next startup.
- SQLite WAL mode means no data loss from kill -9.
- For "lost" uploads (uploaded but pre-processing died), trigger a reprocess via the API.
