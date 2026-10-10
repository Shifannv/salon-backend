#!/usr/bin/env bash
set -euo pipefail

# Build locally by default. Use --pull with SALON_API_IMAGE for a registry release.
# Migrations are always a separate, explicitly reviewed command.
cd "$(dirname "$0")/.."

mode="${1:---build}"
if [[ $# -gt 1 || ( "$mode" != "--build" && "$mode" != "--pull" ) ]]; then
  echo "Usage: bash scripts/gcp-vm-deploy.sh [--build|--pull]" >&2
  exit 1
fi

export COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE:-.env}"
if [[ ! -f "$COMPOSE_ENV_FILE" ]]; then
  echo "Missing runtime env file. Create backend/.env from .env.gcp.example and fill it on the VM." >&2
  exit 1
fi
if [[ "$mode" == "--pull" && -z "${SALON_API_IMAGE:-}" ]]; then
  echo "Set SALON_API_IMAGE to the reviewed registry image (preferably an immutable digest)." >&2
  exit 1
fi

compose=(docker compose --env-file "$COMPOSE_ENV_FILE")
"${compose[@]}" config --quiet
if [[ "$mode" == "--pull" ]]; then
  "${compose[@]}" pull api notification-worker media-cleanup redis
else
  "${compose[@]}" build --pull api
  "${compose[@]}" pull redis
fi

# Wait for API/Redis health and for the worker process to be running.
if ! "${compose[@]}" up -d --no-build --pull never --remove-orphans --wait --wait-timeout 120; then
  "${compose[@]}" ps --all
  echo "Deployment did not become healthy. Inspect container logs on the VM." >&2
  exit 1
fi
"${compose[@]}" ps
echo "API and notification worker deployed. Required migrations must already be applied."
