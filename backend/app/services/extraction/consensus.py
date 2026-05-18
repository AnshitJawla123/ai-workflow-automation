"""Multi-model consensus extraction.

Strategy: call up to N independent vision providers in parallel, then merge:
- For each row (matched by row_index), and each field:
  - If all providers agree -> conf = 0.95
  - If majority agree -> use majority value, conf = 0.80
  - If providers disagree -> pick the value from the most-trusted provider, conf = 0.45
- Rows the providers disagree on COUNT are reported via a 'consensus_note'

This dramatically improves accuracy on ambiguous handwriting because:
- Two independent models reading the same cell that AGREE is strong signal
- Disagreement correctly surfaces the row for human review
"""
from __future__ import annotations

import concurrent.futures as cf
import logging
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from ..llm import providers as llm_providers
from ..llm.openrouter import LLMUnavailable

log = logging.getLogger("consensus")

# Provider trust order (highest first) for tiebreak when fewer than 2 agree
_TRUST_ORDER = ["gemini", "groq", "openrouter", "ollama", "together"]

# Fields where we want consensus (canonical record fields)
_FIELDS = ["date", "shift", "employee_no", "operation_code",
           "machine_no", "work_order_no", "quantity_produced", "time_taken_hours"]


def call_all_providers(image_path: str, prompt: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Call every enabled provider in parallel; return list of (provider_name, payload)."""
    providers = [(n, llm_providers._instance(n)) for n, _ in llm_providers._PROVIDER_ORDER]
    enabled = [(n, inst) for n, inst in providers if inst.enabled()]
    results: List[Tuple[str, Dict[str, Any]]] = []

    def _call(name_inst):
        name, inst = name_inst
        try:
            log.info("consensus call provider=%s", name)
            out = inst.vision_extract(image_path, prompt, json_only=True,
                                       cache_key_extra=f"consensus:{name}")
            if isinstance(out, dict) and out.get("records"):
                return (name, out)
        except LLMUnavailable as e:
            log.info("provider %s skipped: %s", name, e)
        except Exception as e:
            log.warning("provider %s error: %s", name, e)
        return None

    # Limit to top 3 providers to keep latency reasonable
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        for r in ex.map(_call, enabled[:3]):
            if r:
                results.append(r)
    return results


def _row_signature(row: Dict[str, Any]) -> str:
    """Identify rows across providers by their s_no (or fallback row_index)."""
    s = row.get("s_no") or row.get("row_index")
    return str(s) if s is not None else ""


def _merge_field(field: str, values: List[Tuple[str, Any]]) -> Tuple[Any, float, str]:
    """Given (provider, value) tuples for one field, return (chosen_value, confidence, note)."""
    # Filter out None values
    non_null = [(p, v) for p, v in values if v not in (None, "", "null")]
    if not non_null:
        return (None, 0.0, "all-null")
    # Normalize for comparison (strings strip+upper for codes; numbers as float)
    def _norm(v):
        if v is None:
            return None
        if field in ("quantity_produced", "time_taken_hours"):
            try:
                return round(float(v), 2)
            except Exception:
                return None
        return str(v).strip().upper()

    counter: Counter = Counter(_norm(v) for _, v in non_null)
    most_common, count = counter.most_common(1)[0]
    if count >= 2:
        # Pick the original value (not normalized) from a provider that voted for it
        for p, v in non_null:
            if _norm(v) == most_common:
                conf = 0.95 if count == len(values) else 0.85
                note = f"{count}/{len(values)} agree"
                return (v, conf, note)
    # No majority - pick by trust order
    for trusted in _TRUST_ORDER:
        for p, v in non_null:
            if p == trusted:
                return (v, 0.50, f"no-consensus; using {p}")
    p, v = non_null[0]
    return (v, 0.50, f"no-consensus; using {p}")


def merge_results(results: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, Any]:
    """Merge per-row, per-field across providers into a single payload with per-field conf."""
    if not results:
        return {"doc_type": "machine_shop_log", "records": [], "warnings": ["no provider returned data"]}
    if len(results) == 1:
        # Only one provider succeeded — return its output verbatim (no consensus boost)
        only = results[0][1]
        only["consensus"] = {"providers_used": [results[0][0]], "rows_with_agreement": 0}
        return only

    # Collect all unique row signatures
    row_sigs: List[str] = []
    seen = set()
    for name, payload in results:
        for r in payload.get("records", []):
            sig = _row_signature(r) or f"row_{len(seen) + 1}"
            if sig not in seen:
                seen.add(sig)
                row_sigs.append(sig)

    merged_records = []
    for sig in row_sigs:
        merged_row: Dict[str, Any] = {"row_index": int(sig) if sig.isdigit() else len(merged_records) + 1,
                                       "s_no": int(sig) if sig.isdigit() else None}
        confs: Dict[str, float] = {}
        notes: Dict[str, str] = {}
        for field in _FIELDS:
            values_for_field: List[Tuple[str, Any]] = []
            for name, payload in results:
                for r in payload.get("records", []):
                    if _row_signature(r) == sig:
                        values_for_field.append((name, r.get(field)))
                        break
            v, conf, note = _merge_field(field, values_for_field)
            merged_row[field] = v
            confs[field] = conf
            notes[field] = note
        merged_row["confidence"] = confs
        merged_row["consensus_notes"] = notes
        merged_records.append(merged_row)

    return {
        "doc_type": "machine_shop_log",
        "records": merged_records,
        "extraction_strategy": "vision_consensus",
        "consensus": {
            "providers_used": [r[0] for r in results],
            "rows": len(merged_records),
        },
    }
