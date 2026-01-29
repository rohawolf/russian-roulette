import os
import sqlite3

DB_FILE = "sqlite.db"

def db_setting():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA wal_autocheckpoint=0;")
    
    cursor_ = conn.cursor()

    cursor_.execute("PRAGMA integrity_check;")
    return cursor_.fetchone()
