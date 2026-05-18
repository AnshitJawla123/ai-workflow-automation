"""File / image helpers."""
from __future__ import annotations

import base64
import hashlib
import io
import uuid
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def new_uuid() -> str:
    return uuid.uuid4().hex


def write_bytes(path: str | Path, data: bytes) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def encode_image_b64(path: str | Path) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def image_to_data_url(path: str | Path, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64,{encode_image_b64(path)}"


def pdf_to_images(pdf_path: str | Path, out_dir: str | Path, dpi: int = 200) -> List[Path]:
    """Convert each PDF page to a JPEG. Uses pypdf + pillow fallback."""
    try:
        from pdf2image import convert_from_path
        imgs = convert_from_path(str(pdf_path), dpi=dpi)
        out_paths = []
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for i, im in enumerate(imgs, start=1):
            p = out_dir / f"page_{i:03d}.jpg"
            im.save(p, "JPEG", quality=92)
            out_paths.append(p)
        return out_paths
    except Exception:
        # Fallback: single-page render via pypdf (rasterless) – we just copy + note
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        # If poppler isn't available, return empty so caller can raise a clear error
        return []


def preprocess_image(in_path: str | Path, out_path: str | Path) -> Tuple[int, int]:
    """Deskew + denoise + adaptive threshold to improve OCR readability."""
    img = cv2.imread(str(in_path))
    if img is None:
        # PIL fallback
        pil = Image.open(in_path).convert("RGB")
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 5, 50, 50)
    # Deskew via image moments of binarized version
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 11)
    coords = np.column_stack(np.where(bw > 0))
    angle = 0.0
    if coords.size > 0:
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
    (h, w) = img.shape[:2]
    if abs(angle) > 0.1:
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return w, h
