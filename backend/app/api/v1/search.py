from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ...core.workspace import current_owner
from ...db.session import get_db
from ...models import Document, ExtractedRecord
from ...services.rag.graph_rag import graph_rag
from ...services.rag.page_index import page_index
from ...services.rag.vector_store import vector_store

router = APIRouter(prefix="/search", tags=["search"])


class SearchHit(BaseModel):
    type: str
    score: float
    record_id: Optional[int] = None
    document_id: Optional[int] = None
    snippet: str
    metadata: Dict[str, Any] = {}


def _allowed_doc_ids(db: Session, owner: str) -> set:
    """Set of document ids the owner can see (their own + samples)."""
    rows = db.query(Document.id).filter(or_(Document.owner_id == owner, Document.is_sample.is_(True))).all()
    return {r[0] for r in rows}


@router.get("", response_model=List[SearchHit])
def search(
    q: str = Query(..., min_length=1),
    top_k: int = 20,
    mode: str = Query("hybrid", description="hybrid|keyword|vector|graph|page"),
    db: Session = Depends(get_db),
    owner: str = Depends(current_owner),
):
    allowed = _allowed_doc_ids(db, owner)
    hits: List[SearchHit] = []

    if mode in ("hybrid", "keyword"):
        like = f"%{q}%"
        qry = db.query(ExtractedRecord).join(Document, ExtractedRecord.document_id == Document.id).filter(
            or_(Document.owner_id == owner, Document.is_sample.is_(True))
        ).filter(or_(
            ExtractedRecord.employee_no.ilike(like),
            ExtractedRecord.machine_no.ilike(like),
            ExtractedRecord.work_order_no.ilike(like),
            ExtractedRecord.operation_code.ilike(like),
            ExtractedRecord.shift.ilike(like),
            ExtractedRecord.date.ilike(like),
        )).limit(top_k)
        for r in qry.all():
            hits.append(SearchHit(type="keyword", score=1.0, record_id=r.id, document_id=r.document_id,
                                  snippet=f"Row {r.row_index}: {r.machine_no} / {r.employee_no} / WO {r.work_order_no}",
                                  metadata={"shift": r.shift, "date": r.date,
                                            "qty": r.quantity_produced, "hrs": r.time_taken_hours}))

    if mode in ("hybrid", "vector"):
        for v in vector_store.search(q, top_k=top_k):
            did = int(v["metadata"].get("document_id", 0)) if v.get("metadata") else None
            if did and did not in allowed:
                continue  # tenant isolation
            hits.append(SearchHit(type="vector", score=1 - (v.get("distance") or 0.5),
                                  document_id=did,
                                  snippet=v.get("document", "")[:240], metadata=v.get("metadata", {})))

    if mode in ("hybrid", "page"):
        for p in page_index.search(q, top_k=top_k):
            if p.get("document_id") and p["document_id"] not in allowed:
                continue
            hits.append(SearchHit(type="page", score=float(p["score"]),
                                  document_id=p["document_id"],
                                  snippet=f"{p['title']} — {p['summary']}",
                                  metadata=p.get("data") or {}))

    if mode in ("hybrid", "graph"):
        terms = [t for t in q.split() if t]
        for g in graph_rag.query(terms, depth=2):
            for e in g["edges"]:
                # Graph triples don't carry document_id yet; restrict to keyword-matched docs
                hits.append(SearchHit(type="graph", score=0.5,
                                      snippet=f"{e['source']} --{e['predicate']}--> {e['target']}",
                                      metadata=e.get("meta") or {}))

    seen = set()
    out = []
    for h in sorted(hits, key=lambda x: -x.score):
        k = (h.type, h.snippet[:80])
        if k in seen:
            continue
        seen.add(k)
        out.append(h)
        if len(out) >= top_k * 2:
            break
    return out
