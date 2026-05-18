from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from ..db.session import Base


class ValidationRule(Base):
    """Configurable business rule (built-in + user-defined via GUI)."""
    __tablename__ = "validation_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    field: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rule_type: Mapped[str] = mapped_column(String(32))  # required | regex | enum | range | unique | expression | duplicate
    params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="error")  # error | warning | info
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ValidationIssue(Base):
    __tablename__ = "validation_issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    record_id: Mapped[Optional[int]] = mapped_column(ForeignKey("extracted_records.id", ondelete="CASCADE"), nullable=True, index=True)
    rule_code: Mapped[str] = mapped_column(String(64), index=True)
    field: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="error")
    message: Mapped[str] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
