# 🤔 Assumptions & Tradeoffs

## Domain assumptions
- Documents are **machine-shop daily-production sheets** with the columns:
  *S.No, Date, Shift (I/II/III), Emp. No (BT####), Opn Code (6 digits), Machine No. (MC-###), Work Order No., Qty. Prod., Time taken (hrs)*
- Schema is extensible — `ExtractedRecord` has core columns + JSON `extra_fields` for new field types
- Handwriting style is consistent ballpoint pen on printed grid (matches the supplied samples)

## Tradeoffs we explicitly made

| Decision | Tradeoff | Why |
|---|---|---|
| **SQLite over Postgres** | Limited horizontal scale | Zero ops; works for 10k docs/day on single VPS |
| **In-process job runner over Celery** | Single-node only | No Redis required; persisted to SQLite; trivial deploy |
| **htm + React UMD over Next.js build** | No SSR, no code splitting | Eliminates 1 GB Node toolchain; 180 MB container |
| **Vision-LLM consensus over fine-tuned OCR model** | Slower (~12 s/page) | No GPU needed; uses free APIs; better than any single model |
| **Workspace cookie over forced signup** | Less identity precision | Zero-friction demo for evaluators |
| **Embedded Chroma over Qdrant** | Single-node | No second service; easy backup; <100k vectors works fine |
| **Tesseract local + HF TrOCR remote** | 2 fallback chains | First works offline; second beats Tesseract on handwriting when available |
| **JSON triples for GraphRAG** | Not full Neo4j | Tiny corpus, trivial to query, zero ops |
| **No PII redaction layer** | Possible PII leak if logs uploaded | Out of scope for a 48 h prototype; trivial to add |
| **HS256 JWT over RS256** | Single secret | Single-node; rotate via env redeploy |

## Things we deliberately did NOT build

- **WebSocket auth tokens** — only cookie/JWT propagation
- **Email notifications** — SMTP settings present in config but unused
- **Multi-language UI** — English only
- **Mobile apps** — web-only
- **Real-time collaboration on review** — last-write-wins
- **Custom rule DSL** — current rules are Python; LLM can synthesize new ones via `/api/v1/rules/synthesize`

## Things that look broken but aren't

- **0 providers at health on first boot** — fixed by adding `python-dotenv` early load; if it persists, check that `.env` exists at one of `[".env", "../.env", "/app/.env"]`
- **Some samples show low confidence (0.4)** — that's by design; the handwriting really is ambiguous and consensus deliberately collapses confidence when models disagree. The fields are still extracted; UI highlights them yellow for human review.
- **Docker build takes ~6 minutes** — opencv-python-headless + numpy + Pillow + chromadb compile native bindings. Pre-built wheels work for python:3.11-slim.

## What would change if we had another 48 h

- Postgres + Alembic migrations
- Per-field bbox highlighting on the image preview during review (we collect bbox but don't visualize yet)
- Bulk approve / reject with shift+click
- LLM-judge re-read for low-confidence rows
- Local OCR-LLM model (qwen2-vl) for fully offline mode
- Playwright E2E tests
- Audit-log export to JSONL for SIEM ingestion
