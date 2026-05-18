"""FastAPI application entrypoint."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

# Load .env BEFORE other imports so any module using os.getenv() sees the values.
try:
    from dotenv import load_dotenv
    for candidate in (".env", "../.env", "/app/.env", str(Path(__file__).resolve().parents[2] / ".env")):
        if Path(candidate).exists():
            load_dotenv(candidate, override=False)
            break
except ImportError:
    pass  # python-dotenv optional — pydantic-settings handles its own load

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .core.logging import setup_logging
from .db.bootstrap import bootstrap
from .db.session import SessionLocal, init_db
from .services.jobs.runner import runner

setup_logging(settings.app_log_level)
log = logging.getLogger("main")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AI-powered workflow automation for digitising handwritten operational documents.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS for separate-frontend dev mode
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Routers ----
from .api.v1 import (auth, upload, documents, review, rules, search,
                     dashboard, analytics, chat, export, ws, health,
                     selftest, audit, settings_api, webhooks, workspace)

API_PREFIX = "/api/v1"
for r in [health.router, auth.router, upload.router, documents.router, review.router,
          rules.router, search.router, dashboard.router, analytics.router, chat.router,
          export.router, ws.router, selftest.router, audit.router,
          settings_api.router, webhooks.router, workspace.router]:
    app.include_router(r, prefix=API_PREFIX)


# ---- Lifecycle ----
@app.on_event("startup")
async def on_startup():
    log.info("starting %s env=%s", settings.app_name, settings.app_env)
    init_db()
    with SessionLocal() as db:
        bootstrap(db)
    # Wire pipeline handler
    from .workflows.pipeline import process_document
    runner.set_handler(process_document)
    runner.start()
    log.info("ready on %s:%s", settings.app_host, settings.app_port)


# ---- Static frontend (built into /static at build time) ----
_static_dir = Path(__file__).parent / "static"
if _static_dir.exists() and (_static_dir / "index.html").exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir), html=True), name="static")

    @app.get("/", include_in_schema=False)
    async def root():
        return HTMLResponse((_static_dir / "index.html").read_text())
else:
    @app.get("/", include_in_schema=False)
    async def root():
        return JSONResponse({
            "app": settings.app_name,
            "version": "1.0.0",
            "docs": "/api/docs",
            "health": "/api/v1/health",
            "frontend": "Build the frontend (make build) to serve UI here.",
        })
