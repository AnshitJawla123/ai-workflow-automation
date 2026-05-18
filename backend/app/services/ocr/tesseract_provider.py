"""Tesseract fallback — runs locally, fully offline."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

log = logging.getLogger("ocr.tesseract")


def ocr_image(path: str | Path) -> Dict:
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(path)
        txt = pytesseract.image_to_string(img)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        # Average confidence over tokens that have confidence
        confs = [int(c) for c in data.get("conf", []) if str(c).isdigit() and int(c) >= 0]
        avg = (sum(confs) / len(confs) / 100.0) if confs else 0.0
        return {"text": txt, "confidence": avg, "provider": "tesseract"}
    except Exception as e:
        log.warning("tesseract OCR failed: %s", e)
        return {"text": "", "confidence": 0.0, "provider": "tesseract", "error": str(e)}
