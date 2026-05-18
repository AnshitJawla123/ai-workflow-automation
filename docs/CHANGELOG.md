# Changelog

All notable changes to this project will be documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] – 2026-05-18

### Added — initial release
- FastAPI backend with 15 routers (auth, upload, documents, records, rules, search, dashboard, analytics, chat, export, ws, health, selftest, audit, settings, webhooks)
- SQLAlchemy models (User, Document, DocumentPage, ExtractedRecord, FieldValue, ValidationRule, ValidationIssue, AuditLog, JobRun, ApiKey)
- JWT auth (HS256) + bootstrap admin
- 10 versioned prompt templates (`backend/app/prompts/`)
- OpenRouter LLM client with model rotation, 429-aware retries, SQLite KV cache
- HuggingFace Inference adapter (legacy + new router endpoints)
- Tesseract local OCR fallback
- Multi-strategy extractor (vision LLM → OCR+text LLM → OCR+regex → demo mock)
- 8-stage pipeline (preprocess, detect, extract, confidence, persist, validate, index, complete)
- In-process asyncio job runner with SQLite-backed requeue on restart
- WebSocket bus for live document/job updates
- PageIndex vectorless RAG (hierarchical JSON tree)
- ChromaDB embedded vector store + MiniLM embeddings
- NetworkX GraphRAG with persisted JSON
- 13 default validation rules (required, regex, enum, range, unique, expression)
- NL → rule synthesis via LLM
- Z-score anomaly detection
- NL → safe SELECT-only SQL chat
- Per-document PDF report generator (ReportLab)
- CSV / JSON / XLSX exports
- Outbound webhooks API
- Audit log with field-level diffs
- Settings + prompt management API
- Single-page React SPA (CDN React + Tailwind + Recharts + Babel-standalone), zero node build
- Single-container Dockerfile + docker-compose + render.yaml + fly.toml
- Comprehensive documentation: README, ARCHITECTURE, AGENTS, AI_WORKFLOW, PROMPTS, API, DEPLOYMENT, ASSUMPTIONS, SECURITY, DEMO, AI_TOOLS_AND_FRAMEWORKS, LIVE_TEST_REPORT, CHANGELOG, CONTRIBUTING, RUNBOOK

### Fixed
- Reprocess endpoint now clears prior DocumentPage rows for idempotency
- bcrypt 4.x compatibility (pinned to 4.0.1) for passlib
- Bootstrap admin email needs `@local.dev` rather than `@local` for email-validator

### Known limitations
- Free OpenRouter vision models heavily rate-limited upstream (HTTP 429) — mitigated by 4-strategy fallback chain
- HF Inference router endpoint partially broken for some classic models — Tesseract local fallback covers it
