from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Float, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from ..db.session import Base


class Document(Base):
    """An uploaded operational document (image or PDF)."""
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    filename: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(1024))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", index=True)
    # uploaded | preprocessing | ocr | extracting | validating | indexed | completed | failed | needs_review
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    doc_type: Mapped[str] = mapped_column(String(64), default="machine_shop")
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    uploaded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Multi-tenant ownership: format "user:<id>" or "ws:<uuid>" (anonymous workspace).
    owner_id: Mapped[Optional[str]] = mapped_column(String(80), index=True, nullable=True)
    # Sample/demo flag — these are world-readable so evaluators can test without uploading.
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pages: Mapped[List["DocumentPage"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    records: Mapped[List["ExtractedRecord"]] = relationship(  # type: ignore[name-defined]
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    image_path: Mapped[str] = mapped_column(String(1024))
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    page_tree: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # PageIndex tree
    raw_ocr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="pages")
