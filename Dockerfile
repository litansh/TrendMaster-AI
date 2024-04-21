FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libgfortran5 \
    libatlas-base-dev \
    libsodium-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/

# Upgrade pip and install packages individually
RUN pip install --no-cache-dir -U pip
RUN pip install --no-cache-dir numpy==1.23.1
RUN pip install --no-cache-dir pandas==1.2.3
RUN pip install --no-cache-dir pyyaml==5.4.1
RUN pip install --no-cache-dir holidays==0.10.3
RUN pip install --no-cache-dir pystan==2.19.1.1
RUN pip install --no-cache-dir prophet==1.0

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app
WORKDIR /app

CMD ["python", "./scripts/anomaly_detection.py"]
