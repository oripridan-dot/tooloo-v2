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

# Copy python configuration
COPY pyproject.toml uv.lock* ./

# Install uv and sync dependencies (avoids needing a requirements.txt)
RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-install-project || uv sync --no-install-project

# Copy application files
COPY . .

# Set environment defaults (can be overridden by Cloud Run)
ENV PORT=8080
ENV STUDIO_HOST=0.0.0.0
ENV STUDIO_PORT=8080

# Run API using uv
CMD exec uv run uvicorn studio.api:app --host 0.0.0.0 --port ${PORT} --workers 1
