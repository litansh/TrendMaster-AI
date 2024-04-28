FROM python:3.9-slim

# Install necessary system packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libgfortran5 \
    libatlas-base-dev \
    libsodium-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file to the container
COPY requirements.txt /tmp/

# # Install the remaining Python packages from requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy your application to the container
COPY . /app
WORKDIR /app

CMD ["python", "./scripts/anomaly_detection.py"]
