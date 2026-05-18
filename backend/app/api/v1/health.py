from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...core.config import settings

router = APIRouter(tags=["meta"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    # Provider status (no API calls — just check key presence)
    from ...services.llm import providers as llm_providers
    enabled = llm_providers.enabled_providers()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "app": settings.app_name,
        "env": settings.app_env,
        "version": "1.0.0",
        "llm_providers_enabled": enabled,
        "llm_provider_count": len(enabled),
        "vision_consensus_active": len(enabled) >= 2,
        "warning": None if enabled else "No LLM provider configured — extraction will fail."
    }


@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        from ...services.llm import providers as llm_providers
        ready_flag = bool(llm_providers.enabled_providers())
        return {"ready": ready_flag,
                "reason": None if ready_flag else "no_llm_provider_configured"}
    except Exception as e:
        return {"ready": False, "reason": str(e)}


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Prometheus-format exporter (counters only, no external dep)."""
    from ...models import Document, ExtractedRecord, ValidationIssue
    docs = db.query(Document).count()
    recs = db.query(ExtractedRecord).count()
    issues = db.query(ValidationIssue).count()
    completed = db.query(Document).filter(Document.status == "completed").count()
    needs_review = db.query(Document).filter(Document.status == "needs_review").count()
    failed = db.query(Document).filter(Document.status == "failed").count()
    from sqlalchemy import func
    avg_conf = db.query(func.coalesce(func.avg(ExtractedRecord.overall_confidence), 0.0)).scalar() or 0.0
    body = (
        "# HELP awa_documents_total Total uploaded documents\n"
        "# TYPE awa_documents_total counter\n"
        f"awa_documents_total {docs}\n"
        f"awa_documents_completed_total {completed}\n"
        f"awa_documents_needs_review_total {needs_review}\n"
        f"awa_documents_failed_total {failed}\n"
        "# HELP awa_records_total Total extracted records\n"
        "# TYPE awa_records_total counter\n"
        f"awa_records_total {recs}\n"
        "# HELP awa_validation_issues_total Total validation issues\n"
        "# TYPE awa_validation_issues_total counter\n"
        f"awa_validation_issues_total {issues}\n"
        "# HELP awa_avg_confidence Average extraction confidence (0-1)\n"
        "# TYPE awa_avg_confidence gauge\n"
        f"awa_avg_confidence {avg_conf:.4f}\n"
    )
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(body, media_type="text/plain; version=0.0.4")
