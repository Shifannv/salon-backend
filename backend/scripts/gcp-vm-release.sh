#!/usr/bin/env bash
set -euo pipefail

# No implicit head or environment-derived approval. Reviewed operator input is required.
: "${SALON_MIGRATION_POLICY:?Set explicit migration policy after review; no automatic upgrade head}"
: "${SALON_MIGRATION_REVISION:?Set an explicit reviewed revision; head is refused}"
: "${SALON_MIGRATION_APPROVAL_ID:?Explicit migration/deployment approval is required}"
case "$SALON_MIGRATION_POLICY:$SALON_MIGRATION_REVISION" in
  portable-ci:0037_customer_processing_charge) ;;
  mumbai:0040_fastapi_only_access)
    : "${SALON_MUMBAI_PROJECT:?Confirm the Mumbai Supabase project}"
    : "${SALON_MIGRATION_MANIFEST:?Provide the approved review/preflight manifest}"
    [[ "$SALON_MUMBAI_PROJECT" == wqjlgpnbiapcrlkxumcp && -f "$SALON_MIGRATION_MANIFEST" ]] || {
      echo "Mumbai confirmation or approved evidence manifest missing; migrations refused." >&2
      exit 1
    }
    ;;
  *) echo "Unreviewed migration target; portable CI is 0037, prepared Mumbai is 0040 with explicit approval. head is refused." >&2; exit 1 ;;
esac

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
echo "Applying explicitly selected reviewed migration target: $SALON_MIGRATION_REVISION"
"${compose[@]}" run --rm --no-deps api alembic current
if [[ "$SALON_MIGRATION_POLICY" == mumbai ]]; then
  manifest_dir="$(cd "$(dirname "$SALON_MIGRATION_MANIFEST")" && pwd -P)"
  manifest_name="$(basename "$SALON_MIGRATION_MANIFEST")"
  "${compose[@]}" run --rm --no-deps -v "$manifest_dir:/migration-approval:ro" api \
    alembic -x migration_policy=mumbai -x "mumbai_project=$SALON_MUMBAI_PROJECT" \
    -x "approval_id=$SALON_MIGRATION_APPROVAL_ID" \
    -x "approval_manifest=/migration-approval/$manifest_name" upgrade "$SALON_MIGRATION_REVISION"
else
  "${compose[@]}" run --rm --no-deps api alembic -x migration_policy=portable-ci upgrade "$SALON_MIGRATION_REVISION"
fi
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
