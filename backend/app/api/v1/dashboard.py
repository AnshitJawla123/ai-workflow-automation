from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ...core.workspace import current_owner
from ...db.session import get_db
from ...models import Document, ExtractedRecord, ValidationIssue

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _own_or_sample(query, owner: str):
    return query.filter(or_(Document.owner_id == owner, Document.is_sample.is_(True)))


def _scoped_record_q(db: Session, owner: str):
    """ExtractedRecord query joined to Document filtered by workspace."""
    return db.query(ExtractedRecord).join(Document, ExtractedRecord.document_id == Document.id).filter(
        or_(Document.owner_id == owner, Document.is_sample.is_(True))
    )


def _scoped_issue_q(db: Session, owner: str):
    return db.query(ValidationIssue).join(Document, ValidationIssue.document_id == Document.id).filter(
        or_(Document.owner_id == owner, Document.is_sample.is_(True))
    )


@router.get("/kpis")
def kpis(db: Session = Depends(get_db), owner: str = Depends(current_owner)) -> Dict[str, Any]:
    base = _own_or_sample(db.query(Document), owner)
    total_docs = base.count()
    completed = base.filter(Document.status == "completed").count()
    needs_review = base.filter(Document.status == "needs_review").count()
    failed = base.filter(Document.status == "failed").count()
    rec_q = _scoped_record_q(db, owner)
    total_records = rec_q.count()
    issues = _scoped_issue_q(db, owner).count()
    avg_conf = rec_q.with_entities(func.coalesce(func.avg(ExtractedRecord.overall_confidence), 0.0)).scalar() or 0.0
    total_qty = rec_q.with_entities(func.coalesce(func.sum(ExtractedRecord.quantity_produced), 0.0)).scalar() or 0.0
    return {
        "total_documents": total_docs,
        "completed": completed,
        "needs_review": needs_review,
        "failed": failed,
        "total_records": total_records,
        "validation_issues": issues,
        "avg_confidence": round(float(avg_conf), 3),
        "total_quantity_produced": float(total_qty),
    }


@router.get("/shift-summary")
def shift_summary(db: Session = Depends(get_db), owner: str = Depends(current_owner)) -> List[Dict[str, Any]]:
    q = _scoped_record_q(db, owner).with_entities(
        ExtractedRecord.shift,
        func.count(ExtractedRecord.id),
        func.coalesce(func.sum(ExtractedRecord.quantity_produced), 0.0),
        func.coalesce(func.avg(ExtractedRecord.time_taken_hours), 0.0),
    ).group_by(ExtractedRecord.shift)
    return [{"shift": s or "Unknown", "records": int(c), "total_qty": float(qq), "avg_hours": float(h)}
            for s, c, qq, h in q.all()]


@router.get("/machine-summary")
def machine_summary(db: Session = Depends(get_db), owner: str = Depends(current_owner)) -> List[Dict[str, Any]]:
    q = _scoped_record_q(db, owner).with_entities(
        ExtractedRecord.machine_no,
        func.count(ExtractedRecord.id),
        func.coalesce(func.sum(ExtractedRecord.quantity_produced), 0.0),
    ).group_by(ExtractedRecord.machine_no).order_by(
        func.sum(ExtractedRecord.quantity_produced).desc()).limit(20)
    return [{"machine": m or "Unknown", "records": int(c), "total_qty": float(qq)} for m, c, qq in q.all()]


@router.get("/daily-throughput")
def daily_throughput(db: Session = Depends(get_db), owner: str = Depends(current_owner),
                     days: int = 30) -> List[Dict[str, Any]]:
    q = _scoped_record_q(db, owner).with_entities(
        ExtractedRecord.date,
        func.count(ExtractedRecord.id),
        func.coalesce(func.sum(ExtractedRecord.quantity_produced), 0.0),
    ).group_by(ExtractedRecord.date).order_by(ExtractedRecord.date.desc()).limit(days)
    return [{"date": d or "n/a", "records": int(c), "total_qty": float(qq)} for d, c, qq in q.all()]


@router.get("/top-issues")
def top_issues(db: Session = Depends(get_db), owner: str = Depends(current_owner),
               limit: int = 10) -> List[Dict[str, Any]]:
    q = _scoped_issue_q(db, owner).with_entities(
        ValidationIssue.rule_code, func.count(ValidationIssue.id)
    ).group_by(ValidationIssue.rule_code).order_by(func.count(ValidationIssue.id).desc()).limit(limit)
    return [{"rule": r, "count": int(c)} for r, c in q.all()]


@router.get("/recent-uploads")
def recent_uploads(db: Session = Depends(get_db), owner: str = Depends(current_owner),
                   limit: int = 10) -> List[Dict[str, Any]]:
    rows = _own_or_sample(db.query(Document), owner).order_by(Document.created_at.desc()).limit(limit).all()
    return [{"id": r.id, "filename": r.filename, "status": r.status, "progress": r.progress,
             "is_sample": bool(r.is_sample), "created_at": r.created_at} for r in rows]
