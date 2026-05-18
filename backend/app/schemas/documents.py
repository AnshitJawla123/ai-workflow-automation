from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    uuid: str
    filename: str
    mime_type: str
    size_bytes: int
    status: str
    progress: float
    error: Optional[str] = None
    doc_type: str
    page_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FieldValueOut(BaseModel):
    id: int
    field_name: str
    raw_value: Optional[str]
    normalized_value: Optional[str]
    confidence: float
    source: str
    edited: bool
    bbox: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None

    class Config:
        from_attributes = True


class RecordOut(BaseModel):
    id: int
    document_id: int
    row_index: int
    page_number: int
    date: Optional[str]
    shift: Optional[str]
    employee_no: Optional[str]
    operation_code: Optional[str]
    machine_no: Optional[str]
    work_order_no: Optional[str]
    quantity_produced: Optional[float]
    time_taken_hours: Optional[float]
    overall_confidence: float
    review_status: str
    notes: Optional[str] = None
    field_values: List[FieldValueOut] = []

    class Config:
        from_attributes = True


class RecordUpdate(BaseModel):
    date: Optional[str] = None
    shift: Optional[str] = None
    employee_no: Optional[str] = None
    operation_code: Optional[str] = None
    machine_no: Optional[str] = None
    work_order_no: Optional[str] = None
    quantity_produced: Optional[float] = None
    time_taken_hours: Optional[float] = None
    review_status: Optional[str] = None
    notes: Optional[str] = None


class ValidationIssueOut(BaseModel):
    id: int
    document_id: int
    record_id: Optional[int]
    rule_code: str
    field: Optional[str]
    severity: str
    message: str
    resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentDetail(DocumentOut):
    records: List[RecordOut] = []
    issues: List[ValidationIssueOut] = []
