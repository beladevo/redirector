FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src
WORKDIR /app

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    apk add --no-cache --virtual .build-deps gcc musl-dev && \
    pip install -r requirements.txt && \
    apk del .build-deps && \
    apk add --no-cache curl && \
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared && \
    chmod +x /usr/local/bin/cloudflared && \
    adduser -D -s /bin/sh redirector

COPY --chown=redirector src/ src/
COPY --chown=redirector templates/ templates/
COPY --chown=redirector static/ static/

RUN mkdir -p /app/data /app/logs && chown -R redirector:redirector /app/data /app/logs

USER redirector
EXPOSE 8080 3000
ENTRYPOINT ["python", "-m", "redirector.cli.main"]
CMD ["run", "--redirect-port", "8080", "--dashboard-port", "3000", "--host", "0.0.0.0", "--database", "/app/data/logs.db", "--accept-security-notice"]
