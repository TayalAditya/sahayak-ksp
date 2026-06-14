"""
RBAC middleware + user resolution.

In dev/local mode: read Authorization: Bearer <username> to look up the user in the DB.
In Catalyst production: Catalyst Authentication will inject the user claims, swapped in Phase 6.

Roles and what they can query:
  Investigator   - their own police station's data only
  Analyst        - their district's data
  Supervisor     - their district + subordinate stations
  Policymaker    - state-wide (no restriction)
"""

import sqlite3
from fastapi import HTTPException, Header
from typing import Optional
from .. engine import config


ROLE_SCOPE = {
    "Investigator": "station",
    "Analyst":      "district",
    "Supervisor":   "district",
    "Policymaker":  "state",
}


def _get_user(username: str):
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, name, role, police_station_id, district_id FROM users WHERE username=?",
        (username,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Resolve the current user from the Authorization header.
    In dev mode, accepts 'Bearer <username>' (no real JWT needed).
    Returns a user dict with id, name, role, police_station_id, district_id.
    Falls back to a default Analyst if no header (dev convenience).
    """
    username = "ana01"  # default dev user
    if authorization and authorization.lower().startswith("bearer "):
        username = authorization[7:].strip()
    user = _get_user(username)
    if not user:
        # Dev fallback — first analyst in DB
        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT id,name,role,police_station_id,district_id,username FROM users WHERE role='Analyst' LIMIT 1").fetchone()
        conn.close()
        if row:
            user = dict(row)
        else:
            raise HTTPException(status_code=401, detail="User not found")
    return user
