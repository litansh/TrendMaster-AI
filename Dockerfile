FROM python:3.9-slim

# Install necessary system packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libgfortran5 \
    libatlas-base-dev \
    libsodium-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file to the container
COPY requirements.txt /tmp/

# Update pip and install numpy separately to ensure it's available for other packages
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir numpy==1.23.1

# Install the remaining Python packages from requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy your application to the container
COPY . /app
WORKDIR /app

CMD ["python", "./scripts/anomaly_detection.py"]
