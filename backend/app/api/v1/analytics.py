from typing import Any, Dict, List

import statistics

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ...core.workspace import current_owner
from ...db.session import get_db
from ...models import Document, ExtractedRecord

router = APIRouter(prefix="/analytics", tags=["analytics"])


class AnomalyOut(BaseModel):
    record_id: int
    field: str
    value: float
    z_score: float
    message: str


def _scoped(db: Session, owner: str):
    return db.query(ExtractedRecord).join(Document, ExtractedRecord.document_id == Document.id).filter(
        or_(Document.owner_id == owner, Document.is_sample.is_(True))
    )


@router.get("/anomalies", response_model=List[AnomalyOut])
def anomalies(db: Session = Depends(get_db), owner: str = Depends(current_owner)) -> List[AnomalyOut]:
    out: List[AnomalyOut] = []
    rows = _scoped(db, owner).filter(ExtractedRecord.machine_no.isnot(None)).all()
    by_machine: Dict[str, List[ExtractedRecord]] = {}
    for r in rows:
        by_machine.setdefault(r.machine_no, []).append(r)
    for machine, group in by_machine.items():
        for field in ("quantity_produced", "time_taken_hours"):
            vals = [float(getattr(r, field)) for r in group if getattr(r, field) is not None]
            if len(vals) < 4:
                continue
            mu = statistics.mean(vals)
            sd = statistics.pstdev(vals) or 1.0
            for r in group:
                v = getattr(r, field)
                if v is None:
                    continue
                z = (float(v) - mu) / sd
                if abs(z) >= 2.5:
                    out.append(AnomalyOut(
                        record_id=r.id, field=field, value=float(v), z_score=round(z, 2),
                        message=f"{field}={v} on {machine} is {round(z,2)}σ from mean ({round(mu,1)})"
                    ))
    return out


@router.get("/quantity-trend")
def quantity_trend(db: Session = Depends(get_db), owner: str = Depends(current_owner)) -> List[Dict[str, Any]]:
    rows = _scoped(db, owner).filter(ExtractedRecord.date.isnot(None)).all()
    by_date: Dict[str, float] = {}
    for r in rows:
        if r.quantity_produced is None:
            continue
        by_date[r.date] = by_date.get(r.date, 0.0) + float(r.quantity_produced)
    return [{"date": d, "total_qty": q} for d, q in sorted(by_date.items())]


@router.get("/top-operators")
def top_operators(db: Session = Depends(get_db), owner: str = Depends(current_owner),
                  limit: int = 10) -> List[Dict[str, Any]]:
    rows = _scoped(db, owner).filter(ExtractedRecord.employee_no.isnot(None)).all()
    by_emp: Dict[str, float] = {}
    cnt: Dict[str, int] = {}
    for r in rows:
        if r.quantity_produced is None:
            continue
        by_emp[r.employee_no] = by_emp.get(r.employee_no, 0.0) + float(r.quantity_produced)
        cnt[r.employee_no] = cnt.get(r.employee_no, 0) + 1
    out = [{"employee": e, "total_qty": q, "records": cnt[e]} for e, q in by_emp.items()]
    out.sort(key=lambda x: -x["total_qty"])
    return out[:limit]
