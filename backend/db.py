"""SQLite schema and serialized connection access."""
from __future__ import annotations
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from .config import DATABASE_PATH

_lock = threading.RLock()
_connections: dict[str, sqlite3.Connection] = {}
SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
 transaction_id TEXT PRIMARY KEY, date TEXT NOT NULL,
 amount_minor INTEGER NOT NULL CHECK(amount_minor > 0), currency TEXT NOT NULL DEFAULT 'INR',
 direction TEXT NOT NULL, txn_type TEXT NOT NULL, counterparty_raw TEXT NOT NULL,
 vpa TEXT, name_key TEXT, display_merchant TEXT NOT NULL, merchant_source TEXT NOT NULL,
 category TEXT NOT NULL, upi_ref TEXT, source TEXT NOT NULL, dedup_key TEXT NOT NULL UNIQUE,
 created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(date);
CREATE TABLE IF NOT EXISTS merchant_aliases (
 identifier_type TEXT NOT NULL, identifier_value TEXT NOT NULL, display_merchant TEXT NOT NULL,
 category TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(identifier_type, identifier_value));
CREATE TABLE IF NOT EXISTS budgets (
 month TEXT PRIMARY KEY, limit_minor INTEGER NOT NULL CHECK(limit_minor >= 100));
"""

def _path() -> str:
    return os.environ.get("WDMMG_DB", DATABASE_PATH)

def get_connection() -> sqlite3.Connection:
    path = _path()
    with _lock:
        conn = _connections.get(path)
        if conn is None:
            if path != ":memory:":
                Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(path, check_same_thread=False, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 10000")
            _connections[path] = conn
        return conn

@contextmanager
def locked_connection() -> Iterator[sqlite3.Connection]:
    with _lock:
        conn = get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

def init_db() -> None:
    with locked_connection() as conn:
        conn.executescript(SCHEMA)

def close_connections() -> None:
    with _lock:
        for conn in _connections.values():
            conn.close()
        _connections.clear()
