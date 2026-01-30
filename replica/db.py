import os
import sqlite3

DB_FILE = "sqlite.db"

def get_conn():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
    else:
        conn = sqlite3.connect(f'file:{DB_FILE}?mode=ro', uri=True)
    return conn


def db_setting(conn):
    conn.execute("PRAGMA journal_mode=WAL;")


def select_(conn):
    conn.execute("""
        SELECT
            *
        FROM
            test
        ;
    """)