# syntax=docker/dockerfile:1.6

# ---------- Build (deps -> venv) ----------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .

# Build venv with cached pip dir (valid BuildKit --mount usage)
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# ---------- Runtime ----------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    DATABASE_PATH=/app/data/logs.db \
    HOST=0.0.0.0 \
    LOG_LEVEL=info

# Non-root user (Debian slim has adduser/addgroup)
RUN addgroup --system redirector && adduser --system --ingroup redirector redirector

WORKDIR /app

# Bring in venv first for better layer reuse
COPY --from=builder /opt/venv /opt/venv

# App code (no dev/test/docs to keep image small; use .dockerignore too)
COPY src/ ./src/
COPY templates/ ./templates/
COPY static/ ./static/

# Data & logs
RUN mkdir -p /app/data /app/logs && chown -R redirector:redirector /app
USER redirector

# Healthcheck (no curl; no heredoc)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; \
    r=urllib.request.urlopen('http://localhost:3000/health',timeout=5); \
    sys.exit(0 if r.status==200 else 1)" || exit 1

EXPOSE 8080 3000

ENTRYPOINT ["python","-m","redirector.cli.main"]
CMD ["run","--redirect-port","8080","--dashboard-port","3000","--database","/app/data/logs.db","--accept-security-notice"]
