FROM python:3.11-slim

WORKDIR /app

# OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Deps — single install from requirements only (no inline pip duplication)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Non-root user — Cloud Run security best practice
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=/app

# Cloud Run port
EXPOSE 8080

# Readiness probe — Cloud Run uses this to know when the container is healthy
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "tooloo_v4_hub/portal/sovereign_api.py"]
