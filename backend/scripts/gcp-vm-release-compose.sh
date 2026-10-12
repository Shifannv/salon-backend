#!/usr/bin/env bash
set -euo pipefail

# Operate on an artifact release using the existing VM secrets and Compose project.
cd "$(dirname "$0")/.."
export COMPOSE_ENV_FILE="${SALON_DEPLOY_ROOT:-$HOME/salon-backend}/backend/.env"
export COMPOSE_PROJECT_NAME=backend
export SALON_API_IMAGE
SALON_API_IMAGE="$(cat image-ref)"
if [[ ! "$SALON_API_IMAGE" =~ ^salon-platform-api:sha-[a-f0-9]{40}-[0-9]+-[0-9]+$ ]]; then
  echo "Invalid release image reference." >&2
  exit 1
fi
if [[ ! -f "$COMPOSE_ENV_FILE" ]]; then
  echo "Missing VM runtime env file: $COMPOSE_ENV_FILE" >&2
  exit 1
fi
if [[ "$(docker image inspect --format '{{.Id}}' "$SALON_API_IMAGE")" != "$(cat image-id)" ]]; then
  echo "Release image does not match the image tested in CI." >&2
  exit 1
fi

if [[ "${1:-}" == "--deploy" && $# -eq 1 ]]; then
  exec bash scripts/gcp-vm-deploy.sh --local-image
fi
exec docker compose --env-file "$COMPOSE_ENV_FILE" "$@"
