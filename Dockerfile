# syntax=docker/dockerfile:1

# Milestone 2 (Docker Image) of docs/remote_mcp_deployment_prd.md.
#
# Two stages: `builder` resolves and installs the locked dependency set plus
# the project itself into a venv using uv; `runtime` copies only that venv
# and the source tree into a minimal, non-root image. Development
# dependencies (ruff, mypy, pytest, ...) are never installed here.

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

RUN pip install --no-cache-dir uv

# Dependencies are installed from the lockfile before the source tree is
# copied in, so editing application code does not invalidate this layer.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --no-editable

COPY src ./src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

WORKDIR /app

# Runs as a dedicated non-root user; no shell/home directory is required.
RUN groupadd --system app \
    && useradd --system --gid app --no-create-home --shell /usr/sbin/nologin app

COPY --from=builder --chown=app:app /app/.venv ./.venv
COPY --from=builder --chown=app:app /app/src ./src

USER app

EXPOSE 8000

# Liveness only — never calls Semantic Scholar or arXiv (see /health in
# src/research_intelligence_mcp/mcp/tools/health.py). Uses the stdlib so no
# extra HTTP client needs to be installed in the runtime image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

# Exec form (not shell form) so SIGTERM from `docker stop` / ECS reaches this
# process directly instead of being absorbed by an intermediate shell.
CMD ["python", "-m", "research_intelligence_mcp"]
