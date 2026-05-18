# AGENTS.md

## 🚀 **LIVE DEPLOYMENT: [http://44.207.148.185/](http://44.207.148.185/)** 🚀

A complete record of AI assistance used in the development of this project — as required by the assignment brief.

> A more detailed breakdown lives in [`docs/AI_WORKFLOW.md`](docs/AI_WORKFLOW.md) and [`docs/AI_TOOLS_AND_FRAMEWORKS.md`](docs/AI_TOOLS_AND_FRAMEWORKS.md).

## Primary agent
**Anthropic-backbone coding assistant** — interactive AI-driven development.

## What it did
- Multi-revision **planning** (3 plan iterations refined by user feedback on tech, infra constraints, sizing)
- Wrote **every file** in `backend/`, `frontend SPA`, `docs/`, and deployment configs
- Authored **10 versioned LLM prompts** with explicit JSON contracts and few-shot from real Image1 data
- Implemented **multi-strategy extraction** (vision LLM → OCR+text LLM → OCR regex → demo mock)
- Built **3-layer RAG** (PageIndex vectorless + Chroma vector + NetworkX graph)
- Ran live shell tests, observed real OpenRouter free-tier behaviour, and added 429-aware retries
- Wrote Dockerfile, docker-compose, render.yaml, fly.toml
- Authored 14 docs in `docs/` plus README

## Where the human supplied judgment
- Infrastructure constraint: "single server, no Redis/pubsub" → adopted in-process asyncio queue with SQLite-backed persistence
- AI provider choice: free OpenRouter + HF
- Tech stack: chose FastAPI + React-CDN over the referenced IDP's Java/Spring for shipping speed
- API keys (kept in `.env`, never committed)
- Verification of live extraction output against the actual sample image

## Verified end-to-end (see `docs/LIVE_TEST_REPORT.md`)
- Real Vision LLM (gemma-4-31b-it:free) returned **100%-correct** Image1 row 1 fields
- Full pipeline, search, dashboard, exports, review, audit, WebSocket, rules — all green
