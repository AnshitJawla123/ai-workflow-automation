"""Initial DB bootstrap: create admin + default validation rules."""
from sqlalchemy.orm import Session
from ..core.config import settings
from ..core.security import hash_password
from ..models import User, ValidationRule


DEFAULT_RULES = [
    {"code": "REQ_DATE", "name": "Date required", "field": "date", "rule_type": "required", "severity": "error"},
    {"code": "REQ_SHIFT", "name": "Shift required", "field": "shift", "rule_type": "required", "severity": "error"},
    {"code": "REQ_EMP", "name": "Employee No required", "field": "employee_no", "rule_type": "required", "severity": "error"},
    {"code": "REQ_MACHINE", "name": "Machine No required", "field": "machine_no", "rule_type": "required", "severity": "error"},
    {"code": "REQ_WO", "name": "Work Order required", "field": "work_order_no", "rule_type": "required", "severity": "error"},
    {"code": "REQ_QTY", "name": "Quantity required", "field": "quantity_produced", "rule_type": "required", "severity": "error"},
    {"code": "ENUM_SHIFT", "name": "Shift must be I, II or III", "field": "shift",
     "rule_type": "enum", "params": {"values": ["I", "II", "III"]}, "severity": "error"},
    {"code": "REGEX_MACHINE", "name": "Machine code format (MC-XXX)", "field": "machine_no",
     "rule_type": "regex", "params": {"pattern": "^MC-\\d{2,4}$"}, "severity": "warning"},
    {"code": "REGEX_EMP", "name": "Employee No format (BT XXXX)", "field": "employee_no",
     "rule_type": "regex", "params": {"pattern": "^BT\\s?\\d{3,5}$"}, "severity": "warning"},
    {"code": "RANGE_QTY", "name": "Quantity in plausible range 0-10000", "field": "quantity_produced",
     "rule_type": "range", "params": {"min": 0, "max": 10000}, "severity": "warning"},
    {"code": "RANGE_TIME", "name": "Time taken 0-24 hours", "field": "time_taken_hours",
     "rule_type": "range", "params": {"min": 0, "max": 24}, "severity": "error"},
    {"code": "UNIQUE_WO", "name": "Work Order number unique per document",
     "field": "work_order_no", "rule_type": "duplicate", "severity": "warning"},
    {"code": "EXPR_QTY_TIME", "name": "Quantity per hour sanity check",
     "rule_type": "expression",
     "params": {"expression": "(quantity_produced or 0) / max(time_taken_hours or 0.1, 0.1) <= 200"},
     "severity": "info"},
]


def bootstrap(db: Session) -> None:
    # Admin user
    if not db.query(User).filter(User.email == settings.bootstrap_admin_email).first():
        admin = User(
            email=settings.bootstrap_admin_email,
            password_hash=hash_password(settings.bootstrap_admin_password),
            role="admin",
        )
        db.add(admin)

    # Rules
    existing = {r.code for r in db.query(ValidationRule).all()}
    for r in DEFAULT_RULES:
        if r["code"] not in existing:
            db.add(ValidationRule(**r))

    db.commit()
