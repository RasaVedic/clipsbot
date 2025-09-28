# Use official Python slim image
FROM python:3.12-slim

# set workdir
WORKDIR /app

# system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ffmpeg \
      git \
      build-essential \
      libsndfile1 \
      libssl-dev \
      ca-certificates \
      && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt /app/requirements.txt

# Install torch CPU wheel first (stable) to avoid heavy builds
# Use official PyTorch index for CPU wheels
RUN pip install --upgrade pip setuptools wheel
RUN pip install "torch==2.2.3+cpu" --index-url https://download.pytorch.org/whl/cpu -f https://download.pytorch.org/whl/torch_stable.html || true

# Install Python requirements
RUN pip install -r /app/requirements.txt

# Copy app files
COPY . /app

# Make start script executable
RUN chmod +x /app/start.sh

# Environment defaults (can be overridden)
ENV OUTPUT_DIR=/app/outputs
ENV WHISPER_MODEL=small
ENV MAX_CLIP_SECONDS=60
ENV MIN_CLIP_SECONDS=6
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["/app/start.sh"]
