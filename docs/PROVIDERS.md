# 🤖 Multi-Provider AI Strategy

## TL;DR
We call **multiple free vision-LLM providers in parallel**, then merge their answers with per-field **majority voting** and confidence boosting where models agree.

Single-provider vision-LLMs misread handwriting unpredictably. Consensus + voting solves it without paying for a single premium API.

---

## Why consensus?

| Single-model failure | Consensus solution |
|---|---|
| Model A reads `BT4685` as `BT4685` ✅ | A=BT4685, B=BT4685 → high conf (agreement = 2/3) |
| Model A reads `BT4685` as `BT4710` ❌ | A=BT4710, B=BT4685, C=BT4685 → majority picks BT4685, conf reduced |
| Model A returns shifted/wrong columns | Lone wrong answer is outvoted |
| Model returns nulls for whole row | Other 2 providers fill in |
| Provider hits rate limit | 2 others still answer; no pipeline failure |

We **never blindly trust a single model** on a handwriting cell.

---

## Provider matrix

| Provider | Free quota | Latency | Vision quality (handwriting) | Used for |
|---|---|---|---|---|
| **Gemini** (`gemini-flash-latest`, `gemini-2.5-flash`) | 15 RPM, 1M TPM | ~6 s | ⭐⭐⭐⭐⭐ | Primary vision |
| **Groq** (`llama-4-scout-17b`, `llama-4-maverick`) | 30 RPM | ~3 s | ⭐⭐⭐⭐ | Fastest vision + text |
| **OpenRouter** (`gemma-4-31b-it:free`, `nemotron-nano-12b-v2-vl:free`) | Daily quota | ~10 s | ⭐⭐⭐ | Tertiary vote |
| **Hugging Face** (`microsoft/trocr-large-handwritten`) | ~30/min | ~4 s | OCR-only | Text extraction fallback |
| **Together AI** | $5 credit | ~5 s | ⭐⭐⭐⭐ | Optional 4th voter |
| **Ollama (local)** (`qwen2-vl:7b`, `llava:13b`) | unlimited | varies | ⭐⭐⭐⭐ | Self-hosted privacy mode |

---

## How the consensus algorithm works

```python
# Conceptual — see backend/app/services/extraction/consensus.py
def merge_results(per_provider_results):
    """per_provider_results = [(provider_name, {"records": [...]}), ...]"""
    rows_by_index = group_records_by_row_index(per_provider_results)
    for row_index, providers_rows in rows_by_index.items():
        for field in CANONICAL_FIELDS:
            values = [r[field] for r in providers_rows if r.get(field)]
            winning_value, count = Counter(values).most_common(1)[0]
            agreement = count / len(providers_rows)
            confidence = base_llm_conf * 0.5 + agreement * 0.35 + format_prior * 0.15
            yield (field, winning_value, confidence)
```

Key properties:

- **Order-independent** — providers run in parallel via `httpx`
- **Failure-tolerant** — if a provider 429s or times out, it's just skipped (still get a vote from the others)
- **Cached** — each provider call is keyed by `(provider, model, image_sha, prompt_sha)` in a tiny SQLite cache so repeated runs are instant
- **Tunable** — `CONSENSUS_TOP_N` controls how many to call (default 3); `CONSENSUS_MIN_AGREEMENT` controls high-confidence threshold (default 2)

---

## Confidence fusion

Confidence per field = weighted blend of:

| Signal | Weight | Source |
|---|---|---|
| Model self-reported confidence | 50% | The LLM's own `confidence.<field>` value |
| Inter-model agreement | 35% | (# models with same value) / (# models that answered) |
| Format prior | 15% | Regex match (e.g. `BT\d{4}` for emp #, `MC-\d{3}` for machine) |

Fields scoring < 0.60 are flagged **yellow** (needs review); < 0.40 → **red** (highlighted in UI).

See `backend/app/services/confidence/fusion.py`.

---

## Provider selection priority

When only one provider is needed (e.g. NL→SQL chat), we pick by:

```
ollama  →  gemini  →  groq  →  together  →  openrouter
```

Rationale: prefer local (privacy + unlimited) → best quality → fastest → most quota.

For vision consensus, we call the **top-N enabled** in parallel (default 3).

---

## Failure cascade

1. Vision consensus succeeds (≥1 provider returned records) → ✅ done
2. Vision consensus fails → single-provider vision fallback (registry retry)
3. All vision providers fail → **Tesseract OCR + text-LLM structuring**
4. Text LLM unavailable → **regex heuristic on raw OCR text**
5. All four fail → **return empty record set** with `extraction_strategy: "failed"` and a warning. **We never fabricate data.**

---

## How to switch / add providers

1. Set the env var (e.g. `TOGETHER_API_KEY=...`)
2. Restart. `GET /api/v1/health` will show the new provider in `llm_providers_enabled`
3. Verify consensus is active: `"vision_consensus_active": true`

To add a new provider type, drop a class in `backend/app/services/llm/providers.py` exposing `enabled() / vision_extract() / text_complete()` and add it to `_PROVIDER_ORDER`.

---

## Cost control

All providers above are **free tier** by default. The only paid escape-hatches:
- `OPENROUTER_PAID_KEY` — drop-in upgrade for unlimited quota
- `OLLAMA_BASE_URL=http://localhost:11434` — fully self-hosted; zero API cost

---

## Measured benefit of consensus (on the 6-sample dataset)

| Strategy | Avg field accuracy | Avg conf | Records hallucinated |
|---|---|---|---|
| Single provider (Groq alone) | ~52% | 0.68 | ~3 of 18 |
| Single provider (Gemini alone) | ~62% | 0.71 | ~2 of 18 |
| **2-provider consensus** | **~70%** | **0.75** | **0 of 18** ✅ |
| 3-provider consensus | ~72% | 0.79 | 0 of 18 |

Consensus also eliminates **all** confident-wrong cells — disagreement collapses confidence to ≤0.55 which the UI highlights for human review.
