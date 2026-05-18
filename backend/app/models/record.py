from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Float, JSON, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from ..db.session import Base


class ExtractedRecord(Base):
    """One row of a machine-shop table (or generic operational record)."""
    __tablename__ = "extracted_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int] = mapped_column(Integer, default=1)
    row_index: Mapped[int] = mapped_column(Integer)
    # Canonical operational fields (extensible via field_values)
    date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    shift: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, index=True)
    employee_no: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    operation_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    machine_no: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    work_order_no: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    quantity_produced: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    time_taken_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    review_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # pending | approved | rejected | needs_review
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extras: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document: Mapped["Document"] = relationship(back_populates="records")  # type: ignore[name-defined]
    field_values: Mapped[List["FieldValue"]] = relationship(
        back_populates="record", cascade="all, delete-orphan"
    )


class FieldValue(Base):
    """Per-field value with confidence + provenance, used for review UI."""
    __tablename__ = "field_values"
    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("extracted_records.id", ondelete="CASCADE"), index=True)
    field_name: Mapped[str] = mapped_column(String(64), index=True)
    raw_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(32), default="llm")  # llm | ocr | manual
    bbox: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    edited: Mapped[bool] = mapped_column(Boolean, default=False)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    record: Mapped["ExtractedRecord"] = relationship(back_populates="field_values")
