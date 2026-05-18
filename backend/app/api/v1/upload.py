from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ...core.config import settings
from ...core.workspace import current_owner
from ...db.session import get_db
from ...models import Document
from ...schemas.documents import DocumentOut
from ...services.jobs.runner import runner
from ...utils.files import new_uuid, sha256_bytes, write_bytes
from ..deps import optional_user

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp", "image/jpg", "application/pdf"}
MAX_BYTES = 25 * 1024 * 1024

# Per-workspace storage limits (anti-abuse for public demo)
MAX_DOCS_PER_WORKSPACE = 50
MAX_BYTES_PER_WORKSPACE = 50 * 1024 * 1024  # 50 MB


@router.post("", response_model=List[DocumentOut])
async def upload(files: List[UploadFile] = File(...),
                 db: Session = Depends(get_db),
                 user=Depends(optional_user),
                 owner: str = Depends(current_owner)):
    if not files:
        raise HTTPException(400, "No files provided")

    # Enforce per-workspace limits (anti-abuse)
    existing = db.query(Document).filter(Document.owner_id == owner, Document.is_sample.is_(False)).all()
    if len(existing) + len(files) > MAX_DOCS_PER_WORKSPACE:
        raise HTTPException(429, f"Workspace document limit reached ({MAX_DOCS_PER_WORKSPACE}). "
                                 f"Delete some documents or reset your workspace.")
    used_bytes = sum(d.size_bytes for d in existing)

    out: List[Document] = []
    for f in files:
        if f.content_type not in ALLOWED_MIMES:
            raise HTTPException(415, f"Unsupported file type: {f.content_type}")
        data = await f.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "File too large (max 25MB)")
        if used_bytes + len(data) > MAX_BYTES_PER_WORKSPACE:
            raise HTTPException(429, f"Workspace storage limit reached ({MAX_BYTES_PER_WORKSPACE // 1024 // 1024} MB).")
        used_bytes += len(data)

        uid = new_uuid()
        ext = Path(f.filename).suffix.lower() or ".bin"
        # Store under data/uploads/<owner>/<uuid>/original.ext for clean per-workspace bulk-delete
        safe_owner = owner.replace(":", "_").replace("/", "_")
        rel = Path(safe_owner) / uid / f"original{ext}"
        full = Path(settings.upload_dir) / rel
        write_bytes(full, data)
        doc = Document(
            uuid=uid,
            filename=f.filename,
            mime_type=f.content_type,
            size_bytes=len(data),
            storage_path=str(full),
            sha256=sha256_bytes(data),
            status="uploaded",
            uploaded_by=user.id if user else None,
            owner_id=owner,
            is_sample=False,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        out.append(doc)
        runner.submit(doc.id)
    return out
