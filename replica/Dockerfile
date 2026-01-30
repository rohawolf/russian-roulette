FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    sqlite3 \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY replica_worker.py .
COPY db.py .

RUN pip install requests

CMD ["python", "replica_worker.py"]
