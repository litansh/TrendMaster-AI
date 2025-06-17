# TrendMaster-AI Adaptive Istio Rate Limiting System
# Production-ready Docker image

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r trendmaster && useradd -r -g trendmaster trendmaster

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY scripts/ scripts/
COPY config/ config/
COPY tests/ tests/
COPY k8s/ k8s/

# Create necessary directories
RUN mkdir -p output logs && \
    chown -R trendmaster:trendmaster /app

# Switch to non-root user
USER trendmaster

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command
CMD ["python", "scripts/main.py"]

# Labels for metadata
LABEL maintainer="Kaltura DevOps Team <devops@kaltura.com>"
LABEL version="3.0.0"
LABEL description="TrendMaster-AI Adaptive Istio Rate Limiting System"
LABEL org.opencontainers.image.source="https://github.com/kaltura/TrendMaster-AI"
LABEL org.opencontainers.image.documentation="https://github.com/kaltura/TrendMaster-AI/blob/main/README.md"
LABEL org.opencontainers.image.licenses="MIT"
