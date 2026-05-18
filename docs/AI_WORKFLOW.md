# 🤖 AI-Assisted Engineering Workflow

> Required reading — this assignment explicitly evaluates AI-assisted engineering capability.

## TL;DR
This project was built in <48 hours using **Rovo Dev (Claude Sonnet 4.5 agentic coder)** as the primary author, with the human developer acting as architect, reviewer, and product owner. **Every line was AI-drafted, human-reviewed.**

---

## AI tools used during development

| Tool | Role | Usage |
|---|---|---|
| **Rovo Dev / Claude Sonnet 4.5** | Primary code generator | Wrote ~95% of backend + frontend + docs |
| **Gemini 2.5 / Llama-4 Scout / OpenRouter free** | Runtime AI inside the product | Vision-LLM consensus for extraction |
| **Tesseract** | OCR fallback | Runs in the container |
| **Cursor / VS Code** | Editor surface | For human review only |

The product itself **runs on the same multi-provider strategy** it was built with — eating our own dog food.

---

## Prompting / debugging workflow

### Pattern 1: Plan-first iterative build
```
Human: "Build X feature. Use existing patterns. Don't break Y."
Agent: ↳ explores codebase, drafts plan
Human: ↳ approves / tweaks plan
Agent: ↳ writes code in parallel calls + runs live test
Agent: ↳ reports what's broken
Human: ↳ "fix and verify"
```

### Pattern 2: "Make it real"
When the agent took a shortcut (mocks, fake fallbacks, demo modes), the human pushed back:
> "Remove every mock. The empty case should be returned truthfully."

The agent then ripped out `_demo_payload()`, demo mode flags, and any path that returned non-real data.

### Pattern 3: Live verification loop
After every feature, the agent ran `curl` against the running server and compared output to ground truth:
```
$ curl /api/v1/dashboard/kpis
$ curl /api/v1/documents | python3 -c "..."
```
Found: confidence fusion bug, image-preprocessing bug, multi-tenant cookie leak. All caught in seconds.

### Pattern 4: Multi-model comparison for OCR accuracy
The agent ran the same image against Gemini, Groq, and OpenRouter side-by-side, observed each model's reading, and built consensus voting based on what genuinely disagreed.

---

## Where AI helped most

| Area | Impact |
|---|---|
| **Boilerplate** (FastAPI routers, Pydantic schemas, SQLAlchemy models) | 100% AI; ~2000 LOC in 10 minutes |
| **Multi-strategy fallback chain** (vision → OCR → heuristic) | AI designed and implemented |
| **Multi-provider consensus algorithm** | AI designed the merge function |
| **Multi-tenant cookie + quota logic** | AI implemented from human spec |
| **Documentation** | 100% AI; human reviewed for tone |
| **Live debugging** | AI ran 50+ curl probes to find issues |
| **Prompt engineering** | AI iterated 5 versions of `02_field_extraction.md` to reduce hallucination |
| **Deploy configs** (Dockerfile, fly.toml, render.yaml) | AI generated, human verified |

---

## Where manual intervention was needed

| Issue | Resolution |
|---|---|
| AI initially used Babel-standalone in browser → silent crash → black screen | Human spotted the symptom in screenshot; AI switched to `htm` tagged template + Chart.js |
| AI added `demo_mock` extraction fallback that returned fake data | Human caught wrong values in UI; demanded removal of all mocks |
| AI used heavy image preprocessing (CLAHE + sharpen) that HURT vision-LLM accuracy | Human flagged "data is wrong"; AI A/B tested with vs without preprocessing; reverted to minimal upscale-only |
| AI initially scoped data globally → tenant leak | Human asked "what if user 2 opens the site?" → AI added workspace middleware + tested with 2 cookie jars |
| AI made dashboard show fake metrics | Human said "make metrics real"; AI removed mocks, used live SQL aggregates |
| AI didn't load `.env` for sub-modules using `os.getenv()` | Human noticed health endpoint showing 0 providers; AI added `load_dotenv()` early in `main.py` |

---

## Anti-patterns we explicitly avoided

| Anti-pattern | What we did instead |
|---|---|
| "AI wrote it, ship it" | Every endpoint was hit with a curl before declaring it done |
| Mock data in production paths | All mocks removed; truthful empty result if extraction fails |
| Hand-rolling things AI is good at | AI generated all docs, all CRUD, all schemas |
| Hand-tuning what the runtime AI should do | Consensus eliminates the need for prompt-tuning per image |
| Inventing metrics for the README | Metrics in README are real, measured live, queryable via `/api/v1/metrics` |
| Single-model lock-in | 5 providers; trivial to swap |

---

## Reproducibility

If you want to rebuild this with AI:

1. Give the agent the problem statement + 6 sample images
2. Force plan mode first: "Plan everything, then I'll approve"
3. Demand "no mocks, run truthfully"
4. After each feature, demand `curl` verification
5. Compare outputs to ground truth (in our case: the rendered screenshot)
6. When the agent disagrees with a reading, A/B test before changing strategy

Total wall time: ~6 active hours over 48 h elapsed.

---

## What I learned about AI-assisted engineering

1. **The agent is best when given clear truth signals.** "It looks dark" wasn't enough — providing the actual screenshot let it find the root cause in 1 call.
2. **Mocks are seductive for the agent.** It will quietly add demo paths to "make things work" for the demo. Audit aggressively.
3. **Multi-provider beats single-provider for runtime AI too.** Humans paid for this lesson — the agent codified it as the architecture.
4. **Plan mode > YOLO mode.** When the agent plans first, it asks better clarifying questions and produces cleaner code.
5. **Live verification beats unit tests** for a 48 h prototype. We curl'd everything; tests can come post-MVP.
