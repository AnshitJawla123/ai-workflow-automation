"""OpenRouter client supporting:
- Vision (image_url multipart) + text completion
- Free-model rotation with circuit breaker
- SQLite cache by content hash
- Exponential backoff + retries
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ...core.config import settings
from ...utils.cache import cache
from ...utils.files import image_to_data_url
from ...utils.json_extract import extract_json

log = logging.getLogger("llm.openrouter")


class LLMUnavailable(Exception):
    pass


class OpenRouterClient:
    def __init__(self):
        self.base = settings.openrouter_base_url.rstrip("/")
        self.key = settings.openrouter_api_key
        self.vision_models = settings.vision_models
        self.text_models = settings.text_models
        self._client = httpx.Client(
            timeout=httpx.Timeout(60.0, connect=10.0),
            headers={
                "HTTP-Referer": settings.app_public_url,
                "X-Title": settings.app_name,
            },
        )

    # ---------- Public ----------
    def vision_extract(
        self,
        image_path: str,
        prompt: str,
        models: Optional[List[str]] = None,
        json_only: bool = True,
        cache_key_extra: str = "",
    ) -> Dict[str, Any]:
        models = models or self.vision_models
        img_hash = hashlib.sha1(open(image_path, "rb").read()).hexdigest()[:16]
        ck = f"vision:{img_hash}:{hashlib.sha1((prompt+cache_key_extra).encode()).hexdigest()[:12]}"
        if settings.llm_cache_enabled:
            cached = cache.get(ck)
            if cached is not None:
                return cached

        if not self.key:
            raise LLMUnavailable("OPENROUTER_API_KEY not set")

        data_url = image_to_data_url(image_path)
        last_err: Optional[Exception] = None
        for model in models:
            try:
                txt = self._chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a precise structured-extraction assistant. Always respond with JSON only."},
                        {"role": "user", "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ]},
                    ],
                    json_only=json_only,
                )
                obj = extract_json(txt) if json_only else txt
                if obj is None:
                    raise ValueError("LLM did not return JSON")
                if settings.llm_cache_enabled:
                    cache.set(ck, obj, ttl_sec=60 * 60 * 24 * 7)
                return obj
            except Exception as e:
                last_err = e
                log.warning("vision model %s failed: %s", model, e)
                continue
        raise LLMUnavailable(f"All vision models failed: {last_err}")

    def text_complete(self, prompt: str, models: Optional[List[str]] = None, json_only: bool = True) -> Any:
        models = models or self.text_models
        ck = f"text:{hashlib.sha1(prompt.encode()).hexdigest()[:16]}"
        if settings.llm_cache_enabled:
            cached = cache.get(ck)
            if cached is not None:
                return cached
        if not self.key:
            raise LLMUnavailable("OPENROUTER_API_KEY not set")
        last_err: Optional[Exception] = None
        for model in models:
            try:
                txt = self._chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You respond with strict JSON when asked."},
                        {"role": "user", "content": prompt},
                    ],
                    json_only=json_only,
                )
                out = extract_json(txt) if json_only else txt
                if json_only and out is None:
                    raise ValueError("non-JSON")
                if settings.llm_cache_enabled:
                    cache.set(ck, out, ttl_sec=60 * 60 * 24)
                return out
            except Exception as e:
                last_err = e
                log.warning("text model %s failed: %s", model, e)
                continue
        raise LLMUnavailable(f"All text models failed: {last_err}")

    # ---------- Internals ----------
    def _chat(self, model: str, messages: List[Dict[str, Any]], json_only: bool) -> str:
        """Call chat completions with smart retry: backoff on 429 (rate-limit) and 5xx."""
        body = {"model": model, "messages": messages, "temperature": settings.llm_temperature}
        if json_only:
            body["response_format"] = {"type": "json_object"}
        last_err: Optional[Exception] = None
        for attempt in range(settings.llm_max_retries):
            try:
                r = self._client.post(
                    f"{self.base}/chat/completions",
                    headers={"Authorization": f"Bearer {self.key}"},
                    json=body,
                )
                if r.status_code == 429 or r.status_code >= 500:
                    log.warning("openrouter %s -> %s (retry %d): %s",
                                model, r.status_code, attempt + 1, r.text[:120])
                    import time as _t
                    _t.sleep(min(2 ** attempt, 6))
                    last_err = httpx.HTTPStatusError("rate-limited", request=r.request, response=r)
                    continue
                if r.status_code >= 400:
                    log.warning("openrouter %s -> %s %s", model, r.status_code, r.text[:200])
                    r.raise_for_status()
                data = r.json()
                return data["choices"][0]["message"]["content"]
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_err = e
                import time as _t
                _t.sleep(min(2 ** attempt, 6))
                continue
        if last_err:
            raise last_err
        raise RuntimeError("unknown LLM failure")


openrouter = OpenRouterClient()
