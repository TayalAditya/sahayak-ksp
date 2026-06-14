"""
Read-only database access + SQL safety for the NL->query engine.

Two layers of defence against unsafe model output:
  1. The connection is opened READ-ONLY (SQLite `mode=ro`) — writes fail at the driver.
  2. Every query is validated before execution: must be a single SELECT/WITH, no DDL/DML
     keywords, references only known tables, and is row-capped.

Nothing the LLM emits is trusted; this module is the gatekeeper.
"""

import re
import sqlite3

from . import config

# Statements/keywords that must never appear in a generated query.
_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|"
    r"pragma|vacuum|reindex|grant|revoke)\b",
    re.IGNORECASE,
)


class UnsafeQueryError(ValueError):
    """Raised when a generated query fails the safety check."""


def _connect():
    # Read-only URI connection — defence-in-depth even if validation is bypassed.
    return sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)


def table_names():
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def get_schema_dict():
    """Return {table: [(col, type), ...]} — fed to the model so it writes correct SQL."""
    conn = _connect()
    schema = {}
    try:
        for t in table_names():
            cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
            schema[t] = [(c[1], c[2]) for c in cols]  # (name, type)
        return schema
    finally:
        conn.close()


def validate_select(sql, allowed_tables=None):
    """
    Validate a generated query is a safe read. Returns the cleaned SQL (LIMIT enforced).
    Raises UnsafeQueryError otherwise.
    """
    if sql is None:
        raise UnsafeQueryError("empty query")
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise UnsafeQueryError("empty query")

    # Single statement only (no stacked queries).
    if ";" in cleaned:
        raise UnsafeQueryError("multiple statements are not allowed")

    lowered = cleaned.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise UnsafeQueryError("only SELECT/WITH queries are allowed")

    if _FORBIDDEN.search(cleaned):
        raise UnsafeQueryError("query contains a forbidden (write/DDL) keyword")

    # Table allow-list: every identifier after FROM/JOIN must be a known table.
    allowed = set(allowed_tables or table_names())
    referenced = re.findall(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", cleaned, re.IGNORECASE)
    for tbl in referenced:
        if tbl.lower() not in {a.lower() for a in allowed}:
            raise UnsafeQueryError(f"query references unknown table '{tbl}'")

    # Enforce a row cap so a runaway query can't dump the whole DB.
    if not re.search(r"\blimit\b", lowered):
        cleaned = f"{cleaned}\nLIMIT {config.MAX_ROWS}"
    return cleaned


def run_query(sql, allowed_tables=None):
    """
    Validate + execute a read-only query.
    Returns {"columns": [...], "rows": [ {...}, ... ], "sql": <executed sql>, "row_count": n}.
    """
    safe_sql = validate_select(sql, allowed_tables)
    conn = _connect()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(safe_sql)
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description] if cur.description else []
        return {
            "columns": columns,
            "rows": [dict(r) for r in rows],
            "sql": safe_sql,
            "row_count": len(rows),
        }
    finally:
        conn.close()
