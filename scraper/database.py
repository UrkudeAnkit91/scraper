import sqlite3
from typing import Optional, Tuple
from .config import DB_PATH


def init_database() -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            results_count INTEGER,
            code_generated TEXT
        )
    ''')
    conn.commit()
    return conn, cursor


def save_search(
    cursor: sqlite3.Cursor,
    conn: sqlite3.Connection,
    query: str,
    results_count: int,
    code_generated: Optional[str] = None,
):
    try:
        cursor.execute(
            'INSERT INTO searches (query, results_count, code_generated) VALUES (?, ?, ?)',
            (query, results_count, code_generated),
        )
        conn.commit()
    except Exception as e:
        print(f"  Database error: {e}", flush=True)
