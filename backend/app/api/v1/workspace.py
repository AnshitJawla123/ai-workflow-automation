"""Workspace API — per-user / per-browser data isolation for multi-tenant demo."""
from __future__ import annotations

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ...core.config import settings
from ...core.workspace import (
    WORKSPACE_COOKIE, WORKSPACE_COOKIE_MAX_AGE,
    current_owner, get_or_create_workspace,
)
from ...db.session import get_db
from ...models import AuditLog, Document, ExtractedRecord, ValidationIssue
from ...schemas.common import Msg
from ..deps import optional_user

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("/me")
def me(db: Session = Depends(get_db), owner: str = Depends(current_owner),
       user=Depends(optional_user)) -> Dict[str, Any]:
    is_anonymous = owner.startswith("ws:")
    own_docs = db.query(Document).filter(Document.owner_id == owner, Document.is_sample.is_(False)).all()
    used_bytes = sum(d.size_bytes for d in own_docs)
    sample_count = db.query(Document).filter(Document.is_sample.is_(True)).count()
    return {
        "owner_id": owner,
        "is_anonymous": is_anonymous,
        "user": {"id": user.id, "email": user.email, "role": user.role} if user else None,
        "docs_uploaded": len(own_docs),
        "storage_used_bytes": used_bytes,
        "storage_limit_bytes": 50 * 1024 * 1024,
        "doc_limit": 50,
        "samples_visible": sample_count,
        "cookie_max_age_days": WORKSPACE_COOKIE_MAX_AGE // 86400,
    }


@router.post("/reset", response_model=Msg)
def reset(db: Session = Depends(get_db), owner: str = Depends(current_owner),
          user=Depends(optional_user)):
    """Wipe all NON-sample documents for the current workspace and their files."""
    docs = db.query(Document).filter(Document.owner_id == owner, Document.is_sample.is_(False)).all()
    n = len(docs)
    for d in docs:
        try:
            p = Path(d.storage_path)
            if p.exists():
                # Delete the workspace folder (one dir up from original.<ext>)
                if p.parent.exists():
                    shutil.rmtree(p.parent, ignore_errors=True)
        except Exception:
            pass
        db.delete(d)
    db.add(AuditLog(entity_type="workspace", entity_id=0, action="reset",
                    actor_id=user.id if user else None, diff={"docs_deleted": n, "owner": owner}))
    db.commit()
    return Msg(message=f"Reset complete — {n} documents deleted")


@router.post("/new", response_model=Msg)
def new_workspace(response: Response):
    """Force a fresh anonymous workspace cookie (handy for testing isolation in same browser)."""
    import uuid
    new_ws = f"ws:{uuid.uuid4().hex[:16]}"
    response.set_cookie(WORKSPACE_COOKIE, new_ws,
                         max_age=WORKSPACE_COOKIE_MAX_AGE,
                         httponly=True, samesite="lax",
                         secure=settings.app_env == "production", path="/")
    return Msg(message=f"New workspace: {new_ws}")


@router.post("/cleanup-stale", response_model=Msg)
def cleanup_stale(db: Session = Depends(get_db), user=Depends(optional_user)):
    """Admin-only: delete anonymous workspaces inactive >24h."""
    if not user or user.role != "admin":
        raise HTTPException(403, "Admin only")
    cutoff = datetime.utcnow() - timedelta(hours=24)
    stale = db.query(Document).filter(
        Document.owner_id.like("ws:%"),
        Document.is_sample.is_(False),
        Document.created_at < cutoff,
    ).all()
    n = len(stale)
    for d in stale:
        try:
            p = Path(d.storage_path)
            if p.parent.exists():
                shutil.rmtree(p.parent, ignore_errors=True)
        except Exception:
            pass
        db.delete(d)
    db.commit()
    return Msg(message=f"Cleaned {n} stale anonymous documents")
