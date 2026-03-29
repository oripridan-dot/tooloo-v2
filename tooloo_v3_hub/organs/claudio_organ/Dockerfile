# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: CLAUDIO_DOCKERFILE_v3.0.0
# WHERE: tooloo_v3_hub/organs/claudio_organ/Dockerfile
# WHY: Federated DSP synthesis with Native Acceleration
# HOW: Python 3.12-Slim + Build-Essential
# ==========================================================

FROM python:3.12-slim

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    make \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Compile the C++ Core (Claudio Studio) - DEFERRED: JUCE headers required
# RUN g++ -O3 -shared -fPIC -o core/libclaudio.so core/ClaudioAudioProcessor.cpp core/ClaudioHNSynthesizer.cpp core/ClaudioAudioEditor.cpp core/ClaudioDecompiler.cpp

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port
EXPOSE 8080

# Command to run the SSE server
CMD ["python", "web_server.py"]
