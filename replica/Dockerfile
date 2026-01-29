FROM python:3.11-slim

WORKDIR /app

COPY replica_worker.py .
COPY db.py .

RUN pip install requests

CMD ["python", "replica_worker.py"]
