"""Multi-strategy structured extraction (production — no mocks):

Strategies tried in order until one returns records:
  1. **Vision LLM multi-provider consensus** — call top-N enabled vision providers
     (Gemini, Groq Llama-4 Scout, OpenRouter free models) in parallel and merge
     with per-field voting. 2+ agree → high confidence; disagreement → needs_review.
  2. **Single-provider vision** — registry fallback if only one provider is configured.
  3. **Tesseract OCR → text LLM structuring** — when vision is rate-limited.
  4. **Regex heuristic on OCR text** — last-resort deterministic fallback.

If ALL strategies fail we return an empty record set (truthful — never fake data).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...prompts import render
from ..llm.openrouter import openrouter, LLMUnavailable
from ..llm import providers as llm_providers
from ..ocr.router import ocr_image
from ..ocr.tesseract_provider import ocr_image as tesseract_ocr
from ...utils.json_extract import extract_json
from . import consensus as consensus_mod
from ...core.config import settings as _settings

log = logging.getLogger("extraction")


def _preprocess_image_for_vision(image_path: Path) -> Path:
    """Light preprocessing — upscale small images only.
    Heavy preprocessing (CLAHE + sharpen + grayscale) was tested and HURT vision-LLM
    accuracy (model lost color/anti-aliasing cues). So we keep this minimal.
    """
    try:
        import cv2
        img = cv2.imread(str(image_path))
        if img is None:
            return image_path
        h, w = img.shape[:2]
        # Upscale tiny images only — large images go as-is (best for vision model)
        if max(h, w) < 1200:
            scale = 1600 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
            out_path = image_path.with_suffix(".enh.png")
            cv2.imwrite(str(out_path), img)
            return out_path
        return image_path
    except Exception as e:
        log.warning("image preprocessing failed: %s — using original", e)
        return image_path


# ---------- Deterministic fallback (when no LLM key) ----------
def _heuristic_extract(raw_ocr: str) -> Dict[str, Any]:
    """Very small fallback: parses tabular tokens from OCR text.
    Used only when no LLM is configured so the app still works for demos.
    """
    records: List[Dict[str, Any]] = []
    if not raw_ocr.strip():
        return {"doc_type": "machine_shop_log", "records": records, "warnings": ["no OCR text"]}
    lines = [ln.strip() for ln in raw_ocr.splitlines() if ln.strip()]
    pat_machine = re.compile(r"MC[-\s]?\d{2,4}", re.I)
    pat_emp = re.compile(r"BT\s?\d{3,5}", re.I)
    row_i = 0
    for ln in lines:
        if not (pat_machine.search(ln) or pat_emp.search(ln)):
            continue
        row_i += 1
        tokens = ln.split()
        rec = {
            "row_index": row_i,
            "date": next((t for t in tokens if re.match(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", t)), None),
            "shift": next((t for t in tokens if t.upper() in {"I", "II", "III"}), None),
            "employee_no": (pat_emp.search(ln).group(0) if pat_emp.search(ln) else None),
            "machine_no": (pat_machine.search(ln).group(0).upper().replace(" ", "-") if pat_machine.search(ln) else None),
            "operation_code": None,
            "work_order_no": None,
            "quantity_produced": None,
            "time_taken_hours": None,
            "confidence": {k: 0.4 for k in ["date","shift","employee_no","machine_no","operation_code","work_order_no","quantity_produced","time_taken_hours"]},
        }
        records.append(rec)
    return {"doc_type": "machine_shop_log", "records": records, "warnings": ["heuristic fallback"]}


def extract_from_image(image_path: str | Path, page_number: int = 1, title: str = "") -> Dict[str, Any]:
    """Try multiple strategies in order of accuracy."""
    title = title or "Machine shop data"

    # Strategy 1: Multi-provider CONSENSUS vision extraction
    # Calls top-N enabled providers in parallel and merges results.
    # 2+ providers agree -> high confidence; disagreement -> needs_review.
    enhanced_path = _preprocess_image_for_vision(Path(image_path))
    try:
        prompt = render("02_field_extraction", title=title, page_number=page_number)
        all_results = consensus_mod.call_all_providers(str(enhanced_path), prompt)
        if all_results:
            result = consensus_mod.merge_results(all_results)
            if result.get("records"):
                result.setdefault("doc_type", "machine_shop_log")
                result.setdefault("extraction_strategy", "vision_consensus" if len(all_results) > 1 else "vision_llm")
                log.info("strategy=%s providers=%s produced %d records",
                         result["extraction_strategy"],
                         [r[0] for r in all_results],
                         len(result["records"]))
                return result
    except Exception as e:
        log.warning("consensus vision extraction failed: %s — falling back", e)

    # Strategy 1b: single-provider vision (registry fallback for backwards compat)
    try:
        prompt = render("02_field_extraction", title=title, page_number=page_number)
        result = llm_providers.call_vision(str(enhanced_path), prompt=prompt, json_only=True,
                                            cache_key_extra=f"enh:{page_number}")
        if isinstance(result, dict) and result.get("records"):
            result.setdefault("doc_type", "machine_shop_log")
            result.setdefault("extraction_strategy", "vision_llm")
            for r in result["records"]:
                if "field_confidence" in r and "confidence" not in r:
                    r["confidence"] = r.pop("field_confidence")
            log.info("strategy=vision_llm produced %d records", len(result["records"]))
            return result
    except LLMUnavailable as e:
        log.info("vision LLM unavailable across all providers: %s", e)
    except Exception as e:
        log.warning("vision LLM error: %s", e)

    # Strategy 2: Tesseract OCR → text LLM structuring
    raw_text = tesseract_ocr(image_path).get("text", "") or ""
    if raw_text.strip():
        try:
            result = _structure_with_text_llm(raw_text, title=title, page_number=page_number)
            if result and result.get("records"):
                result["extraction_strategy"] = "ocr+text_llm"
                log.info("strategy=ocr+text_llm produced %d records", len(result["records"]))
                return result
        except Exception as e:
            log.warning("text LLM structuring failed: %s", e)

    # Strategy 3: pure regex heuristic
    payload = _heuristic_extract(raw_text)
    if payload.get("records"):
        payload["extraction_strategy"] = "ocr+heuristic"
        log.info("strategy=ocr+heuristic produced %d records", len(payload["records"]))
        return payload

    # All strategies failed — return empty (truthful) result
    log.warning("All extraction strategies failed — returning empty records (truthful)")
    return {
        "doc_type": "machine_shop_log",
        "title": title,
        "records": [],
        "extraction_strategy": "failed",
        "warnings": ["Vision LLM returned no records and OCR fallback yielded nothing parseable."],
    }


def _structure_with_text_llm(raw_text: str, title: str, page_number: int) -> Optional[Dict[str, Any]]:
    """Send raw OCR text to a free text LLM to structure into our JSON schema."""
    prompt = f"""You are extracting structured machine-shop production records from MESSY HANDWRITTEN OCR TEXT.
The OCR is imperfect — letters/digits may be confused (O↔0, I↔1, l↔1, S↔5, B↔8, Z↔2). Use context.

Expected columns: S.No, Date, Shift (I/II/III), Emp. No (like BT4710), Opn Code (6 digits like 856430),
Machine No. (like MC-730), Work Order No. (digits), Qty. Prod. (number), Time taken in hrs (decimal).

Output strict JSON only:
{{
  "doc_type": "machine_shop_log",
  "title": "{title}",
  "page_number": {page_number},
  "records": [
    {{"row_index": 1, "date":"YYYY-MM-DD or raw", "shift":"I|II|III", "employee_no":"BT####",
      "operation_code":"######", "machine_no":"MC-###", "work_order_no":"######",
      "quantity_produced": number, "time_taken_hours": number,
      "confidence": {{"date":0.0..1, "shift":0.0..1, "employee_no":0.0..1,
                      "operation_code":0.0..1, "machine_no":0.0..1, "work_order_no":0.0..1,
                      "quantity_produced":0.0..1, "time_taken_hours":0.0..1}}}}
  ]
}}

Rules:
- Skip empty rows (only emit rows with at least one handwritten value).
- Per-field confidence reflects OCR reliability (be honest; 0.4 for ambiguous strokes).
- If a field is illegible, set value=null, confidence=0.0.
- Use lower confidence (~0.5-0.7) since this is OCR-derived, not direct vision.
- JSON only. No prose.

OCR TEXT:
```
{raw_text}
```
"""
    try:
        out = llm_providers.call_text(prompt, json_only=True)
    except LLMUnavailable as e:
        log.info("text LLM unavailable: %s", e)
        return None
    if not isinstance(out, dict) or "records" not in out:
        return None
    out.setdefault("doc_type", "machine_shop_log")
    return out


def detect_table(image_path: str | Path) -> Dict[str, Any]:
    prompt = render("01_table_detection")
    try:
        return llm_providers.call_vision(str(image_path), prompt=prompt, json_only=True,
                                         cache_key_extra="table_detect")
    except Exception as e:
        log.info("table_detect fallback: %s", e)
        return {"has_table": True, "title": "Machine shop data", "columns": []}
