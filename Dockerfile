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
# Install dependencies into system site-packages to avoid venv path issues in Cloud Run
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache-dir .

# Copy application files
COPY . .

# Expose port and set host
EXPOSE 8080
ENV STUDIO_HOST=0.0.0.0
ENV STUDIO_PORT=8080

# Run API using uvicorn directly
CMD ["uvicorn", "studio.api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
