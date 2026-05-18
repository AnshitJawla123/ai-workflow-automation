"""HuggingFace Inference API for TrOCR handwritten OCR (free tier)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

import httpx

from ...core.config import settings

log = logging.getLogger("ocr.hf")


def ocr_image(path: str | Path, model: str | None = None) -> Dict:
    if not settings.hf_api_token:
        return {"text": "", "confidence": 0.0, "provider": "hf", "error": "HF_API_TOKEN not set"}
    model = model or settings.hf_ocr_model
    url = f"{settings.hf_base_url}/{model}"
    headers = {"Authorization": f"Bearer {settings.hf_api_token}"}
    data = Path(path).read_bytes()
    try:
        r = httpx.post(url, headers=headers, content=data, timeout=60)
        if r.status_code != 200:
            return {"text": "", "confidence": 0.0, "provider": "hf",
                    "error": f"{r.status_code}: {r.text[:200]}"}
        j = r.json()
        if isinstance(j, list) and j and isinstance(j[0], dict):
            text = j[0].get("generated_text") or j[0].get("text") or ""
        else:
            text = str(j)
        return {"text": text, "confidence": 0.7, "provider": "hf"}
    except Exception as e:
        log.warning("HF OCR failed: %s", e)
        return {"text": "", "confidence": 0.0, "provider": "hf", "error": str(e)}
