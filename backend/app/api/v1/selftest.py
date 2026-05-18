"""End-to-end self-test: ingest seed images, run pipeline, return summary."""
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.workspace import current_owner
from ...db.session import get_db
from ...models import Document
from ...services.jobs.runner import runner
from ...utils.files import new_uuid, sha256_bytes, write_bytes
from ...core.config import settings

router = APIRouter(prefix="/selftest", tags=["meta"])


@router.post("/seed")
def seed(db: Session = Depends(get_db), owner: str = Depends(current_owner)):
    # Try common locations (covers dev, Docker, Render, Fly, monorepo)
    candidates = [
        Path("/app/samples"),                                  # Docker
        Path(__file__).resolve().parents[4] / "samples",       # repo root / samples
        Path(__file__).resolve().parents[3] / "samples",
        Path.cwd() / "samples",
        Path.cwd() / ".." / "samples",
        Path(__file__).resolve().parents[4] / "files",         # legacy /files alias
    ]
    samples_dir = next((p for p in candidates if p.exists()), None)
    if not samples_dir:
        return {"ok": False, "reason": "no samples directory",
                "looked": [str(p) for p in candidates]}
    created: List[int] = []
    for img in sorted(samples_dir.glob("*.jpeg")):
        data = img.read_bytes()
        uid = new_uuid()
        full = Path(settings.upload_dir) / uid / f"original{img.suffix}"
        write_bytes(full, data)
        doc = Document(
            uuid=uid, filename=img.name, mime_type="image/jpeg", size_bytes=len(data),
            storage_path=str(full), sha256=sha256_bytes(data), status="uploaded",
            owner_id=owner, is_sample=False,
        )
        db.add(doc); db.commit(); db.refresh(doc)
        runner.submit(doc.id)
        created.append(doc.id)
    return {"ok": True, "created": created}
