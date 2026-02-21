FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    python3-dev \
    libssl-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ../requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY ../main.py .

ENTRYPOINT ["python"]
CMD ["main.py"]
