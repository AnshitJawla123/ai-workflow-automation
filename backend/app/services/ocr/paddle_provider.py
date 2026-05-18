"""PaddleOCR — open-source, free, runs offline. Much better than Tesseract for handwriting.
Import is lazy because the package is large (~500MB w/ models on first use).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

log = logging.getLogger("ocr.paddle")

_paddle = None
_init_err = None


def _get():
    global _paddle, _init_err
    if _paddle is not None or _init_err is not None:
        return _paddle
    try:
        from paddleocr import PaddleOCR  # type: ignore
        _paddle = PaddleOCR(use_textline_orientation=True, lang="en", show_log=False)
        log.info("PaddleOCR initialised")
    except Exception as e:
        _init_err = e
        log.warning("PaddleOCR unavailable: %s", e)
        _paddle = None
    return _paddle


def ocr_image(path: str | Path) -> Dict:
    p = _get()
    if p is None:
        return {"text": "", "confidence": 0.0, "provider": "paddle", "error": str(_init_err)}
    try:
        result = p.ocr(str(path), cls=True)
        # result is list of pages, each is list of [bbox, (text, conf)]
        lines = []
        confs = []
        for page in result or []:
            for entry in page or []:
                try:
                    txt, c = entry[1]
                    lines.append(txt)
                    confs.append(float(c))
                except Exception:
                    continue
        text = "\n".join(lines)
        avg = sum(confs) / len(confs) if confs else 0.0
        return {"text": text, "confidence": avg, "provider": "paddle"}
    except Exception as e:
        log.warning("PaddleOCR failed: %s", e)
        return {"text": "", "confidence": 0.0, "provider": "paddle", "error": str(e)}
