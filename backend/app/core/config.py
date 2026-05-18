"""Centralized settings (Pydantic v2) loaded from environment / .env."""
from __future__ import annotations

from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "/app/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "AI Workflow Automation"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"
    app_secret_key: str = "change-me-please-32-chars-minimum-secret"
    app_public_url: str = "http://localhost:8000"

    # Storage / DB
    database_url: str = "sqlite:///./data/app.db"
    data_dir: str = "./data"
    upload_dir: str = "./data/uploads"
    export_dir: str = "./data/exports"
    chroma_dir: str = "./data/chroma"
    graph_dir: str = "./data/graph"

    # Auth
    jwt_algo: str = "HS256"
    jwt_expires_minutes: int = 720
    bootstrap_admin_email: str = "admin@local.dev"
    bootstrap_admin_password: str = "admin123"

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_vision_models: str = (
        "google/gemma-4-31b-it:free,"
        "google/gemma-4-26b-a4b-it:free,"
        "nvidia/nemotron-nano-12b-v2-vl:free,"
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    )
    openrouter_text_models: str = (
        "qwen/qwen3-next-80b-a3b-instruct:free,"
        "deepseek/deepseek-v4-flash:free,"
        "openai/gpt-oss-120b:free,"
        "z-ai/glm-4.5-air:free"
    )

    # Gemini (Google AI Studio) — best free vision quality
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_vision_models: str = "gemini-flash-latest,gemini-2.5-flash,gemini-3-flash-preview,gemini-2.0-flash"
    gemini_text_models: str = "gemini-flash-latest,gemini-2.5-flash"

    # Groq — fastest free LLM (Llama-4 Scout vision-enabled)
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_vision_models: str = "meta-llama/llama-4-scout-17b-16e-instruct,meta-llama/llama-4-maverick-17b-128e-instruct"
    groq_text_models: str = "llama-3.3-70b-versatile,llama-3.1-8b-instant"

    # Together AI — $5 free credit
    together_api_key: str = ""
    together_base_url: str = "https://api.together.xyz/v1"
    together_vision_models: str = "meta-llama/Llama-Vision-Free,Qwen/Qwen2-VL-72B-Instruct"
    together_text_models: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"

    # Local Ollama — unlimited self-hosted vision
    ollama_base_url: str = ""
    ollama_vision_models: str = "qwen2-vl:7b,llava:13b"
    ollama_text_models: str = "qwen2.5:7b,llama3.1:8b"

    # Multi-provider consensus
    consensus_top_n: int = 3        # Call top-N enabled vision providers in parallel
    consensus_min_agreement: int = 2  # 2+ providers must agree for high confidence

    # ---- Multi-tenant / public-demo controls ----
    allow_anonymous: bool = True
    workspace_cookie_days: int = 90
    workspace_doc_limit: int = 50
    workspace_storage_bytes: int = 52428800   # 50 MB per workspace

    # Hugging Face
    hf_api_token: str = ""
    hf_base_url: str = "https://api-inference.huggingface.co/models"
    hf_ocr_model: str = "microsoft/trocr-large-handwritten"
    hf_table_model: str = "microsoft/table-transformer-structure-recognition"

    # Embeddings (local)
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Pipeline
    pipeline_max_workers: int = 2
    pipeline_timeout_sec: int = 120
    ocr_provider: str = "auto"
    llm_temperature: float = 0.1
    llm_max_retries: int = 4
    llm_cache_enabled: bool = True

    # Confidence
    conf_green_min: float = 0.85
    conf_yellow_min: float = 0.60

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # SMTP / Webhooks
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = "noreply@local"
    webhook_timeout_sec: int = 10

    # ---- Derived helpers ----
    @property
    def vision_models(self) -> List[str]:
        return [m.strip() for m in self.openrouter_vision_models.split(",") if m.strip()]

    @property
    def text_models(self) -> List[str]:
        return [m.strip() for m in self.openrouter_text_models.split(",") if m.strip()]

    @property
    def cors_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        for p in [self.data_dir, self.upload_dir, self.export_dir, self.chroma_dir, self.graph_dir]:
            Path(p).mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
