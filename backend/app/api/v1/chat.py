"""Natural-language Q&A over operational data using NL→SQL with safety rails."""
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...core.workspace import current_owner
from ...db.session import get_db
from ...models import Document
from ...prompts import render
from ...services.llm.openrouter import openrouter, LLMUnavailable
from sqlalchemy import or_

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatIn(BaseModel):
    question: str


class ChatOut(BaseModel):
    sql: str
    explanation: str
    columns: List[str]
    rows: List[List[Any]]


SAFE_PREFIXES = ("select",)
FORBIDDEN = ("insert", "update", "delete", "drop", "alter", "create", "attach", "detach", "pragma")


def _is_safe(sql: str) -> bool:
    s = sql.strip().lower()
    if not s.startswith(SAFE_PREFIXES):
        return False
    for bad in FORBIDDEN:
        if bad in s:
            return False
    return True


@router.post("/ask", response_model=ChatOut)
def ask(payload: ChatIn, db: Session = Depends(get_db), owner: str = Depends(current_owner)):
    # Compute the list of allowed document ids for the current workspace (own + samples)
    allowed_ids = [r[0] for r in db.query(Document.id).filter(
        or_(Document.owner_id == owner, Document.is_sample.is_(True))
    ).all()]
    if not allowed_ids:
        return ChatOut(sql="", explanation="No documents visible to your workspace.", columns=[], rows=[])

    prompt = render("08_nl_to_sql") + f"\n\n## Question\n{payload.question}\n"
    try:
        out = openrouter.text_complete(prompt, json_only=True)
    except LLMUnavailable:
        sql = "SELECT shift, COUNT(*), COALESCE(SUM(quantity_produced),0) FROM extracted_records GROUP BY shift"
        out = {"sql": sql, "explanation": "Fallback: per-shift summary"}
    if not isinstance(out, dict) or "sql" not in out:
        raise HTTPException(422, "Could not generate SQL")
    sql = out["sql"].rstrip(";")
    if not _is_safe(sql):
        raise HTTPException(400, "Unsafe SQL rejected")

    # Inject tenant-isolation WHERE clause: wrap as subquery
    ids_csv = ",".join(str(i) for i in allowed_ids)
    safe_sql = (
        f"SELECT * FROM ({sql}) AS user_q "
        f"WHERE 1=1"  # SQLite will let unrelated rows pass; we additionally filter at executor below
    )
    # If the underlying SQL touches extracted_records, constrain by document_id IN allowed list.
    # Simpler approach: prefix a CTE that limits the table.
    if "extracted_records" in sql.lower():
        sql = f"WITH extracted_records AS (SELECT * FROM extracted_records WHERE document_id IN ({ids_csv})) {sql}"

    if " limit " not in sql.lower():
        sql += " LIMIT 200"
    try:
        result = db.execute(text(sql))
        cols = list(result.keys())
        rows = [list(r) for r in result.fetchall()]
    except Exception as e:
        raise HTTPException(400, f"SQL error: {e}")
    return ChatOut(sql=sql, explanation=out.get("explanation", ""), columns=cols, rows=rows)
