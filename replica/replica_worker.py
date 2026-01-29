import os
import time
import requests

from db import db_setting

# ---------------------------
# 설정
# ---------------------------

LEADER_URL = os.getenv(
    "LEADER_URL",
    "http://leader:8000/internal/wal",
)                                                # Leader WAL API
WAL_FILE = "sqlite.db-wal"                       # 로컬 WAL 파일
OFFSET_FILE = "wal_offset.meta"                  # 로컬 offset 저장
POLL_INTERVAL = 2.0                              # polling 주기 (초)
MAX_BYTES = 256 * 1024                           # 한 번에 가져올 최대 WAL bytes


# ---------------------------
# offset 관리
# ---------------------------

def load_offset():
    if not os.path.exists(OFFSET_FILE):
        return 0
    with open(OFFSET_FILE, "r") as f:
        return int(f.read().strip())

def save_offset(offset):
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))
        f.flush()
        os.fsync(f.fileno())

# ---------------------------
# WAL pull
# ---------------------------

def pull_wal(last_offset):
    try:
        resp = requests.get(
            LEADER_URL,
            params={"offset": last_offset, "max_bytes": MAX_BYTES},
            timeout=5
        )
        if resp.status_code == 204:
            # 최신 상태
            return None, last_offset
        resp.raise_for_status()
        chunk = resp.content
        end_offset = int(resp.headers.get("X-WAL-End-Offset", last_offset + len(chunk)))
        return chunk, end_offset
    except requests.RequestException as e:
        print(f"[WARN] WAL pull failed: {e}")
        return None, last_offset

# ---------------------------
# WAL append
# ---------------------------

def append_wal(chunk):
    with open(WAL_FILE, "ab") as f:
        f.write(chunk)
        f.flush()
        os.fsync(f.fileno())

# ---------------------------
# Main Loop
# ---------------------------

def work():
    print(f"[INFO] DB status: {db_setting()}")
    print("[INFO] Starting Replica WAL Pull Worker")
    last_offset = load_offset()
    print(f"[INFO] Starting from offset {last_offset}")

    while True:
        chunk, new_offset = pull_wal(last_offset)
        if chunk:
            append_wal(chunk)
            save_offset(new_offset)
            print(f"[INFO] Pulled {len(chunk)} bytes, offset updated to {new_offset}")
        else:
            # 최신 상태이거나 실패 시 sleep
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    work()
