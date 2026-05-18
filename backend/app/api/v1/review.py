from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...core.workspace import current_owner
from ...db.session import get_db
from ...models import AuditLog, Document, ExtractedRecord, FieldValue, ValidationIssue, ValidationRule
from ...schemas.common import Msg
from ...schemas.documents import RecordOut, RecordUpdate
from ...services.validation.engine import persist_issues, validate_record
from ..deps import optional_user

router = APIRouter(prefix="/records", tags=["records"])


def _check_access(db: Session, record_id: int, owner: str, user=None) -> ExtractedRecord:
    r = db.get(ExtractedRecord, record_id)
    if not r:
        raise HTTPException(404, "Record not found")
    doc = db.get(Document, r.document_id)
    if not doc or (not doc.is_sample and doc.owner_id != owner):
        raise HTTPException(403, "No access to this record")
    # Samples are read-only for non-admins
    if doc.is_sample and (not user or user.role != "admin"):
        # Allow GET but block mutations — caller decides; we just flag via attr
        r._is_sample_readonly = True  # type: ignore[attr-defined]
    return r


@router.get("/{record_id}", response_model=RecordOut)
def get_record(record_id: int, db: Session = Depends(get_db), owner: str = Depends(current_owner)):
    r = _check_access(db, record_id, owner)
    return RecordOut.model_validate({
        **{c.name: getattr(r, c.name) for c in r.__table__.columns},
        "field_values": [fv for fv in r.field_values],
    })


@router.patch("/{record_id}", response_model=RecordOut)
def update_record(record_id: int, payload: RecordUpdate, db: Session = Depends(get_db),
                  user=Depends(optional_user), owner: str = Depends(current_owner)):
    r = _check_access(db, record_id, owner, user)
    if getattr(r, "_is_sample_readonly", False):
        raise HTTPException(403, "Sample records are read-only. Upload your own document to test edits.")
    diff = {}
    for field, value in payload.model_dump(exclude_none=True).items():
        old = getattr(r, field)
        if old != value:
            diff[field] = {"old": old, "new": value}
            setattr(r, field, value)
            # mark field as manually edited
            fv = next((f for f in r.field_values if f.field_name == field), None)
            if fv:
                fv.normalized_value = str(value)
                fv.confidence = 1.0
                fv.source = "manual"
                fv.edited = True
    if payload.review_status in {"approved", "rejected", "needs_review", "pending"}:
        r.review_status = payload.review_status
        r.reviewed_by = user.id if user else None
        r.reviewed_at = datetime.utcnow()
    r.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(r)

    # Re-run validation after edit
    rules = db.query(ValidationRule).filter(ValidationRule.enabled.is_(True)).all()
    siblings = db.query(ExtractedRecord).filter(ExtractedRecord.document_id == r.document_id).all()
    db.query(ValidationIssue).filter(ValidationIssue.record_id == r.id).delete()
    db.commit()
    failures = validate_record(db, r, rules, siblings=siblings)
    persist_issues(db, r, failures)

    db.add(AuditLog(entity_type="record", entity_id=r.id, action="update",
                    actor_id=user.id if user else None, diff=diff))
    db.commit()
    return RecordOut.model_validate({
        **{c.name: getattr(r, c.name) for c in r.__table__.columns},
        "field_values": [fv for fv in r.field_values],
    })


@router.post("/{record_id}/approve", response_model=Msg)
def approve(record_id: int, db: Session = Depends(get_db), user=Depends(optional_user),
            owner: str = Depends(current_owner)):
    r = _check_access(db, record_id, owner, user)
    if getattr(r, "_is_sample_readonly", False):
        raise HTTPException(403, "Sample records are read-only.")
    r.review_status = "approved"
    r.reviewed_by = user.id if user else None
    r.reviewed_at = datetime.utcnow()
    db.commit()
    db.add(AuditLog(entity_type="record", entity_id=r.id, action="approve",
                    actor_id=user.id if user else None))
    db.commit()
    return Msg(message="Approved")


@router.post("/{record_id}/reject", response_model=Msg)
def reject(record_id: int, db: Session = Depends(get_db), user=Depends(optional_user),
           owner: str = Depends(current_owner)):
    r = _check_access(db, record_id, owner, user)
    if getattr(r, "_is_sample_readonly", False):
        raise HTTPException(403, "Sample records are read-only.")
    r.review_status = "rejected"
    r.reviewed_by = user.id if user else None
    r.reviewed_at = datetime.utcnow()
    db.commit()
    db.add(AuditLog(entity_type="record", entity_id=r.id, action="reject",
                    actor_id=user.id if user else None))
    db.commit()
    return Msg(message="Rejected")
