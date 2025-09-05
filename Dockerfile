# syntax=docker/dockerfile:1.6
FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy only requirements first for better caching
COPY requirements.txt .

# Install dependencies directly (no separate venv needed in container)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-deps --upgrade pip && \
    pip install -r requirements.txt

# Create non-root user
RUN addgroup -S redirector && adduser -S redirector -G redirector

# Copy application code
COPY --chown=redirector:redirector src/ ./src/
COPY --chown=redirector:redirector templates/ ./templates/
COPY --chown=redirector:redirector static/ ./static/

# Create data directory
RUN mkdir -p /app/data && chown redirector:redirector /app/data

USER redirector

EXPOSE 8080 3000

ENTRYPOINT ["python", "-m", "redirector.cli.main"]
CMD ["run", "--redirect-port", "8080", "--dashboard-port", "3000", "--database", "/app/data/logs.db", "--accept-security-notice"]
