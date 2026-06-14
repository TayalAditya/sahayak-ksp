"""AppSail entry point — Catalyst looks for main.py at repo root or service root."""
from backend.api.main import app  # noqa: F401 — re-exported for uvicorn
