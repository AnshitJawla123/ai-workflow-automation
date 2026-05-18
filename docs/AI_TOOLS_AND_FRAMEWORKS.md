# AI Tools, Frameworks & Libraries

Complete catalog of every AI tool, model, library, and external service used in this project.

---

## 🤖 AI Agents / Development Tools

| Tool | Role | Where it appears |
|---|---|---|
| **Interactive AI Agent** (Anthropic-family backbone) | Primary coding agent — planned architecture, wrote every file, ran live shell tests, fixed bugs in real-time | Whole codebase |
| **Anthropic Claude** | Reasoning, code generation, prompt design | All code + 10 versioned prompt templates |

> No GitHub Copilot, Cursor, Codex, Replit, ChatGPT-Plus, or other secondary agents were used in this build. Every line was produced through the interactive loop.

---

## 🧠 AI Models (Runtime)

### Vision LLMs (OpenRouter free tier — handwriting → JSON)
Rotating fallback chain in `backend/app/services/llm/openrouter.py`:
1. `google/gemma-4-31b-it:free` (primary; **verified working** in live test)
2. `google/gemma-4-26b-a4b-it:free` (secondary)
3. `nvidia/nemotron-nano-12b-v2-vl:free`
4. `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`

> The free vision tier on OpenRouter is **heavily rate-limited upstream** (HTTP 429 from upstream providers). The code handles this with exponential-backoff retries and rotation. For production, add your own provider key at https://openrouter.ai/settings/integrations to bypass shared rate limits.

### Text LLMs (OpenRouter free tier — for chat / rule synthesis / OCR-text structuring)
1. `qwen/qwen3-next-80b-a3b-instruct:free`
2. `deepseek/deepseek-v4-flash:free` (**verified working** in live test)
3. `openai/gpt-oss-120b:free`
4. `z-ai/glm-4.5-air:free`

### Embeddings (local — no API)
- `sentence-transformers/all-MiniLM-L6-v2` (~80 MB model, CPU)
  - Used in `backend/app/services/rag/vector_store.py`

### Local OCR
- **Tesseract 5.5.2** (offline, free) — handwriting OCR fallback used when vision LLM is rate-limited
- **HuggingFace Inference (TrOCR)** — also configured, currently returns "model not supported by provider hf-inference" (HF changed their router API; the code still supports the legacy endpoint and will pick up newer providers as HF re-enables free routing)

### Document AI
- **OpenCV 4.10** — deskew + denoise + adaptive thresholding for image normalization (`backend/app/utils/files.py::preprocess_image`)
- **pdf2image / poppler-utils** — PDF page rasterization

---

## 🐍 Python Frameworks & Libraries (backend)

| Package | Version | Purpose |
|---|---|---|
| **fastapi** | 0.115.0 | REST + WebSocket framework |
| **uvicorn[standard]** | 0.30.6 | ASGI server |
| **pydantic** | 2.9.2 | Schema validation |
| **pydantic-settings** | 2.5.2 | Env-driven config |
| **sqlalchemy** | 2.0.35 | ORM (SQLite default, Postgres-ready) |
| **alembic** | 1.13.3 | DB migrations |
| **aiosqlite** | 0.20.0 | Async SQLite |
| **python-jose** | 3.3.0 | JWT |
| **passlib[bcrypt]** + bcrypt==4.0.1 | — | Password hashing |
| **httpx** | 0.27.2 | HTTP client (LLM calls) |
| **tenacity** | 9.0.0 | Retry decorators (custom 429-aware retry built on top) |
| **apscheduler** | 3.10.4 | Scheduled tasks |
| **opencv-python-headless** | 4.10.0.84 | Image preprocessing |
| **pillow** | 10.4.0 | Image I/O |
| **numpy / pandas** | 1.26.4 / 2.2.3 | Numeric work |
| **pypdf** | 5.0.1 | PDF metadata |
| **pdf2image** | 1.17.0 | PDF → JPEG |
| **chromadb** | 0.5.15 | Embedded vector store |
| **sentence-transformers** | 3.1.1 | Local embeddings |
| **networkx** | 3.3 | GraphRAG entity graph |
| **pytesseract** | 0.3.13 | Tesseract Python binding |
| **reportlab** | 4.2.5 | PDF report generation |
| **openpyxl** | 3.1.5 | XLSX export |
| **websockets** | 13.1 | WS support for uvicorn |
| **jinja2** | 3.1.4 | Templating |
| **email-validator** | (latest) | Pydantic EmailStr validator |

---

## ⚛️ Frontend stack

| Tool | Loaded from | Purpose |
|---|---|---|
| **React 18** | unpkg CDN | UI framework |
| **Tailwind CSS** (JIT) | cdn.tailwindcss.com | Styling, dark mode |
| **Recharts 2.12** | jsdelivr CDN | Charts (bar/line/pie) |
| **Babel standalone** | unpkg CDN | In-browser JSX compile (zero node build) |

> Single `index.html` + `app.js` (~700 lines) — no `node_modules`, no build step. This is intentional: the static SPA is served directly by FastAPI from `backend/app/static/`, keeping the deploy artifact to a single Python process.

---

## ☁️ External free services (optional)

| Service | URL | Free tier |
|---|---|---|
| **OpenRouter** | https://openrouter.ai | Free vision + text LLMs (rate-limited upstream) |
| **HuggingFace Inference** | https://huggingface.co | Free hosted inference for many models |
| **Render** | https://render.com | Free web service tier (works with `render.yaml`) |
| **Fly.io** | https://fly.io | Free 3 small VMs (works with `fly.toml`) |
| **Oracle Cloud Always Free** | https://oracle.com/cloud/free | 4 vCPU + 24 GB ARM VM — best free tier |

---

## 🛠️ Operational tools

| Tool | Use |
|---|---|
| **Docker 24+** | Single-container packaging (`Dockerfile`) |
| **docker-compose v2** | `docker-compose.yml` for separated config |
| **poppler-utils** | PDF rendering (bundled in Docker image) |
| **tesseract-ocr** | Offline OCR (bundled in Docker image) |
| **GitHub Actions** (not bundled — add later if needed) | CI for lint/test/build |

---

## 🔐 No secret material is committed

All API keys live in `.env` (gitignored). `.env.example` ships with empty placeholders.
