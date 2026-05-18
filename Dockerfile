# =============================================================================
# AI Workflow Automation - Single-container deployment
# Includes Python backend + static React SPA (no node build required at runtime)
# Build:  docker build -t ai-workflow:latest .
# Run:    docker run -p 8000:8000 -v $(pwd)/data:/app/data ai-workflow:latest
# =============================================================================
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System packages: poppler for pdf2image, tesseract for OCR fallback, opencv runtime libs
RUN apt-get update && apt-get install -y --no-install-recommends \
      poppler-utils \
      tesseract-ocr \
      libgl1 \
      libglib2.0-0 \
      curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt 'bcrypt==4.0.1' email-validator

COPY backend /app/backend
COPY samples /app/samples

# Pre-create data dir
RUN mkdir -p /app/data/uploads /app/data/exports /app/data/chroma /app/data/graph

ENV DATA_DIR=/app/data \
    UPLOAD_DIR=/app/data/uploads \
    EXPORT_DIR=/app/data/exports \
    CHROMA_DIR=/app/data/chroma \
    GRAPH_DIR=/app/data/graph \
    DATABASE_URL=sqlite:////app/data/app.db \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/v1/health || exit 1

WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
