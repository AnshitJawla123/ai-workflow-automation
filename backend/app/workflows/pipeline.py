"""Document processing pipeline — runs all stages for a single document.

Stages (sequential; each emits WebSocket progress events):
    1. preprocess  → OpenCV deskew + image normalization, PDF → page images
    2. detect      → identify table region (vision LLM, with fallback)
    3. extract     → vision-LLM JSON extraction per page
    4. confidence  → fuse LLM + format priors
    5. persist     → create ExtractedRecord + FieldValue rows
    6. validate    → run rule engine, attach issues
    7. index       → PageIndex + Vector + Graph
    8. complete    → mark document done, broadcast
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.session import SessionLocal
from ..models import Document, DocumentPage, ExtractedRecord, FieldValue, ValidationRule
from ..services.confidence.fusion import fuse, overall
from ..services.extraction.extractor import extract_from_image, detect_table
from ..services.jobs.runner import record_job
from ..services.jobs.ws_bus import emit
from ..services.rag.graph_rag import graph_rag
from ..services.rag.page_index import PageIndex, page_index
from ..services.rag.vector_store import vector_store
from ..services.validation.engine import persist_issues, validate_record
from ..utils.files import pdf_to_images, preprocess_image

log = logging.getLogger("pipeline")

CANONICAL_FIELDS = [
    "date", "shift", "employee_no", "operation_code",
    "machine_no", "work_order_no", "quantity_produced", "time_taken_hours",
]


def _set_status(db: Session, doc: Document, status: str, progress: float, error: str | None = None):
    doc.status = status
    doc.progress = progress
    if error:
        doc.error = error
    doc.updated_at = datetime.utcnow()
    db.commit()
    emit("document.update", {"id": doc.id, "status": status, "progress": progress, "error": error})


async def process_document(document_id: int) -> None:
    """Main entry — runs in the JobRunner thread."""
    t0 = time.time()
    db: Session = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if not doc:
            log.error("doc %s not found", document_id)
            return
        log.info("pipeline start doc=%s file=%s", doc.id, doc.filename)

        # ---- 1) Preprocess: render pages ----
        _set_status(db, doc, "preprocessing", 0.05)
        pages = _prepare_pages(db, doc)
        if not pages:
            _set_status(db, doc, "failed", 1.0, error="No pages produced from upload")
            record_job(db, doc.id, "preprocess", "failed", error="no pages")
            return
        record_job(db, doc.id, "preprocess", "success", result={"pages": len(pages)})

        # ---- 2..7) For each page, detect+extract+persist+validate+index ----
        all_records: List[ExtractedRecord] = []
        rules = db.query(ValidationRule).filter(ValidationRule.enabled.is_(True)).all()

        for idx, page in enumerate(pages, start=1):
            ratio = idx / max(len(pages), 1)
            _set_status(db, doc, "extracting", 0.05 + 0.6 * ratio)

            # Table detection (best-effort)
            try:
                meta = detect_table(page.image_path)
                title = meta.get("title", "Machine shop data") if isinstance(meta, dict) else "Machine shop data"
            except Exception:
                title = "Machine shop data"
            record_job(db, doc.id, "detect", "success", result={"page": idx, "title": title})

            # Extraction (sync — runs in this asyncio thread)
            try:
                payload = await asyncio.to_thread(extract_from_image, page.image_path, idx, title)
            except Exception as e:
                _set_status(db, doc, "failed", 1.0, error=f"extract failed: {e}")
                record_job(db, doc.id, "extract", "failed", error=str(e))
                return
            record_job(db, doc.id, "extract", "success", result={"rows": len(payload.get("records", []))})

            # Persist records with per-field confidence fusion
            recs = _persist_records(db, doc, page, payload)
            all_records.extend(recs)

            # Indexing (vector + page + graph)
            try:
                vector_store.upsert_records(doc.id, payload.get("records", []))
            except Exception as e:
                log.warning("vector index failed: %s", e)
            try:
                tree = PageIndex.build_from_records(doc.id, title, payload.get("records", []))
                page_index.save_document_tree(doc.id, tree)
            except Exception as e:
                log.warning("page index failed: %s", e)
            try:
                for r in recs:
                    rec_dict = {c.name: getattr(r, c.name) for c in r.__table__.columns}
                    graph_rag.add_record_triples(doc.id, r.id, rec_dict)
                graph_rag.save()
            except Exception as e:
                log.warning("graph index failed: %s", e)

        # ---- 8) Validate everything ----
        _set_status(db, doc, "validating", 0.85)
        for r in all_records:
            failures = validate_record(db, r, rules, siblings=all_records)
            persist_issues(db, r, failures)
        record_job(db, doc.id, "validate", "success", result={"records": len(all_records)})

        # ---- Complete ----
        any_needs = any(r.review_status == "needs_review" for r in all_records)
        final_status = "needs_review" if any_needs else "completed"
        _set_status(db, doc, final_status, 1.0)
        record_job(db, doc.id, "complete", "success",
                   result={"records": len(all_records), "elapsed_sec": round(time.time() - t0, 2)})
        log.info("pipeline done doc=%s in %.2fs status=%s", doc.id, time.time() - t0, final_status)
    except Exception as e:
        log.exception("pipeline crashed: %s", e)
        try:
            _set_status(db, doc, "failed", 1.0, error=str(e))
            record_job(db, doc.id, "pipeline", "failed", error=str(e))
        except Exception:
            pass
    finally:
        db.close()


def _prepare_pages(db: Session, doc: Document) -> List[DocumentPage]:
    # Clear any prior pages so reprocess is idempotent
    db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).delete()
    db.commit()
    src = Path(doc.storage_path)
    pages_dir = src.parent / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    images: List[Path] = []
    if doc.mime_type == "application/pdf" or src.suffix.lower() == ".pdf":
        images = pdf_to_images(src, pages_dir)
        if not images:
            log.warning("pdf2image failed; treating PDF as un-renderable")
            return []
    else:
        out = pages_dir / "page_001.jpg"
        try:
            preprocess_image(src, out)
            images = [out]
        except Exception as e:
            log.warning("preprocess failed (%s); using raw file", e)
            images = [src]
    pages: List[DocumentPage] = []
    for i, img_path in enumerate(images, start=1):
        page = DocumentPage(document_id=doc.id, page_number=i, image_path=str(img_path))
        db.add(page)
        pages.append(page)
    doc.page_count = len(pages)
    db.commit()
    for p in pages:
        db.refresh(p)
    return pages


def _persist_records(db: Session, doc: Document, page: DocumentPage, payload: Dict[str, Any]) -> List[ExtractedRecord]:
    out: List[ExtractedRecord] = []
    for rec in payload.get("records", []):
        confs = rec.get("confidence", {}) or {}
        bboxes = rec.get("bbox", {}) or {}
        reasons = rec.get("reasoning", {}) or {}
        fused: Dict[str, float] = {}
        record = ExtractedRecord(
            document_id=doc.id,
            page_number=page.page_number,
            row_index=int(rec.get("row_index") or len(out) + 1),
            date=_s(rec.get("date")),
            shift=_s(rec.get("shift")),
            employee_no=_s(rec.get("employee_no")),
            operation_code=_s(rec.get("operation_code")),
            machine_no=_s(rec.get("machine_no")),
            work_order_no=_s(rec.get("work_order_no")),
            quantity_produced=_f(rec.get("quantity_produced")),
            time_taken_hours=_f(rec.get("time_taken_hours")),
            extras=rec,
        )
        db.add(record)
        db.flush()  # get id
        for field in CANONICAL_FIELDS:
            v = getattr(record, field)
            score = fuse(field, v, float(confs.get(field) or 0.0))
            fused[field] = score
            db.add(FieldValue(
                record_id=record.id,
                field_name=field,
                raw_value=str(rec.get(field)) if rec.get(field) is not None else None,
                normalized_value=str(v) if v is not None else None,
                confidence=score,
                source="llm",
                bbox=bboxes.get(field),
                reasoning=reasons.get(field),
            ))
        record.overall_confidence = overall(fused)
        if record.overall_confidence < settings.conf_yellow_min:
            record.review_status = "needs_review"
        out.append(record)
    db.commit()
    for r in out:
        db.refresh(r)
    return out


def _s(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _f(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None
