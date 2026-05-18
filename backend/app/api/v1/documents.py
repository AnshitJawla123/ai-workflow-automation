from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ...core.workspace import current_owner
from ...db.session import get_db
from ...models import AuditLog, Document, DocumentPage, ExtractedRecord, ValidationIssue
from ...schemas.common import Msg, Page
from ...schemas.documents import DocumentDetail, DocumentOut, FieldValueOut, RecordOut, ValidationIssueOut
from ...services.jobs.runner import runner
from ..deps import optional_user

router = APIRouter(prefix="/documents", tags=["documents"])


def _own_or_sample(qry, owner: str):
    return qry.filter(or_(Document.owner_id == owner, Document.is_sample.is_(True)))


@router.get("", response_model=Page[DocumentOut])
def list_documents(
    page: int = 1, page_size: int = 20,
    status: Optional[str] = None, q: Optional[str] = None,
    only_mine: bool = False,
    db: Session = Depends(get_db),
    owner: str = Depends(current_owner),
):
    qry = db.query(Document)
    if only_mine:
        qry = qry.filter(Document.owner_id == owner, Document.is_sample.is_(False))
    else:
        qry = _own_or_sample(qry, owner)
    if status:
        qry = qry.filter(Document.status == status)
    if q:
        qry = qry.filter(or_(Document.filename.ilike(f"%{q}%"), Document.uuid.ilike(f"%{q}%")))
    total = qry.count()
    items = qry.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Page[DocumentOut](items=items, total=total, page=page, page_size=page_size)


def _load_doc(doc_id: int, db: Session, owner: str) -> Document:
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.is_sample or doc.owner_id == owner:
        return doc
    raise HTTPException(403, "You don't have access to this document")


@router.get("/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: int, db: Session = Depends(get_db), owner: str = Depends(current_owner)):
    doc = _load_doc(doc_id, db, owner)
    records = db.query(ExtractedRecord).filter(ExtractedRecord.document_id == doc_id).order_by(
        ExtractedRecord.page_number, ExtractedRecord.row_index
    ).all()
    issues = db.query(ValidationIssue).filter(ValidationIssue.document_id == doc_id).all()
    rec_out = [
        RecordOut.model_validate({
            **{c.name: getattr(r, c.name) for c in r.__table__.columns},
            "field_values": [FieldValueOut.model_validate(fv) for fv in r.field_values],
        }) for r in records
    ]
    return DocumentDetail(
        **{c.name: getattr(doc, c.name) for c in doc.__table__.columns if c.name in DocumentOut.model_fields},
        records=rec_out,
        issues=[ValidationIssueOut.model_validate(i) for i in issues],
    )


@router.get("/{doc_id}/file")
def get_document_file(doc_id: int, db: Session = Depends(get_db), owner: str = Depends(current_owner)):
    doc = _load_doc(doc_id, db, owner)
    p = Path(doc.storage_path)
    if not p.exists():
        raise HTTPException(404, "File missing")
    return FileResponse(p, media_type=doc.mime_type, filename=doc.filename)


@router.get("/{doc_id}/pages/{page_no}/image")
def get_page_image(doc_id: int, page_no: int, db: Session = Depends(get_db), owner: str = Depends(current_owner)):
    _load_doc(doc_id, db, owner)  # access check
    page = db.query(DocumentPage).filter(
        DocumentPage.document_id == doc_id, DocumentPage.page_number == page_no
    ).first()
    if not page or not Path(page.image_path).exists():
        raise HTTPException(404, "Page image not found")
    return FileResponse(page.image_path, media_type="image/jpeg")


@router.post("/{doc_id}/reprocess", response_model=Msg)
def reprocess(doc_id: int, db: Session = Depends(get_db), user=Depends(optional_user),
              owner: str = Depends(current_owner)):
    doc = _load_doc(doc_id, db, owner)
    # Samples are world-readable but only admin can reprocess them
    if doc.is_sample and (not user or user.role != "admin"):
        raise HTTPException(403, "Sample documents can only be reprocessed by admins")
    db.query(ExtractedRecord).filter(ExtractedRecord.document_id == doc_id).delete()
    db.query(ValidationIssue).filter(ValidationIssue.document_id == doc_id).delete()
    doc.status = "uploaded"
    doc.progress = 0.0
    doc.error = None
    doc.updated_at = datetime.utcnow()
    db.commit()
    db.add(AuditLog(entity_type="document", entity_id=doc.id, action="reprocess",
                    actor_id=user.id if user else None))
    db.commit()
    runner.submit(doc.id)
    return Msg(message="Reprocess queued")


@router.delete("/{doc_id}", response_model=Msg)
def delete_document(doc_id: int, db: Session = Depends(get_db), user=Depends(optional_user),
                    owner: str = Depends(current_owner)):
    doc = _load_doc(doc_id, db, owner)
    if doc.is_sample and (not user or user.role != "admin"):
        raise HTTPException(403, "Sample documents can only be deleted by admins")
    if doc.owner_id != owner and not (user and user.role == "admin"):
        raise HTTPException(403, "Not yours")
    db.delete(doc)
    db.add(AuditLog(entity_type="document", entity_id=doc_id, action="delete",
                    actor_id=user.id if user else None))
    db.commit()
    return Msg(message="Deleted")
