"""Lightweight settings + .env loader (no external dependency)."""

import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DB = os.path.join(_ROOT, "data", "ksp_crime.db")


def load_dotenv(path=None):
    """Minimal .env loader: KEY=VALUE lines into os.environ (does not override existing)."""
    path = path or os.path.join(_ROOT, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)


def get(key, default=None):
    return os.environ.get(key, default)


# Load .env on import so all modules see the values.
load_dotenv()

DB_PATH = os.environ.get("SAHAYAK_DB", DEFAULT_DB)
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "mock")
MAX_ROWS = int(os.environ.get("SAHAYAK_MAX_ROWS", "200"))
