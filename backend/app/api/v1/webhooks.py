"""Outbound webhooks for ERP / external integration."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.config import settings
from ...db.session import get_db
from ...models import ExtractedRecord
from ...utils.cache import cache

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

WEBHOOK_KEY = "webhooks:list"


class WebhookIn(BaseModel):
    name: str
    url: str
    event: str = "document.completed"  # or record.approved, etc.
    headers: Optional[Dict[str, str]] = None


@router.get("")
def list_webhooks() -> List[Dict[str, Any]]:
    return cache.get(WEBHOOK_KEY) or []


@router.post("")
def add_webhook(w: WebhookIn):
    items = cache.get(WEBHOOK_KEY) or []
    items.append(w.model_dump())
    cache.set(WEBHOOK_KEY, items)
    return {"ok": True, "count": len(items)}


@router.delete("/{idx}")
def remove_webhook(idx: int):
    items = cache.get(WEBHOOK_KEY) or []
    if idx < 0 or idx >= len(items):
        raise HTTPException(404, "Webhook index out of range")
    items.pop(idx)
    cache.set(WEBHOOK_KEY, items)
    return {"ok": True}


@router.post("/test/{idx}")
def test_webhook(idx: int):
    items = cache.get(WEBHOOK_KEY) or []
    if idx < 0 or idx >= len(items):
        raise HTTPException(404)
    w = items[idx]
    body = {"event": "test", "at": datetime.utcnow().isoformat(),
            "app": settings.app_name}
    try:
        r = httpx.post(w["url"], headers=w.get("headers") or {}, json=body,
                       timeout=settings.webhook_timeout_sec)
        return {"status_code": r.status_code, "body": r.text[:500]}
    except Exception as e:
        raise HTTPException(502, str(e))
