import os
from fastapi import FastAPI, HTTPException, Query, Response

from db import db_setting

# ---------------------------
# 설정
# ---------------------------
WAL_FILE = "sqlite.db-wal"
MAX_BYTES_DEFAULT = 256 * 1024  # 256 KB per request
print(f"DB status: {db_setting()}")

# ---------------------------
# Helper 함수
# ---------------------------

def get_wal_size():
    if not os.path.exists(WAL_FILE):
        return 0
    return os.path.getsize(WAL_FILE)

def read_wal_chunk(offset: int, max_bytes: int):
    wal_size = get_wal_size()

    if offset >= wal_size:
        return None, wal_size

    read_size = min(max_bytes, wal_size - offset)

    with open(WAL_FILE, "rb") as f:
        f.seek(offset)
        data = f.read(read_size)

    end_offset = offset + len(data)
    return data, end_offset

# ---------------------------
# WAL API
# ---------------------------
app = FastAPI(title="Russian Roulette - Leader WAL API")

@app.get("/internal/wal")
def wal_endpoint(offset: int = Query(..., ge=0), max_bytes: int = Query(MAX_BYTES_DEFAULT, gt=0)):
    chunk, end_offset = read_wal_chunk(offset, max_bytes)
    wal_size = get_wal_size()

    if chunk is None or len(chunk) == 0:
        return Response(
            status_code=204,
            headers={
                "X-WAL-Current-Size": str(wal_size),
            },
        )

    return Response(
        content=chunk,
        media_type="application/octet-stream",
        headers={
            "X-WAL-Start-Offset": str(offset),
            "X-WAL-End-Offset": str(end_offset),
            "X-WAL-Current-Size": str(wal_size),
        },
    )

# ---------------------------
# Health check (PoC용)
# ---------------------------

@app.get("/health")
def health():
    wal_size = get_wal_size()
    return {"status": "ok", "wal_size": wal_size}
