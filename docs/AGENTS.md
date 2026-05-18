# AGENTS.md — AI tools used during development

## 🚀 **LIVE DEPLOYMENT: [http://44.207.148.185/](http://44.207.148.185/)** 🚀

## Primary AI agent
- **Anthropic-family interactive AI** in interactive mode

## What the AI did
| Task | Role |
|---|---|
| Project planning & architecture | drafted multi-revision plan with size/perf sizing |
| File scaffolding | created the entire folder tree, env, Makefile, scripts |
| FastAPI app | wrote every router, model, schema, service |
| Pipeline orchestration | asyncio job runner, WebSocket bus, stage pattern |
| Prompts | authored 10 versioned, few-shot prompt files (see `docs/PROMPTS.md`) |
| RAG implementation | wrote PageIndex (vectorless), Chroma vector, NetworkX GraphRAG |
| Validation engine | rule interpreter + LLM-powered NL→rule synthesis |
| Frontend | single-page React app (CDN React + Tailwind + Recharts) |
| Docker + deploy specs | Dockerfile, compose, render.yaml, fly.toml |
| Docs | this file + README + ARCHITECTURE + DEPLOYMENT + PROMPTS |
| Smoke test | live e2e run on localhost validated all major flows |

## Where human judgment was applied
- Chose **FastAPI + SQLite + React-CDN** over the (referenced) IDP's Spring stack for shipping speed.
- Decided on **zero-infra** as a constraint (no Redis/Kafka/Postgres) per user requirement of "we only have a server".
- Demo-mode mock when no LLM key is configured, so reviewers can experience the UI without keys.

## What the AI could not do alone
- Provide real LLM/OCR API keys (the user supplies these via `.env`).
- Verify visual quality of the React UI in motion — relied on contract tests + assumption that Tailwind + shadcn-style primitives are aesthetic.
- Test under sustained production load.
