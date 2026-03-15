# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.13-slim AS builder
WORKDIR /app

# Install uv (FastAPI-recommended package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency manifests first (cache layer)
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual env
RUN uv sync --frozen --no-install-project

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Activate venv
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Use exec form for graceful shutdown
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
