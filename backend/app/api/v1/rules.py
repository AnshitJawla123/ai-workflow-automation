from typing import List, Optional, Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import ValidationRule
from ...schemas.common import Msg
from ...prompts import render
from ...services.llm.openrouter import openrouter, LLMUnavailable

router = APIRouter(prefix="/rules", tags=["rules"])


class RuleIn(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    field: Optional[str] = None
    rule_type: str
    params: Optional[Dict[str, Any]] = None
    severity: str = "error"
    enabled: bool = True


class RuleOut(RuleIn):
    id: int

    class Config:
        from_attributes = True


@router.get("", response_model=List[RuleOut])
def list_rules(db: Session = Depends(get_db)):
    return db.query(ValidationRule).order_by(ValidationRule.id).all()


@router.post("", response_model=RuleOut)
def create_rule(payload: RuleIn, db: Session = Depends(get_db)):
    if db.query(ValidationRule).filter(ValidationRule.code == payload.code).first():
        raise HTTPException(409, "Rule code already exists")
    r = ValidationRule(**payload.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return r


@router.patch("/{rule_id}", response_model=RuleOut)
def update_rule(rule_id: int, payload: RuleIn, db: Session = Depends(get_db)):
    r = db.get(ValidationRule, rule_id)
    if not r:
        raise HTTPException(404, "Not found")
    for k, v in payload.model_dump().items():
        setattr(r, k, v)
    db.commit(); db.refresh(r)
    return r


@router.delete("/{rule_id}", response_model=Msg)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    r = db.get(ValidationRule, rule_id)
    if not r:
        raise HTTPException(404, "Not found")
    db.delete(r); db.commit()
    return Msg(message="Deleted")


class SynthesizeIn(BaseModel):
    text: str


@router.post("/synthesize", response_model=RuleOut)
def synthesize(payload: SynthesizeIn, db: Session = Depends(get_db)):
    """LLM-powered rule synthesis from natural language."""
    prompt = render("04_validation_rule_synthesis") + f"\n\n## Input\n{payload.text}\n"
    try:
        out = openrouter.text_complete(prompt, json_only=True)
    except LLMUnavailable as e:
        raise HTTPException(503, f"LLM unavailable: {e}")
    if not isinstance(out, dict) or "rule_type" not in out:
        raise HTTPException(422, "Could not synthesize rule")
    if db.query(ValidationRule).filter(ValidationRule.code == out.get("code")).first():
        out["code"] = out["code"] + "_v2"
    rule = ValidationRule(**{k: out.get(k) for k in
                              ["code", "name", "description", "field", "rule_type", "params", "severity"]
                              if k in out})
    rule.enabled = True
    db.add(rule); db.commit(); db.refresh(rule)
    return rule
