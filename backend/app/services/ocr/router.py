"""OCR provider router with auto-fallback chain.
Order:  PaddleOCR (best handwriting) → HF TrOCR → Tesseract.
Vision LLM is used by the extraction stage directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from ...core.config import settings
from . import hf_provider, tesseract_provider, paddle_provider


def ocr_image(path: str | Path) -> Dict:
    provider = settings.ocr_provider.lower()
    if provider in ("auto", "paddle"):
        r = paddle_provider.ocr_image(path)
        if r.get("text"):
            return r
    if provider in ("auto", "hf"):
        r = hf_provider.ocr_image(path)
        if r.get("text"):
            return r
    if provider in ("auto", "tesseract"):
        return tesseract_provider.ocr_image(path)
    return {"text": "", "confidence": 0.0, "provider": provider, "error": "no provider"}
