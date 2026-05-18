"""Read-only settings + prompts inspection (settings UI)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...core.config import settings
from ...prompts import all_prompts, PROMPTS_DIR
from ...services.llm import providers as llm_providers
from ..deps import optional_user

router = APIRouter(prefix="/settings", tags=["meta"])


@router.get("")
def get_settings():
    # Never expose secrets
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "vision_models": settings.vision_models,
        "text_models": settings.text_models,
        "ocr_provider": settings.ocr_provider,
        "embed_model": settings.embed_model,
        "conf_green_min": settings.conf_green_min,
        "conf_yellow_min": settings.conf_yellow_min,
        "has_openrouter_key": bool(settings.openrouter_api_key),
        "has_hf_token": bool(settings.hf_api_token),
        "llm_providers": llm_providers.all_providers(),
        "enabled_providers": llm_providers.enabled_providers(),
    }


@router.get("/providers")
def providers():
    return llm_providers.all_providers()


@router.get("/prompts")
def list_prompts():
    return all_prompts()


class PromptUpdate(BaseModel):
    content: str


@router.put("/prompts/{name}")
def update_prompt(name: str, payload: PromptUpdate, user=Depends(optional_user)):
    if user and user.role != "admin":
        raise HTTPException(403, "Admin only")
    p = PROMPTS_DIR / f"{name}.md"
    if not p.exists():
        raise HTTPException(404, "Prompt not found")
    p.write_text(payload.content, encoding="utf-8")
    return {"ok": True, "name": name, "bytes": p.stat().st_size}
