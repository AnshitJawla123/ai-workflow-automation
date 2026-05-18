# Contributing

Thank you for considering a contribution! This project favours **execution speed + practical usability** over heavy ceremony.

## Local development
```bash
git clone <repo>
cd ai-workflow-automation
cp .env.example .env       # fill OPENROUTER_API_KEY
./scripts/install.sh
./scripts/run.sh
```

## Code style
- Python 3.11+, type hints encouraged.
- Black-compatible formatting (no enforced formatter — keep diffs small).
- One concern per module; new services go under `backend/app/services/<area>/`.

## Adding a new pipeline stage
1. Create `backend/app/workflows/stages/<my_stage>.py` exporting an async function.
2. Wire it into `pipeline.py::process_document` between the relevant existing stages.
3. Use `record_job(db, doc.id, "<stage>", "success|failed", ...)` for observability + WebSocket emit.

## Adding a new validation rule type
1. Extend `services/validation/engine.py::validate_record` with the new `rule_type` branch.
2. Update `prompts/04_validation_rule_synthesis.md` so the LLM can synthesize it from NL.
3. Add a default rule to `db/bootstrap.py::DEFAULT_RULES` if generally useful.

## Adding a new prompt
1. Drop `backend/app/prompts/NN_my_prompt.md`.
2. Call `render("NN_my_prompt", **vars)` from your service.
3. Update `docs/PROMPTS.md`.

## Tests
```bash
cd backend && .venv/bin/pytest -q
```

## Pull-request checklist
- [ ] All new endpoints registered in `backend/app/main.py`
- [ ] DTOs in `schemas/`, not inline in routers
- [ ] Migrations added if schema changed (`alembic revision -m "..."`)
- [ ] README / API docs updated if public surface changed
- [ ] One feature per PR; small diffs preferred
