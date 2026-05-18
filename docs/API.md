# API Reference

The full interactive OpenAPI spec is live at **`/api/docs`** when the server is running.

## Key endpoints

### Auth
- `POST /api/v1/auth/login` — body `{email, password}` → JWT
- `POST /api/v1/auth/register` — same body, role = viewer
- `GET  /api/v1/auth/me`

### Upload
- `POST /api/v1/upload` — multipart `files`, returns list of `DocumentOut`

### Documents
- `GET  /api/v1/documents?page=&page_size=&q=&status=`
- `GET  /api/v1/documents/{id}` — full detail with records + issues
- `GET  /api/v1/documents/{id}/file` — original file download
- `GET  /api/v1/documents/{id}/pages/{n}/image` — preprocessed page image
- `POST /api/v1/documents/{id}/reprocess` — re-run pipeline
- `DELETE /api/v1/documents/{id}`

### Records (review workflow)
- `GET  /api/v1/records/{id}`
- `PATCH /api/v1/records/{id}` — edit fields, mark approved/rejected
- `POST /api/v1/records/{id}/approve`
- `POST /api/v1/records/{id}/reject`

### Validation rules
- `GET  /api/v1/rules`
- `POST /api/v1/rules` — CRUD
- `POST /api/v1/rules/synthesize` — `{text}` → LLM-generated rule

### Search
- `GET  /api/v1/search?q=&mode=hybrid|keyword|vector|graph|page&top_k=20`

### Dashboard
- `GET  /api/v1/dashboard/kpis`
- `GET  /api/v1/dashboard/shift-summary`
- `GET  /api/v1/dashboard/machine-summary`
- `GET  /api/v1/dashboard/daily-throughput`
- `GET  /api/v1/dashboard/top-issues`
- `GET  /api/v1/dashboard/recent-uploads`

### Analytics
- `GET  /api/v1/analytics/anomalies`
- `GET  /api/v1/analytics/quantity-trend`
- `GET  /api/v1/analytics/top-operators`

### Chat
- `POST /api/v1/chat/ask` — `{question}` → `{sql, columns, rows, explanation}`

### Export
- `GET  /api/v1/export/csv?document_id=`
- `GET  /api/v1/export/json`
- `GET  /api/v1/export/xlsx`
- `GET  /api/v1/export/pdf/{document_id}`

### Webhooks
- `GET/POST/DELETE /api/v1/webhooks`
- `POST /api/v1/webhooks/test/{idx}`

### Audit
- `GET  /api/v1/audit?entity_type=&entity_id=&limit=`

### Settings / Prompts
- `GET  /api/v1/settings`
- `GET  /api/v1/settings/prompts`
- `PUT  /api/v1/settings/prompts/{name}` — admin only

### Meta
- `GET  /api/v1/health`
- `GET  /api/v1/ready`
- `GET  /api/v1/metrics` — Prometheus format
- `POST /api/v1/selftest/seed` — load sample dataset

### WebSocket
- `WS   /api/v1/ws/events` — `{event: "document.update"|"job.update", payload: {...}}`
