#!/bin/bash
# Catalyst AppSail startup script
pip install -r /app/backend/requirements.txt --quiet
cd /app
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
