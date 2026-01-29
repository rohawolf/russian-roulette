import os
import sqlite3

DB_FILE = "sqlite.db"

def db_setting():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.close()
    
    conn = sqlite3.connect(f'file:{DB_FILE}?mode=ro', uri=True)
    cursor_ = conn.cursor()

    cursor_.execute("PRAGMA integrity_check;")
    return cursor_.fetchone()

