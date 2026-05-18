"""Multi-provider LLM registry.

Order of preference (first one with credentials wins):
  1. Ollama (local, fully free, unlimited)        — OLLAMA_BASE_URL set
  2. Groq (free 30 req/min, fast)                  — GROQ_API_KEY set
  3. Google AI Studio Gemini (free 15 req/min)     — GEMINI_API_KEY set
  4. Together AI ($5 free credit)                  — TOGETHER_API_KEY set
  5. OpenRouter free tier (heavily rate-limited)   — OPENROUTER_API_KEY set

All providers expose the same interface:
    .vision_extract(image_path, prompt, json_only=True) -> dict
    .text_complete(prompt, json_only=True) -> Any

This module wraps the existing OpenRouterClient and adds parallel clients for the
other providers, plus a `pick_provider(kind)` helper that returns the most-preferred
working provider for the requested capability.
"""
from __future__ import annotations

import logging
import hashlib
import os
import time
from typing import Any, Dict, List, Optional

import httpx

from ...core.config import settings
from ...utils.cache import cache
from ...utils.files import image_to_data_url
from ...utils.json_extract import extract_json
from .openrouter import openrouter, LLMUnavailable

log = logging.getLogger("llm.providers")


# ---------- Base helpers ----------
class _OpenAICompatClient:
    """Generic OpenAI-compatible chat completions client (Groq, Together, OpenRouter)."""
    name = "openai-compat"
    base_url: str = ""
    api_key: str = ""
    vision_models: List[str] = []
    text_models: List[str] = []
    supports_response_format: bool = True

    def __init__(self):
        self._client = httpx.Client(timeout=httpx.Timeout(90.0, connect=10.0))

    def enabled(self) -> bool:
        return bool(self.api_key) and bool(self.base_url)

    def _post(self, body: dict) -> str:
        r = self._client.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=body,
        )
        if r.status_code >= 400:
            log.warning("%s %s -> %s %s", self.name, body.get("model"), r.status_code, r.text[:200])
            r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def vision_extract(self, image_path: str, prompt: str, json_only: bool = True,
                       cache_key_extra: str = "") -> Dict[str, Any]:
        if not self.vision_models:
            raise LLMUnavailable(f"{self.name} has no vision models configured")
        img_hash = hashlib.sha1(open(image_path, "rb").read()).hexdigest()[:16]
        ck = f"{self.name}:vision:{img_hash}:{hashlib.sha1((prompt+cache_key_extra).encode()).hexdigest()[:12]}"
        if settings.llm_cache_enabled:
            cached = cache.get(ck)
            if cached is not None:
                return cached
        data_url = image_to_data_url(image_path)
        last_err: Optional[Exception] = None
        for model in self.vision_models:
            body = {
                "model": model,
                "temperature": settings.llm_temperature,
                "messages": [
                    {"role": "system", "content": "You are a precise structured-extraction assistant. Respond with JSON only."},
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ]},
                ],
            }
            if json_only and self.supports_response_format:
                body["response_format"] = {"type": "json_object"}
            try:
                txt = self._post(body)
                obj = extract_json(txt) if json_only else txt
                if obj is None:
                    raise ValueError("non-JSON")
                if settings.llm_cache_enabled:
                    cache.set(ck, obj, ttl_sec=60 * 60 * 24 * 7)
                return obj
            except Exception as e:
                last_err = e
                log.warning("%s vision model %s failed: %s", self.name, model, e)
                continue
        raise LLMUnavailable(f"{self.name}: all vision models failed: {last_err}")

    def text_complete(self, prompt: str, json_only: bool = True) -> Any:
        if not self.text_models:
            raise LLMUnavailable(f"{self.name} has no text models configured")
        ck = f"{self.name}:text:{hashlib.sha1(prompt.encode()).hexdigest()[:16]}"
        if settings.llm_cache_enabled:
            cached = cache.get(ck)
            if cached is not None:
                return cached
        last_err: Optional[Exception] = None
        for model in self.text_models:
            body = {
                "model": model,
                "temperature": settings.llm_temperature,
                "messages": [
                    {"role": "system", "content": "You respond with strict JSON when asked."},
                    {"role": "user", "content": prompt},
                ],
            }
            if json_only and self.supports_response_format:
                body["response_format"] = {"type": "json_object"}
            try:
                txt = self._post(body)
                out = extract_json(txt) if json_only else txt
                if json_only and out is None:
                    raise ValueError("non-JSON")
                if settings.llm_cache_enabled:
                    cache.set(ck, out, ttl_sec=60 * 60 * 24)
                return out
            except Exception as e:
                last_err = e
                log.warning("%s text model %s failed: %s", self.name, model, e)
                continue
        raise LLMUnavailable(f"{self.name}: all text models failed: {last_err}")


# ---------- Concrete providers ----------
class GroqClient(_OpenAICompatClient):
    name = "groq"
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        self.vision_models = [m.strip() for m in os.getenv(
            "GROQ_VISION_MODELS",
            "meta-llama/llama-4-scout-17b-16e-instruct,meta-llama/llama-4-maverick-17b-128e-instruct"
        ).split(",") if m.strip()]
        self.text_models = [m.strip() for m in os.getenv(
            "GROQ_TEXT_MODELS",
            "llama-3.3-70b-versatile,llama-3.1-8b-instant,gemma2-9b-it"
        ).split(",") if m.strip()]


class TogetherClient(_OpenAICompatClient):
    name = "together"
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("TOGETHER_API_KEY", "")
        self.base_url = os.getenv("TOGETHER_BASE_URL", "https://api.together.xyz/v1")
        self.vision_models = [m.strip() for m in os.getenv(
            "TOGETHER_VISION_MODELS",
            "meta-llama/Llama-Vision-Free,Qwen/Qwen2-VL-72B-Instruct"
        ).split(",") if m.strip()]
        self.text_models = [m.strip() for m in os.getenv(
            "TOGETHER_TEXT_MODELS",
            "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free,meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
        ).split(",") if m.strip()]


class GeminiClient:
    """Google AI Studio (Gemini) — uses its own REST endpoint, not OpenAI-compatible."""
    name = "gemini"
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.base_url = os.getenv(
            "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
        ).rstrip("/")
        self.vision_models = [m.strip() for m in os.getenv(
            "GEMINI_VISION_MODELS",
            "gemini-flash-latest,gemini-2.5-flash,gemini-3-flash-preview,gemini-2.0-flash"
        ).split(",") if m.strip()]
        self.text_models = self.vision_models  # Gemini models are multimodal
        self._client = httpx.Client(timeout=httpx.Timeout(90.0, connect=10.0))

    def enabled(self) -> bool:
        return bool(self.api_key)

    def _call(self, model: str, contents: list) -> str:
        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        body = {"contents": contents, "generationConfig": {"temperature": settings.llm_temperature,
                                                            "responseMimeType": "application/json"}}
        r = self._client.post(url, json=body)
        if r.status_code >= 400:
            log.warning("gemini %s -> %s %s", model, r.status_code, r.text[:200])
            r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def vision_extract(self, image_path: str, prompt: str, json_only: bool = True,
                       cache_key_extra: str = "") -> Dict[str, Any]:
        img_hash = hashlib.sha1(open(image_path, "rb").read()).hexdigest()[:16]
        ck = f"gemini:vision:{img_hash}:{hashlib.sha1((prompt+cache_key_extra).encode()).hexdigest()[:12]}"
        if settings.llm_cache_enabled:
            cached = cache.get(ck)
            if cached is not None:
                return cached
        import base64
        img_b64 = base64.b64encode(open(image_path, "rb").read()).decode("ascii")
        contents = [{"role": "user", "parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
        ]}]
        last_err: Optional[Exception] = None
        for model in self.vision_models:
            try:
                txt = self._call(model, contents)
                obj = extract_json(txt) if json_only else txt
                if obj is None:
                    raise ValueError("non-JSON")
                if settings.llm_cache_enabled:
                    cache.set(ck, obj, ttl_sec=60 * 60 * 24 * 7)
                return obj
            except Exception as e:
                last_err = e
                log.warning("gemini %s failed: %s", model, e)
                continue
        raise LLMUnavailable(f"gemini failed: {last_err}")

    def text_complete(self, prompt: str, json_only: bool = True) -> Any:
        ck = f"gemini:text:{hashlib.sha1(prompt.encode()).hexdigest()[:16]}"
        if settings.llm_cache_enabled:
            cached = cache.get(ck)
            if cached is not None:
                return cached
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        last_err = None
        for model in self.text_models:
            try:
                txt = self._call(model, contents)
                out = extract_json(txt) if json_only else txt
                if json_only and out is None:
                    raise ValueError("non-JSON")
                if settings.llm_cache_enabled:
                    cache.set(ck, out, ttl_sec=60 * 60 * 24)
                return out
            except Exception as e:
                last_err = e
                log.warning("gemini text %s failed: %s", model, e)
        raise LLMUnavailable(f"gemini text failed: {last_err}")


class OllamaClient:
    """Local Ollama — fully free, unlimited. http://localhost:11434"""
    name = "ollama"
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "")
        self.vision_models = [m.strip() for m in os.getenv(
            "OLLAMA_VISION_MODELS", "llama3.2-vision:11b,llava:13b,qwen2-vl:7b"
        ).split(",") if m.strip()]
        self.text_models = [m.strip() for m in os.getenv(
            "OLLAMA_TEXT_MODELS", "llama3.1:8b,qwen2.5:7b,mistral:7b"
        ).split(",") if m.strip()]
        self._client = httpx.Client(timeout=httpx.Timeout(180.0, connect=5.0))

    def enabled(self) -> bool:
        if not self.base_url:
            return False
        try:
            r = self._client.get(f"{self.base_url}/api/tags", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def _chat(self, model: str, messages: list) -> str:
        body = {"model": model, "messages": messages, "stream": False,
                "options": {"temperature": settings.llm_temperature}, "format": "json"}
        r = self._client.post(f"{self.base_url}/api/chat", json=body)
        if r.status_code >= 400:
            log.warning("ollama %s -> %s %s", model, r.status_code, r.text[:200])
            r.raise_for_status()
        return r.json()["message"]["content"]

    def vision_extract(self, image_path: str, prompt: str, json_only: bool = True,
                       cache_key_extra: str = "") -> Dict[str, Any]:
        import base64
        img_b64 = base64.b64encode(open(image_path, "rb").read()).decode("ascii")
        img_hash = hashlib.sha1(open(image_path, "rb").read()).hexdigest()[:16]
        ck = f"ollama:vision:{img_hash}:{hashlib.sha1((prompt+cache_key_extra).encode()).hexdigest()[:12]}"
        if settings.llm_cache_enabled:
            cached = cache.get(ck)
            if cached is not None:
                return cached
        msgs = [{"role": "user", "content": prompt, "images": [img_b64]}]
        last_err = None
        for model in self.vision_models:
            try:
                txt = self._chat(model, msgs)
                obj = extract_json(txt) if json_only else txt
                if obj is None:
                    raise ValueError("non-JSON")
                if settings.llm_cache_enabled:
                    cache.set(ck, obj, ttl_sec=60 * 60 * 24 * 7)
                return obj
            except Exception as e:
                last_err = e
                log.warning("ollama %s vision failed: %s", model, e)
        raise LLMUnavailable(f"ollama vision failed: {last_err}")

    def text_complete(self, prompt: str, json_only: bool = True) -> Any:
        ck = f"ollama:text:{hashlib.sha1(prompt.encode()).hexdigest()[:16]}"
        if settings.llm_cache_enabled:
            cached = cache.get(ck)
            if cached is not None:
                return cached
        msgs = [{"role": "user", "content": prompt}]
        last_err = None
        for model in self.text_models:
            try:
                txt = self._chat(model, msgs)
                out = extract_json(txt) if json_only else txt
                if json_only and out is None:
                    raise ValueError("non-JSON")
                if settings.llm_cache_enabled:
                    cache.set(ck, out, ttl_sec=60 * 60 * 24)
                return out
            except Exception as e:
                last_err = e
                log.warning("ollama %s text failed: %s", model, e)
        raise LLMUnavailable(f"ollama text failed: {last_err}")


# ---------- Wrapper for the original openrouter client to match interface ----------
class OpenRouterWrapper:
    name = "openrouter"
    def enabled(self) -> bool:
        return bool(settings.openrouter_api_key)
    def vision_extract(self, image_path: str, prompt: str, json_only: bool = True,
                       cache_key_extra: str = "") -> Dict[str, Any]:
        return openrouter.vision_extract(image_path, prompt, json_only=json_only,
                                          cache_key_extra=cache_key_extra)
    def text_complete(self, prompt: str, json_only: bool = True) -> Any:
        return openrouter.text_complete(prompt, json_only=json_only)


# ---------- Registry ----------
# Groq prioritized over OpenRouter because OpenRouter free is per-day quotas
# while Groq free is per-minute (much more usable on a bursty workload).
_PROVIDER_ORDER = [
    ("ollama",     OllamaClient),    # local, unlimited
    ("gemini",     GeminiClient),    # best vision quality (free 15 RPM)
    ("groq",       GroqClient),      # fastest text + good vision (free 30 RPM)
    ("together",   TogetherClient),  # $5 credit
    ("openrouter", OpenRouterWrapper),  # last resort
]
_instances: Dict[str, Any] = {}


def _instance(name: str):
    if name not in _instances:
        for n, cls in _PROVIDER_ORDER:
            if n == name:
                _instances[name] = cls()
                break
    return _instances[name]


def all_providers() -> List[Dict[str, Any]]:
    out = []
    for n, _ in _PROVIDER_ORDER:
        inst = _instance(n)
        out.append({"name": n, "enabled": inst.enabled()})
    return out


def enabled_providers() -> List[str]:
    return [p["name"] for p in all_providers() if p["enabled"]]


def pick(kind: str = "vision") -> Optional[Any]:
    """Return the first provider instance whose `kind` capability is available.
       kind: "vision" or "text"
    """
    for n, _ in _PROVIDER_ORDER:
        inst = _instance(n)
        if not inst.enabled():
            continue
        if kind == "vision" and getattr(inst, "vision_models", None) == []:
            continue
        return inst
    return None


def call_vision(image_path: str, prompt: str, json_only: bool = True,
                cache_key_extra: str = "") -> Dict[str, Any]:
    """Try every enabled provider in order until one succeeds."""
    last_err: Optional[Exception] = None
    for n, _ in _PROVIDER_ORDER:
        inst = _instance(n)
        if not inst.enabled():
            continue
        try:
            log.info("vision try provider=%s", n)
            return inst.vision_extract(image_path, prompt, json_only=json_only,
                                       cache_key_extra=cache_key_extra)
        except Exception as e:
            last_err = e
            log.warning("provider=%s vision failed: %s", n, e)
    raise LLMUnavailable(f"All vision providers failed; last: {last_err}")


def call_text(prompt: str, json_only: bool = True) -> Any:
    last_err: Optional[Exception] = None
    for n, _ in _PROVIDER_ORDER:
        inst = _instance(n)
        if not inst.enabled():
            continue
        try:
            log.info("text try provider=%s", n)
            return inst.text_complete(prompt, json_only=json_only)
        except Exception as e:
            last_err = e
            log.warning("provider=%s text failed: %s", n, e)
    raise LLMUnavailable(f"All text providers failed; last: {last_err}")
