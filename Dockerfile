# Multi-stage Dockerfile for production deployment
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /build

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Production stage
FROM python:3.11-slim

# Security: Create non-root user
RUN groupadd -r redirector && useradd --no-log-init -r -g redirector redirector

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy wheels and install packages
COPY --from=builder /build/wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy application code
COPY src/ ./src/
COPY templates/ ./templates/
COPY static/ ./static/

# Create data directory for SQLite database
RUN mkdir -p /app/data && chown -R redirector:redirector /app/data

# Create logs directory
RUN mkdir -p /app/logs && chown -R redirector:redirector /app/logs

# Switch to non-root user
USER redirector

# Set environment variables
ENV PYTHONPATH=/app/src
ENV DATABASE_PATH=/app/data/logs.db
ENV HOST=0.0.0.0
ENV LOG_LEVEL=info

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Expose ports
EXPOSE 8080 3000

# Default command
CMD ["python", "-m", "redirector.cli.main", "run", \
     "--redirect-port", "8080", \
     "--dashboard-port", "3000", \
     "--database", "/app/data/logs.db"]