from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ...core.workspace import current_owner
from ...db.session import get_db
from ...models import AuditLog, Document, ExtractedRecord

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    owner: str = Depends(current_owner),
):
    # Workspace scope: only show entries about documents this workspace can see
    allowed_doc_ids = {r[0] for r in db.query(Document.id).filter(
        or_(Document.owner_id == owner, Document.is_sample.is_(True))
    ).all()}
    allowed_record_ids = {r[0] for r in db.query(ExtractedRecord.id).filter(
        ExtractedRecord.document_id.in_(allowed_doc_ids)
    ).all()} if allowed_doc_ids else set()
    q = db.query(AuditLog)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)
    rows = q.order_by(AuditLog.created_at.desc()).limit(limit * 4).all()
    # Filter by allowed entities
    filtered = []
    for r in rows:
        if r.entity_type == "document" and r.entity_id in allowed_doc_ids:
            filtered.append(r)
        elif r.entity_type == "record" and r.entity_id in allowed_record_ids:
            filtered.append(r)
        elif r.entity_type == "workspace":
            filtered.append(r)  # always show user's own workspace events
        if len(filtered) >= limit:
            break
    return [{"id": r.id, "entity_type": r.entity_type, "entity_id": r.entity_id,
             "action": r.action, "actor_id": r.actor_id, "diff": r.diff,
             "note": r.note, "created_at": r.created_at} for r in filtered]
