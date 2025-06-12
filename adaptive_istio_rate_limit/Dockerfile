# TrendMaster-AI Adaptive Istio Rate Limiting System
# Production-Ready Multi-Stage Dockerfile

# Build stage
FROM python:3.9-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION=3.0.0
ARG VCS_REF

# Add metadata
LABEL maintainer="TrendMaster-AI Team" \
      version="${VERSION}" \
      description="TrendMaster-AI Adaptive Istio Rate Limiting System" \
      build-date="${BUILD_DATE}" \
      vcs-ref="${VCS_REF}"

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.9-slim as production

# Set production arguments
ARG VERSION=3.0.0
ARG BUILD_DATE
ARG VCS_REF

# Add metadata
LABEL maintainer="TrendMaster-AI Team" \
      version="${VERSION}" \
      description="TrendMaster-AI Adaptive Istio Rate Limiting System" \
      build-date="${BUILD_DATE}" \
      vcs-ref="${VCS_REF}"

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r trendmaster && \
    useradd -r -g trendmaster -d /app -s /bin/bash trendmaster

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=trendmaster:trendmaster . .

# Create necessary directories
RUN mkdir -p /app/output /app/logs /app/backups && \
    chown -R trendmaster:trendmaster /app

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    DRY_RUN=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python scripts/main.py --validate-only || exit 1

# Switch to non-root user
USER trendmaster

# Expose port (if web interface is added)
EXPOSE 8080

# Use dumb-init to handle signals properly
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# Default command
CMD ["python", "scripts/main.py"]

# Development stage (optional)
FROM production as development

# Switch back to root for development tools
USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest>=6.2.0 \
    pytest-asyncio>=0.15.0 \
    pytest-cov>=2.12.0 \
    black>=21.6.0 \
    flake8>=3.9.0 \
    mypy>=0.910 \
    pre-commit>=2.13.0 \
    bandit>=1.7.0 \
    safety>=1.10.0 \
    ipython \
    jupyter

# Install additional development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    htop \
    tree \
    && rm -rf /var/lib/apt/lists/*

# Set development environment variables
ENV ENVIRONMENT=local \
    LOG_LEVEL=DEBUG \
    DRY_RUN=true

# Switch back to trendmaster user
USER trendmaster

# Development command
CMD ["python", "scripts/main.py", "--verbose"]

# Testing stage
FROM production as testing

# Switch to root for test dependencies
USER root

# Install testing dependencies
RUN pip install --no-cache-dir \
    pytest>=6.2.0 \
    pytest-asyncio>=0.15.0 \
    pytest-cov>=2.12.0 \
    pytest-xdist>=2.3.0

# Set testing environment variables
ENV ENVIRONMENT=testing \
    LOG_LEVEL=DEBUG \
    DRY_RUN=true

# Switch back to trendmaster user
USER trendmaster

# Testing command
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=scripts", "--cov-report=html"]

# Production optimized stage
FROM production as production-optimized

# Additional production optimizations
USER root

# Remove unnecessary packages and clean up
RUN apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    find /opt/venv -name "*.pyc" -delete && \
    find /opt/venv -name "__pycache__" -type d -exec rm -rf {} + || true

# Optimize Python bytecode
RUN python -m compileall /opt/venv/lib/python*/site-packages/ || true && \
    python -m compileall /app/scripts/ || true

# Set strict production environment
ENV ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    DRY_RUN=false \
    PYTHONOPTIMIZE=2

# Final security hardening
RUN chmod -R 755 /app && \
    chmod -R 644 /app/config/ && \
    chmod 755 /app/scripts/main.py

# Switch to non-root user
USER trendmaster

# Production command with optimizations
CMD ["python", "-O", "scripts/main.py"]
