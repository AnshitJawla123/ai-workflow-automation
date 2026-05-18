# Feature Coverage Matrix — Problem Statement → Implementation

Maps every requirement from the assignment brief to backend endpoint, UI page,
and code file. Use this as a review checklist.

## Core Requirements

### 1. Document Upload
| Requirement | Status | Endpoint | UI page | Code |
|---|---|---|---|---|
| Upload images | ✅ | `POST /api/v1/upload` | `#upload` | `api/v1/upload.py` |
| Upload PDFs | ✅ | same | same | same (pdf2image renders to PNG) |
| Preview uploaded files | ✅ | `GET /api/v1/documents/{id}/pages/{n}/image` | `#doc/:id` | `api/v1/documents.py` |
| View upload history | ✅ | `GET /api/v1/documents` | `#documents` | `api/v1/documents.py` |

### 2. AI-Based Data Extraction
| Requirement | Status | Implementation |
|---|---|---|
| OCR | ✅ | PaddleOCR → HF TrOCR → Tesseract chain (`services/ocr/router.py`) |
| AI/LLM extraction | ✅ | Multi-provider vision LLM (`services/llm/providers.py`) |
| Date | ✅ | extracted, normalized to ISO `YYYY-MM-DD` |
| Shift | ✅ | normalized to `I` / `II` / `III` |
| Employee Number | ✅ | preserved verbatim |
| Operation Code | ✅ | preserved verbatim |
| Machine Number | ✅ | preserved verbatim (e.g., MC-730) |
| Work Order Number | ✅ | preserved + duplicate detection |
| Quantity Produced | ✅ | parsed int |
| Time Taken | ✅ | parsed float (hours) |
| Custom extraction schema | ✅ | extensible via `prompts/02_field_extraction.md` |

### 3. Review Workflow
| Requirement | Status | Endpoint | UI page |
|---|---|---|---|
| Display editable records | ✅ | `GET /api/v1/documents/{id}` | `#doc/:id` |
| Manual correction | ✅ | `PATCH /api/v1/records/{id}` | inline form |
| Save reviewed records | ✅ | same | "💾 Save" / "✓ Approve" / "✗ Reject" buttons |

### 4. Confidence Scoring
| Requirement | Status | Implementation |
|---|---|---|
| Per-field confidence | ✅ | `FieldValue.confidence` 0.0–1.0 |
| Per-record confidence | ✅ | `Record.overall_confidence` |
| Visual highlighting | ✅ | UI `ConfChip`: green ≥0.85, amber ≥0.60, red <0.60 |
| Uncertain field surfacing | ✅ | low-conf rows tagged `needs_review`, listed in dashboard |
| LLM-as-Judge cross-check | ✅ | `services/confidence/fusion.py` |

### 5. Validation & Exception Handling
| Rule type | Code | File |
|---|---|---|
| Missing mandatory fields | `REQ.{field}` | `services/validation/engine.py` |
| Invalid shift values | `SHIFT.INVALID` | same |
| Incorrect machine code format | `MACHINE.FORMAT` (regex `^[A-Z]{2,3}-?\d{2,4}$`) | same |
| Suspicious numeric values | `QTY.SUSPICIOUS` (z-score > 3) | `services/rag/...` + `engine.py` |
| Empty quantity fields | `QTY.EMPTY` | `engine.py` |
| Duplicate work order numbers | `WO.DUPLICATE` | `engine.py` (cross-document scan) |
| User-added NL rules | LLM-synthesized | `prompts/04_validation_rule_synthesis.md` |
| Highlight records/fields needing review | ✅ | UI: chips + `validation_issues` list per record |

### 6. Dashboard & Analytics
| Insight | Status | Endpoint | UI |
|---|---|---|---|
| Total uploads | ✅ | `/dashboard/kpis` | KPI card |
| Validation failures | ✅ | same | KPI card + top-issues list |
| Shift-wise summaries | ✅ | `/dashboard/shift-summary` | bar chart |
| Quantity summaries | ✅ | `/dashboard/kpis` + daily-throughput | KPI + line chart |
| Machine-wise summaries | ✅ | `/dashboard/machine-summary` | horizontal bar |
| Daily throughput | ✅ | `/dashboard/daily-throughput` | line chart |
| Top operators | ✅ | `/analytics/top-operators` | bar chart |
| Quantity trend | ✅ | `/analytics/quantity-trend` | line chart |
| Anomalies | ✅ | `/analytics/anomalies` | cards w/ z-score |
| LLM-generated insights | ✅ | `prompts/09_dashboard_insight.md` | (server-side) |

### 7. Search & History
| Requirement | Status | Endpoint | UI |
|---|---|---|---|
| View previous uploads | ✅ | `GET /api/v1/documents` | `#documents` |
| Search records | ✅ | `GET /api/v1/search?q=...&mode=hybrid` | `#search` |
| Filter | ✅ | status filter dropdown | `#documents` |
| Open previously processed documents | ✅ | `#doc/:id` | sidebar nav |
| **Bonus** Keyword + Vector + PageIndex + GraphRAG modes | ✅ | `mode=keyword|vector|page|graph|hybrid` | `#search` |
| **Bonus** Ask-your-data (NL → SQL) | ✅ | `POST /chat/ask` | `#chat` |

## Submission Requirements

| Item | Status | Location |
|---|---|---|
| Complete source code | ✅ | this repo |
| `README.md` with setup | ✅ | `/README.md` |
| Architecture/workflow overview | ✅ | `/docs/ARCHITECTURE.md` |
| `.env.example` | ✅ | `/.env.example` |
| Assumptions/tradeoffs | ✅ | `/docs/ASSUMPTIONS.md` |
| Demo video | ⏳ | record after first deploy — `/docs/DEMO.md` script |
| `AGENTS.md` | ✅ | `/AGENTS.md` |
| `AI_WORKFLOW.md` | ✅ | `/docs/AI_WORKFLOW.md` |
| Hosted demo URL | ⏳ | Render/Fly configs ready — `/docs/DEPLOYMENT.md` |

## "Bonus" features beyond the brief

| Feature | Why it matters | Where |
|---|---|---|
| Multi-provider LLM registry | survives 1-provider outage | `services/llm/providers.py` |
| PageIndex (vectorless RAG) | beats vector RAG on hierarchical docs | `services/rag/page_index.py` |
| GraphRAG | answers cross-entity questions | `services/rag/graph_rag.py` |
| Real-time WebSocket status | per-doc progress in UI | `services/jobs/ws_bus.py` |
| Audit log with diffs | compliance-grade traceability | `api/v1/audit.py` |
| JWT + RBAC | multi-user prod-ready | `core/security.py` |
| Outbound webhooks | downstream system integration | `api/v1/webhooks.py` |
| NL → rule synthesis | non-tech users add validation | `prompts/04_validation_rule_synthesis.md` |
| Self-test endpoint | one-click demo seed | `api/v1/selftest.py` |
| Editable prompts at runtime | no redeploy to tune extraction | `PUT /api/v1/settings/prompts/{name}` |
| PDF/CSV/XLSX export | compliance reporting | `api/v1/export.py` |
| Anomaly detection (z-score) | data-quality surfaced automatically | `api/v1/analytics.py` |
