"""Write every NL query + generated SQL to the audit_log table (law-enforcement accountability)."""

import sqlite3
from datetime import datetime, timezone
from . import config


def log(user_id, nl_question, generated_query, row_count, role):
    """Append one row to audit_log. Silently no-ops if the DB is read-only (shouldn't happen)."""
    try:
        conn = sqlite3.connect(config.DB_PATH)
        conn.execute(
            "INSERT INTO audit_log (user_id, asked_at, nl_question, generated_query, row_count, role_at_time) "
            "VALUES (?,?,?,?,?,?)",
            (user_id,
             datetime.now(timezone.utc).isoformat(),
             nl_question, generated_query, row_count, role),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # audit failure must never break the user-facing response
