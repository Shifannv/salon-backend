#!/usr/bin/env bash
set -euo pipefail

release_dir="$(cd "$(dirname "$0")/.." && pwd -P)"
releases_dir="$(cd "${SALON_DEPLOY_ROOT:-$HOME/salon-backend}/releases" && pwd -P)"
if [[ "$release_dir" != "$releases_dir/"* || ! -f "$release_dir/image.tar.gz" ]]; then
  echo "Run this script from an uploaded release under ~/salon-backend/releases/." >&2
  exit 1
fi
cd "$release_dir"

# Keep the lock across image loading, migrations, readiness and pointer update.
exec 9>"$releases_dir/deploy.lock"
flock -w 600 9
docker load --input image.tar.gz
compose=(bash scripts/gcp-vm-release-compose.sh)
"${compose[@]}" config --quiet

# Explicit deploy step. Review migrations before merging a release into main.
# Failure here leaves the running services and current-release pointer untouched.
echo "Applying reviewed database migrations from the tested release image."
"${compose[@]}" run --rm --no-deps api alembic current
"${compose[@]}" run --rm --no-deps api alembic upgrade head
"${compose[@]}" run --rm --no-deps api alembic current

"${compose[@]}" --deploy
for endpoint in health health/db health/redis; do
  "${compose[@]}" exec -T api python -c \
    'import os, sys, urllib.request; urllib.request.urlopen("http://127.0.0.1:" + os.environ.get("PORT", "8000") + "/" + sys.argv[1], timeout=10).read()' \
    "$endpoint"
done

# Only a healthy deployment becomes current. Do not automatically undo migrations.
ln -sfn "$release_dir" "$releases_dir/current.next"
mv -Tf "$releases_dir/current.next" "$releases_dir/current"
echo "Healthy release: $release_dir"
