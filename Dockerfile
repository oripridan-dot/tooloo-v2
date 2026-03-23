FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential && rm -rf /var/lib/apt/lists/*

# Install node for pyright
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*
RUN npm install -g pyright

# Set working directory
WORKDIR /app

# Copy dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn uvicorn google-cloud-firestore

# Copy application files
COPY . .

# Set environment defaults (can be overridden by Cloud Run)
ENV PORT=8080
ENV STUDIO_HOST=0.0.0.0
ENV STUDIO_PORT=8080

# Run API
CMD exec uvicorn studio.api:app --host 0.0.0.0 --port ${PORT} --workers 1
