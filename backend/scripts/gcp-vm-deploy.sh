#!/usr/bin/env bash
set -euo pipefail

# Deploy/update the backend on a GCP VM after the repo is cloned.
# Run from the backend directory:
#   bash scripts/gcp-vm-deploy.sh

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  if [ -f .env.gcp.example ]; then
    cp .env.gcp.example .env
    echo "Created backend/.env from .env.gcp.example."
    echo "Edit backend/.env with real secrets, then run this script again."
    exit 1
  fi
  echo "Missing backend/.env. Create it before deploying."
  exit 1
fi

docker compose build
docker compose up -d
docker compose ps

echo "Backend deployed. Health check:"
echo "  curl http://127.0.0.1:8000/health"
