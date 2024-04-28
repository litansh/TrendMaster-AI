# Use an Alpine base image
FROM python:3.9-alpine as builder

# Install build dependencies
RUN apk add --no-cache gcc g++ python3-dev libgfortran musl-dev libffi-dev openssl-dev make libtool autoconf automake linux-headers libstdc++

# Set up a virtual environment to make dependencies reusable
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Update pip and install critical dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Cython and pre-built wheel of PyYAML
RUN pip install --no-cache-dir Cython
RUN pip install --no-cache-dir PyYAML==6.0.1 --only-binary=:all:

# Copy and install Python dependencies from requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Multi-stage: final image
FROM python:3.9-alpine
COPY --from=builder /opt/venv /opt/venv

# Set environment to use the virtualenv
ENV PATH="/opt/venv/bin:$PATH"

# Copy your application to the container
COPY . /app
WORKDIR /app

CMD ["python", "./scripts/anomaly_detection.py"]
