#!/bin/bash
set -e
export PYTHONPATH=/app

echo "[startup] Installing dependencies..."
python -m pip install -r /app/backend/requirements.txt --quiet --no-warn-script-location

echo "[startup] Generating database..."
cd /app && python data/generate.py

echo "[startup] Starting server..."
exec python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
