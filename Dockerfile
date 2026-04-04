# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: DOCKERFILE | Version: 1.0.0
# WHERE: Dockerfile
# WHY: Rule 18 Cloud-Native Mandate
# HOW: Python 3.11-slim + Multi-Stage Prep
# ==========================================================

FROM python:3.11-slim

# Rule 14: Infrastructure immunity - prevent bloated image
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app

WORKDIR /app

# Install system dependencies (for potential C-extensions or tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Rule 18: Cloud Run binds to $PORT
EXPOSE 8080

# Mandatory 6W initialization on startup
CMD ["python3", "-m", "tooloo_v4_hub.kernel.hub_api"]
