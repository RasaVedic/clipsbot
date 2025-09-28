# Use official Python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ffmpeg \
      git \
      build-essential \
      libsndfile1 \
      libssl-dev \
      ca-certificates \
      && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt /app/requirements.txt

# Upgrade pip, setuptools, wheel
RUN pip install --upgrade pip setuptools wheel

# Install torch CPU wheel first to avoid heavy builds
RUN pip install "torch==2.2.3+cpu" --index-url https://download.pytorch.org/whl/cpu -f https://download.pytorch.org/whl/torch_stable.html || true

# Install Python requirements
# whisper will be installed via Git to ensure Python 3.10 compatibility
RUN pip install -r /app/requirements.txt

# Copy application files
COPY . /app

# Make start script executable
RUN chmod +x /app/start.sh

# Environment defaults (can be overridden via Render or Docker ENV)
ENV OUTPUT_DIR=/app/outputs
ENV WHISPER_MODEL=small
ENV MAX_CLIP_SECONDS=60
ENV MIN_CLIP_SECONDS=6
ENV PYTHONUNBUFFERED=1

# Expose FastAPI port
EXPOSE 8000

# Start the bot/server
CMD ["/app/start.sh"]
