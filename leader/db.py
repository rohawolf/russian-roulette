import sqlite3

DB_FILE = "sqlite.db"

def get_conn():
    conn = sqlite3.connect(
        f'file:{DB_FILE}?mode=rwc',
        uri=True,
        isolation_level=None,
    )
    return conn


def db_setting(conn):
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA wal_autocheckpoint = 0;")


def create_table(conn):
    conn.execute("""
        CREATE TABLE test (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            value TEXT
        )
    """)


def insert_(conn):
    conn.execute("""
        INSERT INTO
            test (value)
        VALUES
            ("hihi")
        ;
    """)
