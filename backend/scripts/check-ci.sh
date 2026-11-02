#!/usr/bin/env bash
set -euo pipefail

# Local pre-commit/pre-push verification. Keep aligned with backend.yml.
# Requires an environment with requirements-dev.txt installed and Docker running.
python="${PYTHON:-python}"
if [[ "$python" == */* ]]; then
  python="$(cd "$(dirname "$python")" && pwd)/$(basename "$python")"
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."
"$python" -c 'import sys; assert sys.version_info >= (3, 12), "Python 3.12+ required"; print("Local Python:", sys.version.split()[0], "(GitHub CI uses 3.12)")'
"$python" -m pip check
"$python" -m ruff check app tests migrations \
  scripts/docker_image_ids.py scripts/cloud_run_candidate.py scripts/cloud_run_auto.py \
  scripts/ci_image_bundle.py scripts/ci_registry_image.py
for script in scripts/*.sh; do bash -n "$script"; done
git diff --check
docker info >/dev/null
docker compose version

database_id=""
cleanup() {
  result=$?
  trap - EXIT
  # Only this invocation's returned container ID; never Compose or shared DBs.
  if [[ -n "$database_id" ]]; then
    if ! docker rm --force --volumes "$database_id" >/dev/null; then
      echo "Could not remove temporary CI database $database_id" >&2
      result=1
    fi
  fi
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

database_id="$(docker run --detach --publish 127.0.0.1::5432 \
  --env POSTGRES_PASSWORD=ci-only-password \
  --label salon.ci.owner=local-preflight postgres:18)"
ready=false
for ((attempt = 0; attempt < 60; attempt++)); do
  if docker exec "$database_id" pg_isready -U postgres >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "$ready" != true ]]; then
  echo 'Temporary CI PostgreSQL did not become ready.' >&2
  exit 1
fi
binding="$(docker port "$database_id" 5432/tcp)"
port="${binding##*:}"
port="${port//$'\r'/}"
[[ "$port" =~ ^[0-9]+$ ]] || { echo 'Invalid temporary database port.' >&2; exit 1; }

export ENVIRONMENT=test
export SALON_ENV_FILE=__no_local_ci_environment_file__
export DATABASE_URL="postgresql+asyncpg://postgres:ci-only-password@127.0.0.1:$port/postgres"
export MIGRATION_TEST_DB="postgresql://postgres:ci-only-password@127.0.0.1:$port/postgres"
export PORTABLE_CI_TARGET=0037_customer_processing_charge
"$python" -m pytest -q tests/unit/test_migration_policy.py
"$python" -m pytest -q

COMPOSE_ENV_FILE=.env.gcp.example docker compose \
  --env-file .env.gcp.example -f docker-compose.yml config --quiet
# Working-tree builds are deliberately unlabelled as a Git release, even when
# the latest commit exists: uncommitted files are part of this verification.
image="salon-platform-api:local-ci-${database_id:0:12}"
docker build --pull --platform linux/amd64 --build-arg SOURCE_COMMIT=unknown --tag "$image" .
bash scripts/check-container.sh "$image" unknown
echo "Local CI checks passed. Diagnostic image retained: $image"
echo 'GitHub must also pass on the pushed commit and PR merge result before release.'
