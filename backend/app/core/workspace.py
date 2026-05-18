"""Workspace identity layer — provides multi-tenant isolation.

The owner_id of any resource is:
  - "user:<int_id>"  when an authenticated user is present (JWT)
  - "ws:<uuid>"      when anonymous (browser cookie `awa_workspace`)

Samples (is_sample=True) are visible to everyone.

This is implemented as FastAPI dependencies + a tiny middleware that
ensures every visitor has a workspace cookie.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Cookie, Depends, Request, Response

from ..db.session import SessionLocal
from .config import settings
from .security import decode_token

WORKSPACE_COOKIE = "awa_workspace"
WORKSPACE_COOKIE_MAX_AGE = 60 * 60 * 24 * 90  # 90 days


def _user_from_token(request: Request) -> Optional[int]:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    try:
        payload = decode_token(auth.split(" ", 1)[1])
        return int(payload.get("sub")) if payload and payload.get("sub") else None
    except Exception:
        return None


def get_or_create_workspace(request: Request, response: Response,
                             awa_workspace: Optional[str] = Cookie(default=None)) -> str:
    """Returns the current owner_id. Sets the cookie if anonymous."""
    user_id = _user_from_token(request)
    if user_id:
        return f"user:{user_id}"
    if awa_workspace and awa_workspace.startswith("ws:") and len(awa_workspace) > 8:
        return awa_workspace
    new_ws = f"ws:{uuid.uuid4().hex[:16]}"
    response.set_cookie(
        WORKSPACE_COOKIE, new_ws,
        max_age=WORKSPACE_COOKIE_MAX_AGE,
        httponly=True, samesite="lax",
        secure=settings.app_env == "production",
        path="/",
    )
    return new_ws


def current_owner(owner: str = Depends(get_or_create_workspace)) -> str:
    return owner


def owner_filter(query, model_class, owner_id: str):
    """Apply: WHERE owner_id = <owner> OR is_sample = True (so samples are world-readable)."""
    return query.filter((model_class.owner_id == owner_id) | (model_class.is_sample.is_(True)))
