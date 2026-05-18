"""Export endpoints: CSV, Excel, JSON, per-document PDF report."""
import csv
import io
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session

from ...core.workspace import current_owner
from ...db.session import get_db
from ...models import ExtractedRecord, Document, ValidationIssue
from ...core.config import settings
from sqlalchemy import or_

router = APIRouter(prefix="/export", tags=["export"])


def _scoped_records(db, owner: str, document_id: Optional[int] = None):
    q = db.query(ExtractedRecord).join(Document, ExtractedRecord.document_id == Document.id).filter(
        or_(Document.owner_id == owner, Document.is_sample.is_(True))
    )
    if document_id:
        q = q.filter(ExtractedRecord.document_id == document_id)
    return q

COLS = ["id", "document_id", "page_number", "row_index", "date", "shift", "employee_no",
        "operation_code", "machine_no", "work_order_no", "quantity_produced",
        "time_taken_hours", "overall_confidence", "review_status"]


@router.get("/csv")
def export_csv(document_id: Optional[int] = None, db: Session = Depends(get_db),
               owner: str = Depends(current_owner)):
    q = _scoped_records(db, owner, document_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLS)
    for r in q.all():
        w.writerow([getattr(r, c) for c in COLS])
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=records.csv"})


@router.get("/json")
def export_json(document_id: Optional[int] = None, db: Session = Depends(get_db),
                owner: str = Depends(current_owner)):
    q = _scoped_records(db, owner, document_id)
    data = [{c: getattr(r, c) for c in COLS} for r in q.all()]
    return Response(content=json.dumps(data, default=str, indent=2),
                    media_type="application/json",
                    headers={"Content-Disposition": "attachment; filename=records.json"})


@router.get("/xlsx")
def export_xlsx(document_id: Optional[int] = None, db: Session = Depends(get_db),
                owner: str = Depends(current_owner)):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Records"
    ws.append(COLS)
    q = _scoped_records(db, owner, document_id)
    for r in q.all():
        ws.append([getattr(r, c) for c in COLS])
    buf = io.BytesIO()
    wb.save(buf)
    return Response(content=buf.getvalue(),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=records.xlsx"})


@router.get("/pdf/{document_id}")
def export_pdf(document_id: int, db: Session = Depends(get_db),
               owner: str = Depends(current_owner)):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if not doc.is_sample and doc.owner_id != owner:
        raise HTTPException(403, "No access to this document")
    records = db.query(ExtractedRecord).filter(ExtractedRecord.document_id == document_id).order_by(
        ExtractedRecord.page_number, ExtractedRecord.row_index).all()
    issues = db.query(ValidationIssue).filter(ValidationIssue.document_id == document_id).all()
    out_path = Path(settings.export_dir) / f"document_{document_id}.pdf"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = SimpleDocTemplate(str(out_path), pagesize=A4, title=f"Document {document_id} report")
    styles = getSampleStyleSheet()
    story = [Paragraph(f"<b>Operational Record Report</b> — {doc.filename}", styles["Title"]),
             Paragraph(f"Status: {doc.status} · Records: {len(records)} · Issues: {len(issues)}", styles["Normal"]),
             Spacer(1, 10)]
    data = [["#", "Date", "Shift", "Emp", "Machine", "WO", "Op", "Qty", "Hrs", "Conf", "Status"]]
    for r in records:
        data.append([r.row_index, r.date, r.shift, r.employee_no, r.machine_no, r.work_order_no,
                     r.operation_code, r.quantity_produced, r.time_taken_hours,
                     f"{r.overall_confidence:.2f}", r.review_status])
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                           ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                           ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    story.append(t)
    if issues:
        story += [Spacer(1, 12), Paragraph("<b>Validation Issues</b>", styles["Heading3"])]
        for i in issues:
            story.append(Paragraph(f"[{i.severity}] {i.rule_code}: {i.message}", styles["Normal"]))
    pdf.build(story)
    return FileResponse(out_path, media_type="application/pdf", filename=out_path.name)
