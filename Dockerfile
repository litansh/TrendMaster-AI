# Use an Alpine base image
FROM python:3.9-alpine as builder

# Install system dependencies for building Python packages
RUN apk add --no-cache gcc g++ python3-dev libgfortran musl-dev libffi-dev openssl-dev linux-headers libstdc++ make

# Set up a virtual environment to make dependencies reusable
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Update pip, setuptools, and wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Cython separately to avoid build issues
RUN pip install --no-cache-dir Cython

# Install PyYAML separately to handle potential build issues
RUN pip install --no-cache-dir PyYAML==5.4.1

# Copy and install remaining Python dependencies
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
