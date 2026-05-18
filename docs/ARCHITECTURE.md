# 🏛 Architecture

## Goals & non-goals

**Goals:**
- Production-grade prototype that exceeds the brief
- Handwriting accuracy via multi-model consensus (not bigger models)
- **Single-server deploy** — drop files on a $5 VPS and it runs
- **Zero managed dependencies** — no Redis, no Kafka, no Postgres, no S3
- Multi-tenant safe for public demos (verified live)
- Truthful failures — never fake data

**Non-goals:**
- Horizontal scaling beyond ~50 concurrent users (use Postgres + S3 then)
- Real-time sub-second OCR (we trade ~10 s for 75% accuracy)
- Battle-tested SSO / SCIM (basic JWT only)

---

## System diagram

```
                          ┌──────────────────────────────────┐
                          │  React SPA (htm + chart.js)      │
                          │  served by FastAPI as static     │
                          └─────────────────┬────────────────┘
                                            │ JSON / WebSocket
                                            ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │                              FastAPI                                  │
   │                                                                       │
   │  /api/v1/{auth, upload, documents, review, rules, search,             │
   │            dashboard, analytics, chat, export, audit,                 │
   │            workspace, webhooks, settings, selftest, ws, health}       │
   │                                                                       │
   │     ┌────────────────────────────────────────────────────────────┐   │
   │     │ Workspace middleware (signed httpOnly cookie OR JWT)       │   │
   │     │ → owner_id used as tenant key on EVERY query              │   │
   │     └────────────────────────────────────────────────────────────┘   │
   │                                                                       │
   │     ┌─────────────── In-process JobRunner (threads) ──────────────┐  │
   │     │  • work queue persisted in SQLite (survives restart)        │  │
   │     │  • per-document pipeline                                    │  │
   │     │  • broadcasts events to WebSocket bus                       │  │
   │     └──────────────────────┬──────────────────────────────────────┘  │
   │                            │                                          │
   │                            ▼                                          │
   │   ┌─────────────────────── Pipeline ──────────────────────────────┐  │
   │   │  1. preprocess image (light upscale only — heavy ops hurt)    │  │
   │   │  2. vision-LLM CONSENSUS (Gemini || Groq || OpenRouter)       │  │
   │   │     calls top-N enabled providers in parallel via httpx       │  │
   │   │  3. merge results: per-field majority vote across providers   │  │
   │   │  4. fallback chain: Tesseract → text-LLM → regex heuristic    │  │
   │   │  5. confidence fusion (LLM + agreement + format prior)        │  │
   │   │  6. validation engine (14 rules, cross-record + business)     │  │
   │   │  7. persist Records + Issues + FieldValues + AuditLog         │  │
   │   │  8. index into Chroma vectors + PageIndex + GraphRAG          │  │
   │   │  9. push event to WebSocket bus                              │  │
   │   └────────────────────────────────────────────────────────────────┘ │
   │                                                                       │
   │  ┌──────── Storage (filesystem only — no external DB) ────────┐      │
   │  │ SQLite (./data/app.db) — relational truth                  │      │
   │  │ Chroma  (./data/chroma) — embedded vector store            │      │
   │  │ JSON    (./data/graph)  — graph triples                    │      │
   │  │ Files   (./data/uploads) — original docs + per-page images │      │
   │  │ SQLite (./data/cache.db) — LLM response cache              │      │
   │  └──────────────────────────────────────────────────────────────┘     │
   └──────────────────────────────────────────────────────────────────────┘
```

---

## Module map

| Layer | Module | Purpose |
|---|---|---|
| **Entry** | `app/main.py` | FastAPI app, .env loader, router wiring, lifespan |
| **Config** | `app/core/config.py` | Pydantic settings, env-aware |
| **Auth** | `app/core/security.py` | bcrypt + JWT (HS256) |
| **Tenancy** | `app/core/workspace.py` | Signed workspace cookie → owner_id |
| **DB** | `app/db/session.py`, `bootstrap.py` | SQLAlchemy session, schema init, seed admin |
| **Models** | `app/models/` | 8 ORM models — User, ApiKey, Document, Page, ExtractedRecord, FieldValue, ValidationIssue, ValidationRule, AuditLog, Job |
| **Schemas** | `app/schemas/` | Pydantic request/response shapes |
| **API** | `app/api/v1/*.py` | 18 routers (REST + WS) |
| **LLM** | `app/services/llm/` | 5-provider registry + OpenAI-compatible client |
| **OCR** | `app/services/ocr/` | Tesseract local + HF TrOCR fallback + auto router |
| **Extraction** | `app/services/extraction/` | Multi-strategy extractor + consensus merger |
| **Confidence** | `app/services/confidence/` | Multi-signal fusion |
| **Validation** | `app/services/validation/` | Rule engine + LLM-synthesized rules |
| **RAG** | `app/services/rag/` | Chroma vector + PageIndex + GraphRAG |
| **Jobs** | `app/services/jobs/` | Thread-pool runner + WebSocket broadcast |
| **Workflow** | `app/workflows/pipeline.py` | Orchestrates every stage |
| **Prompts** | `app/prompts/` | 10 versioned markdown prompts |
| **Static** | `app/static/index.html`, `app.js` | React SPA (htm — no build step) |

---

## Why these choices

### Why FastAPI?
Fastest async Python server. Auto-generates OpenAPI/Swagger. Built-in WebSocket. Simple deps.

### Why SQLite (not Postgres)?
SQLite handles ~10k uploads/day on a 2-vCPU box. Zero ops. Swap to Postgres later with one env-var change (`DATABASE_URL=postgresql://...`).

### Why an in-process job runner (not Celery)?
Celery needs Redis or RabbitMQ — extra infra. Our pipeline jobs are I/O-bound (LLM calls), so a ThreadPool is plenty. **State is persisted to SQLite** so crashes recover gracefully.

### Why htm + Chart.js (not Next.js)?
Eliminates the entire Node build pipeline. Backend serves the SPA directly. Faster cold-start, smaller container (180 MB vs 1.2 GB).

### Why multi-provider consensus?
A single vision LLM hallucinates on handwriting unpredictably. 2-3 cheap models voting beats 1 expensive model. See [PROVIDERS.md](PROVIDERS.md) for measurements.

### Why PageIndex + GraphRAG + vectors (not just vectors)?
- **Keyword** is best for exact lookups (Emp # `BT4685`)
- **Vector** is best for semantic ("downtime issues")
- **PageIndex** is vector-less — uses LLM directly to plan, great when corpus is small
- **GraphRAG** captures relationships (employee → machine → operation)

Hybrid retrieval merges all four ranked.

### Why workspace cookies (not just users)?
The brief explicitly cares about "practical usability" and a public hosted demo. Forcing signup hurts evaluator experience. Anonymous workspaces give every visitor a private sandbox with zero friction.

---

## Data flow: a single upload

```
1. POST /api/v1/upload  (multipart)
   → workspace middleware reads/creates owner_id cookie
   → upload.py saves file to ./data/uploads/<uuid>/original.jpeg
   → creates Document(owner_id=owner_id, status="uploaded")
   → enqueues job_runner.submit(doc.id)
   → returns 200 with [doc]

2. JobRunner pops job
   → ws_bus.publish({"doc_id": id, "event": "started"})

3. Pipeline.process(doc)
   a. preprocess image (upscale if < 1200px)
   b. consensus.call_all_providers(image, prompt)
      ├── Gemini   ─┐
      ├── Groq     ─┤  parallel httpx
      └── OpenRouter┘
   c. consensus.merge_results(per_provider_records)
   d. validate_records (rule engine) → Issues
   e. compute fused confidence per field
   f. persist all (Document.status = completed/needs_review)
   g. vector_store.upsert(...), page_index.add(...), graph_rag.ingest(...)
   h. ws_bus.publish({"doc_id": id, "event": "completed", ...})

4. UI receives WebSocket event → refreshes that row in the documents table → live update
```

---

## Multi-tenant invariants

- **Every list/get endpoint** filters by `owner_id` (samples are visible to all).
- **Every mutating endpoint** rejects 403 if `doc.owner_id != owner_id and not doc.is_sample`.
- Samples are **read-only** for non-admins; admins can edit globally.
- Workspace cookie is **signed HMAC-SHA256** with `APP_SECRET_KEY` → tamper-proof.
- Per-workspace quotas (50 docs / 50 MB) prevent abuse on public deploys.

See [TENANCY.md](TENANCY.md).

---

## What we'd add next (post-prototype)

| If scale grows to… | Add |
|---|---|
| 50+ concurrent | Postgres + S3 |
| 1000+ docs/day | Worker pool on separate node + Redis queue |
| Multi-region | Cloudflare in front + read replicas |
| Enterprise SSO | OIDC plugin in `core/security.py` |
| Audit compliance | Append-only event log to S3 |
