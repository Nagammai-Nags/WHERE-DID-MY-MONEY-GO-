"""SQLite repository. SQL is parameterized and every write is committed."""
from __future__ import annotations
from datetime import datetime, timezone
import sqlite3
from typing import Any

from .db import locked_connection

_TXN_FIELDS = ("transaction_id", "date", "amount_minor", "currency", "direction", "txn_type",
               "counterparty_raw", "vpa", "name_key", "display_merchant", "merchant_source",
               "category", "upi_ref", "source", "dedup_key")

def insert_transaction(t: dict) -> bool:
    values = [t.get(k) for k in _TXN_FIELDS]
    with locked_connection() as conn:
        try:
            conn.execute(
                f"INSERT INTO transactions ({','.join(_TXN_FIELDS)},created_at) VALUES ({','.join('?' for _ in _TXN_FIELDS)},?)",
                (*values, datetime.now(timezone.utc).isoformat()),
            )
            return True
        except sqlite3.IntegrityError as exc:
            exists = conn.execute("SELECT 1 FROM transactions WHERE dedup_key=?", (t.get("dedup_key"),)).fetchone()
            if exists:
                return False
            raise ValueError(f"transaction violates database constraints: {exc}") from exc

def list_transactions(date_from: str | None = None, date_to: str | None = None,
                      category: str | None = None, txn_type: str | None = None,
                      merchant_source: str | None = None, limit: int = 1000,
                      offset: int = 0) -> list[dict]:
    clauses, params = [], []
    for column, value, op in (("date", date_from, ">="), ("date", date_to, "<="),
                              ("category", category, "="), ("txn_type", txn_type, "="),
                              ("merchant_source", merchant_source, "=")):
        if value is not None:
            clauses.append(f"{column} {op} ?")
            params.append(value)
    sql = "SELECT " + ",".join(_TXN_FIELDS) + " FROM transactions"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY date DESC, transaction_id LIMIT ? OFFSET ?"
    params.extend((limit, offset))
    with locked_connection() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]

def get_alias(identifier_type: str, identifier_value: str) -> dict | None:
    with locked_connection() as conn:
        row = conn.execute("SELECT identifier_type,identifier_value,display_merchant,category FROM merchant_aliases WHERE identifier_type=? AND identifier_value=?", (identifier_type, identifier_value)).fetchone()
        return dict(row) if row else None

def upsert_alias(identifier_type: str, identifier_value: str, display_merchant: str, category: str) -> None:
    with locked_connection() as conn:
        conn.execute("INSERT INTO merchant_aliases VALUES (?,?,?,?,?) ON CONFLICT(identifier_type,identifier_value) DO UPDATE SET display_merchant=excluded.display_merchant, category=excluded.category, updated_at=excluded.updated_at",
                     (identifier_type, identifier_value, display_merchant, category, datetime.now(timezone.utc).isoformat()))

def list_aliases() -> list[dict]:
    with locked_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT identifier_type,identifier_value,display_merchant,category FROM merchant_aliases ORDER BY identifier_type,identifier_value").fetchall()]

def update_transactions_for_identifier(identifier_type: str, identifier_value: str, display_merchant: str, category: str) -> int:
    columns = {"VPA": "vpa", "NAME": "name_key"}
    if identifier_type not in columns:
        raise ValueError("identifier_type must be VPA or NAME")
    with locked_connection() as conn:
        cur = conn.execute(f"UPDATE transactions SET display_merchant=?,category=?,merchant_source='USER' WHERE txn_type='EXPENSE' AND {columns[identifier_type]}=?",
                            (display_merchant, category, identifier_value))
        return cur.rowcount

def get_budget(month: str) -> int | None:
    with locked_connection() as conn:
        row = conn.execute("SELECT limit_minor FROM budgets WHERE month=?", (month,)).fetchone()
        return int(row[0]) if row else None

def set_budget(month: str, limit_minor: int) -> None:
    with locked_connection() as conn:
        conn.execute("INSERT INTO budgets(month,limit_minor) VALUES (?,?) ON CONFLICT(month) DO UPDATE SET limit_minor=excluded.limit_minor", (month, limit_minor))

def reset_all() -> None:
    with locked_connection() as conn:
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM merchant_aliases")
        conn.execute("DELETE FROM budgets")
