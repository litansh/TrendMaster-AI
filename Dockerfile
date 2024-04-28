FROM python:3.9-slim

# Install necessary system packages and clean up in one layer to reduce image size
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libgfortran5 \
    libatlas-base-dev \
    libsodium-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Update pip and install Python dependencies in one layer
RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir numpy==1.23.1 cython \
 && pip install --no-cache-dir pandas==1.2.3 convertdate lunarcalendar holidays==0.10.3 ephem tqdm \
 && pip install --no-cache-dir pystan==2.19.1.1 prophet==1.0.1

# Copy your application to the container
COPY . /app
WORKDIR /app

CMD ["python", "./scripts/anomaly_detection.py"]
