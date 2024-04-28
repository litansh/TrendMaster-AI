# Use a Debian base image for better library compatibility
FROM python:3.9-slim as builder

# Install system dependencies required by common Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libffi-dev \
    openssl-dev \
    make \
    libtool \
    autoconf \
    automake \
    libyaml-dev  # This is specifically for PyYAML if it needs to compile from source

# Set up a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Update pip and explicitly install wheel and setuptools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy and install Python dependencies from requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt --verbose

# Multi-stage: final image
FROM python:3.9-slim
COPY --from=builder /opt/venv /opt/venv

# Set environment to use the virtualenv
ENV PATH="/opt/venv/bin:$PATH"

# Copy your application to the container
COPY . /app
WORKDIR /app

CMD ["python", "./scripts/anomaly_detection.py"]
