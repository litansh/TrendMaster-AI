FROM python:3.9-slim as builder

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libffi-dev \
    libssl-dev \
    make \
    libtool \
    autoconf \
    automake \
    libyaml-dev  # This is specifically for PyYAML if it needs to compile from source

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt --verbose

FROM python:3.9-slim
COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY . /app
WORKDIR /app

CMD ["python", "./scripts/anomaly_detection.py"]
