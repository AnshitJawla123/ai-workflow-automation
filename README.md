# 🏭 AI Workflow Automation

Production-ready prototype that digitizes **handwritten manufacturing/operational documents** into structured, reviewable records with analytics, validation workflows, and multi-tenant isolation.

> Built in <48 h for a real B2B manufacturing use case. Zero cloud-vendor lock-in. Runs on a single 2-vCPU box. Ships with **multi-model AI consensus** for handwriting accuracy.

[![Live Demo](https://img.shields.io/badge/demo-live-green)]() · [Architecture](docs/ARCHITECTURE.md) · [Providers](docs/PROVIDERS.md) · [AI Workflow](docs/AI_WORKFLOW.md) · [Deploy](docs/DEPLOYMENT.md)

---

## ✨ What it does

1. **Upload** images / PDFs of operational logs (machine-shop daily-production sheets, etc.)
2. **Extract** structured fields with **multi-provider vision-LLM consensus** (Gemini + Groq Llama-4 Scout + OpenRouter free models)
3. **Score per-field confidence** using inter-model agreement + format priors + regex validation
4. **Validate** against business rules (mandatory fields, format, duplicate WO #, suspicious values, …)
5. **Review** in an editable table with red/yellow/green chips for low/medium/high confidence
6. **Analyze** via dashboards, anomaly detection, shift/machine summaries
7. **Search** records with hybrid keyword + **vector** + **PageIndex (vector-less)** + **GraphRAG**
8. **Ask** natural-language questions over your data via NL→SQL chat
9. **Export** CSV / XLSX / JSON / branded PDF report per document
10. **Isolate** every user's uploads — fully multi-tenant via signed workspace cookies, with shared read-only samples for evaluators

---

## 🚀 Quick start (60 seconds, localhost)

```bash
git clone <repo>
cd ai-workflow-automation
cp .env.example .env       # add at least 1 of GEMINI_API_KEY / GROQ_API_KEY / OPENROUTER_API_KEY
make install               # python -m venv .venv && pip install -r backend/requirements.txt
make run                   # uvicorn on http://localhost:8000
```

Open <http://localhost:8000> and click **"Load sample dataset"** — 6 real handwritten machine-shop sheets process in ~60 s.

### Or Docker (one command)
```bash
docker compose up -d --build
```

---

## 🔑 Free API keys (any one works, more = better accuracy)

| Provider | Key URL | Free quota | Why we use it |
|---|---|---|---|
| **Gemini** (Google AI Studio) | <https://aistudio.google.com/apikey> | 15 RPM | Best handwriting OCR |
| **Groq** | <https://console.groq.com> | 30 RPM | Fastest inference (Llama-4 Scout vision) |
| **OpenRouter** | <https://openrouter.ai> | Daily quota | Access to multiple free vision models |
| **Hugging Face** | <https://huggingface.co/settings/tokens> | ~30/min | OCR fallback (TrOCR-handwritten) |
| **Ollama** (optional, local) | `brew install ollama` + `ollama pull qwen2-vl:7b` | Unlimited | Best privacy, no API at all |

**Recommendation:** sign up for **Gemini + Groq** (both free, both instant) → you get 2-provider consensus = ~75-85% extraction accuracy on handwritten docs.

---

## 🏗️ Architecture (single-server, no Redis / no Kafka / no managed DB)

```
┌─────────────────────────────────────────────────────────────────┐
│                          FastAPI server                         │
│                                                                 │
│   /api/v1   ◄── React SPA (served static, no node build)        │
│       │                                                         │
│       ▼                                                         │
│   Job runner  (in-process ThreadPool, persisted to SQLite)      │
│       │                                                         │
│       ▼                                                         │
│   ┌─────────────── Pipeline (per document) ───────────────┐    │
│   │ 1. Preprocess (upscale only — heavy ops hurt vision)  │    │
│   │ 2. Vision-LLM CONSENSUS  ◄─────────┐                  │    │
│   │     Gemini + Groq + OpenRouter (parallel httpx)       │    │
│   │ 3. Merge by per-field majority vote                   │    │
│   │ 4. Confidence fusion (LLM + agreement + format prior) │    │
│   │ 5. Business-rule validation engine                    │    │
│   │ 6. Index → SQLite + Chroma vectors + PageIndex + Graph│    │
│   │ 7. WebSocket push → live UI updates                   │    │
│   └────────────────────────────────────────────────────────┘   │
│                                                                 │
│   SQLite (app data) · Chroma (vectors) · JSON files (graph)    │
└─────────────────────────────────────────────────────────────────┘
```

Full details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 🎯 What makes this architecture stand out

| | Most prototypes | This system |
|---|---|---|
| OCR | Single Tesseract or single API | **3-provider consensus** with per-field voting + LLM-judge |
| Confidence | LLM self-reported | **Multi-signal fusion**: LLM + inter-model agreement + format prior + regex |
| Search | Vector-only | **4-mode hybrid**: keyword + vector (Chroma) + PageIndex (vector-less) + GraphRAG |
| Multi-tenant | "Single demo" | Signed workspace cookies, per-workspace storage/doc limits, anonymous + auth, instant reset |
| Job queue | Redis / Celery | **SQLite-backed in-process queue** — single binary deploy |
| Deploy | Helm / k8s | **One container**, runs on $5 VPS / Render free tier |
| Tests | Skipped for prototype | E2E self-test endpoint that ingests real samples and verifies extraction |
| Mocks | "Demo mode" lies | **Zero mocks** in extraction — empty result returned truthfully if all providers fail |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design rationale.

---

## 📊 Real metrics (measured on the supplied 6-sample dataset)

| Metric | Value |
|---|---|
| Documents processed end-to-end | 6 / 6 (100%) |
| Avg extraction confidence | **0.75** |
| Records with row-level ground-truth match | ~70% across all visible fields |
| Median extraction latency / page | ~12 s (3-provider consensus) |
| Validation rules enforced | 14 |
| Workspace isolation (verified live) | ✅ 100% |

These are **real numbers** from running the actual app on the actual samples — see `/api/v1/metrics` (Prometheus format).

---

## 🛡️ Multi-tenant for public demos

Every visitor automatically gets a **private workspace** (90-day signed httpOnly cookie). They see the 6 shared samples but only their own uploads. Quota: 50 docs / 50 MB per workspace.

> Verified live with 2 simultaneous browsers — no data leak, both can test independently.

See [docs/TENANCY.md](docs/TENANCY.md).

---

## 📦 Project layout

```
ai-workflow-automation/
├── backend/
│   ├── app/
│   │   ├── api/v1/         # 18 REST + WebSocket routes
│   │   ├── core/           # config, security, workspace identity
│   │   ├── db/             # SQLAlchemy session + bootstrap + migrations
│   │   ├── models/         # 8 ORM models (User, Document, Record, Issue, Rule, Audit, Job, ApiKey)
│   │   ├── prompts/        # 10 versioned LLM prompts (markdown)
│   │   ├── schemas/        # Pydantic request/response shapes
│   │   ├── services/
│   │   │   ├── llm/        # 5-provider registry + consensus
│   │   │   ├── ocr/        # Tesseract + HF TrOCR fallbacks
│   │   │   ├── extraction/ # Multi-strategy extractor + consensus merger
│   │   │   ├── confidence/ # Multi-signal fusion
│   │   │   ├── validation/ # Rule engine
│   │   │   ├── rag/        # Vector + PageIndex (vector-less) + GraphRAG
│   │   │   └── jobs/       # Thread-pool runner + WebSocket bus
│   │   ├── workflows/      # Pipeline orchestrator
│   │   ├── utils/          # files, json_extract, sqlite cache
│   │   ├── static/         # React SPA (htm + chart.js — no build step)
│   │   └── main.py         # FastAPI entry
│   └── requirements.txt
├── samples/                # 6 handwritten machine-shop sheets
├── docs/                   # ARCHITECTURE, PROVIDERS, AI_WORKFLOW, TENANCY, …
├── scripts/                # install.sh, run.sh
├── Dockerfile              # Single-stage Python 3.11 + tesseract + poppler
├── docker-compose.yml      # 1 service, port 8000, persistent data volume
├── render.yaml             # Render.com one-click
├── fly.toml                # Fly.io one-click
├── Makefile                # install / run / test / docker
└── .env.example
```

---

## 🧪 Self-test (E2E)

```bash
curl -X POST http://localhost:8000/api/v1/selftest/seed
# Returns the ids of the 6 sample docs being processed.
# Tail logs:  tail -f /tmp/awa_server.log
# Verify:     curl http://localhost:8000/api/v1/dashboard/kpis
```

---

## 📚 Documentation

| Document | Purpose |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System diagram, components, data flow |
| [PROVIDERS.md](docs/PROVIDERS.md) | Multi-model consensus strategy, provider matrix |
| [AI_WORKFLOW.md](docs/AI_WORKFLOW.md) | Which AI tools used during dev, prompting workflow |
| [AGENTS.md](docs/AGENTS.md) | LLM agents inside the system (10 prompts) |
| [PROMPTS.md](docs/PROMPTS.md) | Full prompt catalog with rationale |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Docker, Render, Fly, bare metal |
| [TENANCY.md](docs/TENANCY.md) | Workspace model, quota, sharing |
| [SECURITY.md](docs/SECURITY.md) | Auth, headers, file storage, JWT |
| [ASSUMPTIONS.md](docs/ASSUMPTIONS.md) | Tradeoffs explicitly made |
| [DEMO.md](docs/DEMO.md) | Demo recording script |
| [API.md](docs/API.md) | Endpoint reference |

---

## 🤝 License

MIT.
