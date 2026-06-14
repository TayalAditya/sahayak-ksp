#!/usr/bin/env bash
# Sahayak — one-command Catalyst deployment
# Usage: bash deploy.sh
# Prereqs: catalyst CLI installed, `catalyst login` done, .env populated

set -e
echo "=== Sahayak — Catalyst Deploy ==="

# 1. Build frontend
echo "\n[1/4] Building React frontend..."
cd frontend && npm run build && cd ..

# 2. Deploy frontend to Catalyst Slate
echo "\n[2/4] Deploying frontend to Catalyst Slate..."
catalyst deploy --service web-client

# 3. Deploy backend to Catalyst AppSail
echo "\n[3/4] Deploying backend to Catalyst AppSail..."
catalyst deploy --service appsail

# 4. Push Data Store tables + data
echo "\n[4/4] Setting up Data Store (tables + CSV upload)..."
python tools/catalyst_datastore_setup.py

echo "\n=== Deploy complete ==="
echo "Frontend : check Catalyst console -> Slate -> Deployments for live URL"
echo "Backend  : check Catalyst console -> AppSail -> sahayak-backend for URL"
echo "Update frontend/.env.production VITE_API_URL with the AppSail URL, then redeploy frontend."
