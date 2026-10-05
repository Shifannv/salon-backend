#!/usr/bin/env bash
set -euo pipefail

# Isolated smoke check: no production credentials, published ports, or live database.
image="${1:?Usage: bash scripts/check-container.sh IMAGE}"
container="salon-api-check-$$"
cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run --detach --name "$container" \
  --env ENVIRONMENT=test --env PORT=8080 \
  --health-interval=2s --health-start-period=1s --health-retries=30 \
  "$image" >/dev/null

for ((attempt = 0; attempt < 60; attempt++)); do
  health="$(docker inspect --format '{{.State.Health.Status}}' "$container")"
  if [[ "$health" == "healthy" ]]; then
    docker exec "$container" python -c \
      "import os, pathlib; assert os.getuid() != 0; assert pathlib.Path('migrations/001_supabase_schema.sql').is_file(); import app.infrastructure.push.outbox_worker"
    docker exec "$container" alembic heads
    echo "Image passed: non-root API on PORT=8080, /health, worker import, migration files."
    exit 0
  fi
  if [[ "$(docker inspect --format '{{.State.Running}}' "$container")" != "true" ]]; then
    break
  fi
  sleep 2
done

docker logs --tail=100 "$container"
echo "Container smoke check failed." >&2
exit 1
