# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MEMORY_DOCKERFILE_v3.0.0
# WHERE: tooloo_v3_hub/organs/memory_organ/Dockerfile
# WHY: Immutable Cloud Run Deployment
# HOW: Python 3.12-Slim
# ==========================================================

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port
EXPOSE 8080

# Command to run the SSE server
CMD ["python", "web_server.py"]
