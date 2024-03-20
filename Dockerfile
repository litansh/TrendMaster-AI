FROM python:3.9-slim

WORKDIR /usr/src/app

COPY . .

# Install system dependencies for Prophet
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        git \
        libatlas-base-dev \
        liblapack-dev \
        gfortran \
        libgsl-dev \
        libsuitesparse-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "./scripts/anomaly_detection.py"]
