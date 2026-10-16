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
      "import importlib, os, pathlib; assert os.getuid() != 0; assert pathlib.Path('migrations/sql/001_supabase_schema.sql').is_file(); [importlib.import_module(module) for module in ('app.infrastructure.push.outbox_worker', 'app.infrastructure.media.cleanup_worker', 'app.infrastructure.account_deletion.worker', 'app.infrastructure.account_deletion.health', 'app.infrastructure.payments.webhook_worker')]"
    docker exec "$container" alembic heads
    # Negative guard check: rejects before DB connection or migration execution.
    if guard_output="$(docker exec --env DATABASE_URL=postgresql+asyncpg://postgres:synthetic@127.0.0.1:1/postgres \
      "$container" alembic -x migration_policy=portable-ci upgrade head 2>&1)"; then
      echo "Unsafe implicit migration head was accepted." >&2
      exit 1
    fi
    if [[ "$guard_output" != *'Implicit upgrade head is refused'* ]]; then
      printf '%s\n' "$guard_output" >&2
      echo "Migration guard check failed for an unexpected reason." >&2
      exit 1
    fi
    echo "Image passed: non-root API on PORT=8080, /health, all worker imports, migration files."
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
