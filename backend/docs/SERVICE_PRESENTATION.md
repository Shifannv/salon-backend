# Service presentation release handover

Revision `0016_service_presentation` follows `0015_salon_admin_approval` and adds
nullable `services.category_name varchar(80)`, `subcategory_name varchar(80)` and
`photo_url text`. Existing rows and the subcategory foreign key survive. Catalog
names remain the fallback; owner display overrides never rename catalog records.
The baseline SQL is unchanged.

Both `ServiceCreateRequest` and `ServiceUpdateRequest` accept the presentation
fields. Names are trimmed, nonempty, and at most 80 characters; photos must be
hosted HTTPS URLs, at most 2048 characters. Unknown fields return 422. PATCH
omission retains values; null clears descriptions, name overrides, and photos.
Required database fields cannot be explicitly null in PATCH.

Use the existing owner image presign endpoint and its JPEG upload/size rules.
When `R2_PUBLIC_URL` is configured, a service photo must use that exact base and
the owning salon's `salon-images/{salon_id}/` namespace. Path traversal is rejected.
Without media configuration, schema validation still requires hosted HTTPS.
Saving a service photo creates no gallery record and changes no cover or slides.
Clearing a reference does not delete the R2 object, which could be referenced elsewhere.

All four service presentation queries (owner list, mutation refetch, public list,
bulk public list) return persisted photos and coalesced names. Walk-in reuses the
public list and preserves all presentation fields through serialization. Existing
public visibility requirements still apply, including active staff assignment.

Service create, update and soft removal invalidate the salon's service and detail
Redis keys and all `walkin:qr:` keys. Prefix invalidation is intentionally broad
because QR keys contain tokens rather than salon IDs. Public summary/detail HTTP
schemas do not embed services; summary starting prices read from the database.
Normal service/detail/walk-in cache TTL is 180 seconds. If Redis is unreachable,
its existing best-effort behavior applies; surviving stale keys expire within that
TTL. In-flight reads overlapping a mutation can also repopulate a key until its TTL.

Changed implementation files:

- `app/api/v1/schemas/platform.py`, `schemas/walkin.py`
- `app/api/v1/routes/owner.py`
- `app/application/use_cases/platform.py`
- `app/infrastructure/db/repositories/platform_repository.py`
- `app/domain/entities/catalog.py`
- `migrations/versions/0016_service_presentation.py`
- `tests/unit/test_service_presentation.py`
- `tests/integration/test_service_presentation_migration.py`
- `docs/SERVICE_PRESENTATION.md`, `docs/migrations/README.md`
- Repository-level `docs/frontend-integration.md`

Pre-existing committed merge markers prevented backend imports and test collection.
They were resolved in `app/core/exceptions.py`, `app/domain/entities/salon.py`,
`app/api/v1/schemas/admin.py`, `app/api/v1/routes/admin.py`,
`app/application/use_cases/admin.py`, and `tests/unit/test_booking_use_cases.py`.
Current-branch approval support and incoming admin catalog cache invalidation were
preserved. The global validation handler now serializes validator ValueErrors so
bad photo URLs produce 422 instead of a serialization failure.

## Verification

Run from `backend/`, with an explicitly disposable local PostgreSQL database:

```powershell
$env:SERVICE_PRESENTATION_TEST_DB='postgresql+asyncpg://postgres@127.0.0.1:55439/postgres'
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check --no-cache app tests migrations
.venv/Scripts/python.exe -m alembic heads
.venv/Scripts/python.exe -m alembic upgrade 0015_salon_admin_approval:0016_service_presentation --sql
```

The integration test refuses remote hosts and never reads the configured runtime
database URL. It applies the actual new revision to an isolated schema containing
an existing service, exercises actual repository INSERT/UPDATE/read SQL through
HTTP, and rolls back all fixtures. Authentication/salon lookup are test doubles;
existing authorization tests cover those separately. It checks catalog fallback,
default subcategory lookup, POST/PATCH and subsequent owner/public/walk-in reads,
photo replacement/removal, omission, override clearing, cross-salon SQL scope,
unknown-field rejection, cache invalidation, soft removal, bulk reads, catalog
preservation, and downgrade preservation of the existing row. Schema tests check
client-facing OpenAPI and malformed/oversized input.

Docker is installed but its daemon was unavailable. This change does not edit
deployment files. No production migration or release was performed.

Local results on 2026-10-08: **209 passed, 1 skipped** (the unrelated opt-in salon
approval database test), Ruff passed, and `git diff --check` passed. Alembic reports
one head, `0016_service_presentation`; offline upgrade and downgrade SQL both
generated successfully. The disposable PostgreSQL 18 server was stopped afterward.

## Commands to run only after review

Use the reviewed release image containing this revision, with existing VM secrets:

```bash
cd ~/salon-backend/backend
export SALON_API_IMAGE=REGION-docker.pkg.dev/PROJECT/salon-backend/salon-platform-api@sha256:REVIEWED_DIGEST
docker compose pull api
docker compose run --rm --no-deps api alembic current
docker compose run --rm --no-deps api alembic upgrade 0016_service_presentation
docker compose run --rm --no-deps api alembic current
bash scripts/gcp-vm-deploy.sh --pull
docker compose ps
curl --fail http://127.0.0.1:8000/health
```

Review the image digest and migration first. Apply migrations explicitly before
running the manual VM deployment script. Downgrading drops
presentation data; do not use downgrade as an unreviewed production rollback.

After release, inspect live OpenAPI for all three request properties, then save
an owner edit and compare its authoritative owner/public/walk-in refetches.
The live issue is fixed only after that verification succeeds.

## Customer and walk-in frontend handover

Customer code is in a separate repository and was not available for inspection.
If its parser strips unknown fields or its service card ignores photos, it needs
these exact contract changes in its existing service type/parser/rendering:

```typescript
// Add to the existing Service type (optional for older server responses).
photo_url?: string | null;

// Add to the existing parser's returned Service object.
photo_url: typeof raw.photo_url === "string" ? raw.photo_url : null,

// Use in the individual service card's existing image component.
const serviceImage = service.photo_url ?? existingDefaultServiceImage;

// Build the salon's category chips/groups from its returned services.
const categoryNames = [...new Set(services.map(s => s.category_name ?? "General"))];
const matchingServices = services.filter(s =>
  (s.category_name ?? "General") === selectedCategory
);
```

Keep parsing the returned `category_name` and `subcategory_name`. Custom salon
names cannot be enumerated from the global curated catalog alone. Apply the same
optional photo handling to walk-in service cards. Do not put service photos into
the salon cover or carousel. Exact frontend filenames cannot be identified from
this backend repository; no customer frontend fix has been claimed.
