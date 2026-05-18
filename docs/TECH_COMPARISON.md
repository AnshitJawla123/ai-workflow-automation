# Tech-Stack Comparison: Why we didn't use LangChain / LlamaIndex

LangChain and LlamaIndex are popular but introduce overhead, hidden retries,
and abstraction layers that are hard to debug on a 48-hour project. Our stack
is **leaner, faster, and exposes every prompt + every retry** for inspection.

| Concern | Our approach | LangChain | LlamaIndex |
|---|---|---|---|
| LLM calls | direct `httpx` to provider; ~120 LOC | wrapper objects, hard to trace | wrapper objects |
| Multi-provider | explicit registry (5 providers) | requires per-provider modules | similar |
| Prompts | `app/prompts/*.md` (10 files, hot-reload) | strings in Python code | YAML config |
| Vector RAG | Chroma direct (~80 LOC) | requires `langchain-chroma` adapter | works natively |
| Vectorless RAG | **PageIndex** (custom, ~150 LOC) | not built-in | **PageIndex** ✅ |
| GraphRAG | NetworkX in-process | `langchain-experimental` (heavy) | **PropertyGraphIndex** ✅ |
| NL → SQL | own AST-based guard (~60 LOC) | `SQLDatabaseChain` (less safe) | `NLSQLTableQueryEngine` |
| OCR fallback chain | 3-tier (Paddle→HF→Tesseract) | not in scope | not in scope |
| Bundle size | **35 MB** | 200+ MB with deps | 150+ MB |
| Cold start | <2 s | 10-15 s | 8-12 s |
| Debuggability | every prompt visible; cache by SHA | high abstraction | high abstraction |

## Where LangChain / LlamaIndex *would* help (and what we did instead)

| Capability | LangChain offers | We provide |
|---|---|---|
| Tool-calling agent | `AgentExecutor` | NL→SQL with safe guard + future-ready hook in `chat.py` |
| Memory | `ConversationBufferMemory` | session-scoped messages table |
| Vector search | community wrappers | direct Chroma (faster, less indirection) |
| Tracing | `LangSmith` (paid) | structured JSON logs + audit table |

## Our advanced AI techniques *beyond* both libraries' defaults

1. **PageIndex (vectorless RAG)** — semantic outline traversal w/o embeddings
2. **GraphRAG** — entities (machines, employees, work orders) become nodes; LLM extracts triples
3. **LLM-as-Judge confidence** — second-pass evaluator on each extraction
4. **Multi-strategy extraction** — vision LLM → OCR+text LLM → heuristic → demo
5. **Multi-provider registry with auto-fallback** — 5 LLM providers, transparent priority
6. **NL → validation rule synthesis** — users add new rules in plain English
7. **Anomaly detection** — z-score outliers on numeric fields per machine
8. **WebSocket live status** — per-document progress streamed to UI
9. **Confidence fusion** — token-level + LLM-judge + field-regex blended into per-field score

LangChain ships none of #1-#7 out of the box. LlamaIndex has #1-#3 partially.

## Bottom line

Our **production-leaning, low-magic** stack is intentionally chosen for:
- single-server deployment (no Redis, Kafka, queue infra)
- explicit prompts (every LLM call inspectable in `/api/v1/settings/prompts`)
- replaceable providers (one env-var swap)
- minimal cold-start for the demo evaluator's first impression
