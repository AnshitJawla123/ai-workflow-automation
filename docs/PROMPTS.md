# Prompts catalog

All prompts live under `backend/app/prompts/`. They are loaded at runtime via `backend/app/prompts/__init__.py::render()`.

| # | File | Purpose | Model class |
|---|---|---|---|
| 01 | `01_table_detection.md` | Detect tabular log region + column headers + row counts | vision |
| 02 | `02_field_extraction.md` | **Main** structured extraction with per-field confidence | vision |
| 03 | `03_confidence_judge.md` | Independent LLM-as-judge for trustworthiness | text |
| 04 | `04_validation_rule_synthesis.md` | NL → executable rule JSON | text |
| 05 | `05_anomaly_detection.md` | Pattern flags across recent records | text |
| 06 | `06_graph_triple_extraction.md` | Record → knowledge-graph triples | text |
| 07 | `07_search_query_expansion.md` | Expand short query into terms + filters | text |
| 08 | `08_nl_to_sql.md` | Natural language → SELECT-only SQL | text |
| 09 | `09_dashboard_insight.md` | Aggregate metrics → 3-bullet exec summary | text |
| 10 | `10_correction_suggestion.md` | Suggest fix for low-confidence field | text |

## Conventions
- Every prompt has a strict JSON output contract (no markdown, no prose).
- Few-shot examples use real Image1 values (`BT4710`, `MC-730`, `165460`, `25 units`, `4.0 hrs`).
- `{{placeholders}}` are substituted by `render(name, **kwargs)`.
- Editable at runtime via `PUT /api/v1/settings/prompts/{name}` (admin role).
- Cached LLM responses are keyed by `sha1(prompt + image_hash)` — editing a prompt invalidates the cache for that prompt.

## Adding a new prompt
1. Drop a new file `backend/app/prompts/11_my_new_prompt.md`.
2. Call `render("11_my_new_prompt", foo=bar)` in code.
3. Update this catalog.

## Versioning
Prompts are versioned implicitly via git history of the `.md` files. For breaking changes, copy to `_v2.md` and update callers, so old cached responses remain valid for old prompts.
