"""Per-field confidence fusion: LLM self-reported + OCR + format-validity prior."""
from __future__ import annotations

import re
from typing import Any, Dict

FIELD_PATTERNS = {
    "date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "shift": re.compile(r"^(I|II|III)$"),
    "employee_no": re.compile(r"^BT\s?\d{3,5}$", re.I),
    "machine_no": re.compile(r"^MC-\d{2,4}$", re.I),
    "work_order_no": re.compile(r"^\d{4,8}$"),
    "operation_code": re.compile(r"^\d{4,8}$"),
}

NUMERIC = {"quantity_produced", "time_taken_hours"}


def _format_prior(field: str, value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if field in NUMERIC:
        try:
            v = float(value)
            return 0.9 if 0 <= v <= 10000 else 0.5
        except Exception:
            return 0.2
    pat = FIELD_PATTERNS.get(field)
    if pat:
        return 0.95 if pat.match(str(value)) else 0.45
    return 0.7


def fuse(field: str, value: Any, llm_conf: float, ocr_conf: float = 0.0) -> float:
    """Weighted fusion.
    - If LLM didn't report explicit per-field confidence (most modern models don't),
      use a baseline of 0.75 when the value was returned (model decided it was readable).
    - Format-prior dominates: if value matches expected regex (BT####, MC-###, etc.),
      we trust the format.
    """
    prior = _format_prior(field, value)
    # If model returned the value but no explicit confidence, assume moderate-high trust.
    effective_llm = llm_conf if llm_conf and llm_conf > 0 else (0.75 if value not in (None, "") else 0.0)
    # Weighting: 0.35 llm-confidence + 0.10 ocr + 0.55 format prior
    score = 0.35 * effective_llm + 0.10 * (ocr_conf or 0.0) + 0.55 * prior
    return max(0.0, min(1.0, score))


def overall(fields: Dict[str, float]) -> float:
    if not fields:
        return 0.0
    return sum(fields.values()) / len(fields)
