"""Pluggable validation engine.

Supports rule_types: required, regex, enum, range, unique/duplicate, expression.
Expressions are evaluated in a tiny sandbox with only record fields + safe builtins.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from ...models import ExtractedRecord, ValidationIssue, ValidationRule

SAFE_BUILTINS = {
    "abs": abs, "min": min, "max": max, "round": round,
    "len": len, "int": int, "float": float, "str": str, "bool": bool,
}


def _eval_expr(expr: str, ctx: Dict[str, Any]) -> bool:
    try:
        return bool(eval(expr, {"__builtins__": SAFE_BUILTINS}, ctx))  # noqa: S307 — sandboxed
    except Exception:
        return False


def _get(rec: ExtractedRecord, field: Optional[str]) -> Any:
    if not field:
        return None
    return getattr(rec, field, None)


def _record_ctx(rec: ExtractedRecord) -> Dict[str, Any]:
    return {c.name: getattr(rec, c.name) for c in rec.__table__.columns}


def validate_record(
    db: Session,
    record: ExtractedRecord,
    rules: Iterable[ValidationRule],
    siblings: Optional[List[ExtractedRecord]] = None,
) -> List[Tuple[ValidationRule, str]]:
    """Return list of (rule, message) failures."""
    failures: List[Tuple[ValidationRule, str]] = []
    siblings = siblings or []
    for rule in rules:
        if not rule.enabled:
            continue
        val = _get(record, rule.field)
        params = rule.params or {}
        msg = None
        if rule.rule_type == "required":
            if val is None or val == "":
                msg = f"{rule.field} is required"
        elif rule.rule_type == "regex":
            if val and not re.match(params.get("pattern", ""), str(val)):
                msg = f"{rule.field}='{val}' does not match {params.get('pattern')}"
        elif rule.rule_type == "enum":
            allowed = params.get("values", [])
            if val and val not in allowed:
                msg = f"{rule.field}='{val}' not in {allowed}"
        elif rule.rule_type == "range":
            try:
                if val is not None and val != "":
                    v = float(val)
                    if v < params.get("min", float("-inf")) or v > params.get("max", float("inf")):
                        msg = f"{rule.field}={v} out of range [{params.get('min')}, {params.get('max')}]"
            except (TypeError, ValueError):
                msg = f"{rule.field}='{val}' is not numeric"
        elif rule.rule_type in ("unique", "duplicate"):
            if val:
                dupes = [s for s in siblings if s.id != record.id and getattr(s, rule.field, None) == val]
                if dupes:
                    msg = f"Duplicate {rule.field}='{val}' (also in row(s) {[d.row_index for d in dupes]})"
        elif rule.rule_type == "expression":
            ok = _eval_expr(params.get("expression", "True"), _record_ctx(record))
            if not ok:
                msg = f"Expression failed: {params.get('expression')}"
        if msg:
            failures.append((rule, msg))
    return failures


def persist_issues(
    db: Session,
    record: ExtractedRecord,
    failures: List[Tuple[ValidationRule, str]],
) -> List[ValidationIssue]:
    issues = []
    for rule, msg in failures:
        issue = ValidationIssue(
            document_id=record.document_id,
            record_id=record.id,
            rule_code=rule.code,
            field=rule.field,
            severity=rule.severity,
            message=msg,
        )
        db.add(issue)
        issues.append(issue)
    if failures and any(r.severity == "error" for r, _ in failures):
        record.review_status = "needs_review"
    db.commit()
    return issues
