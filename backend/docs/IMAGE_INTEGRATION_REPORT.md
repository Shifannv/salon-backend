# Image integration review — 2026-10-10

## Confirmed findings and fixes

Both Expo frontend repositories were available and inspected. Their shared image
processors and camera/gallery selection paths already existed; the backend encoder was
also wired into multipart and signed gateway uploads. Those components were retained.

| Finding before changes | Behavior after changes |
| --- | --- |
| Hosted/R2-looking URLs could be saved without proof of processing | New profile, gallery, staff, service and admin catalog references require owned namespace checks and signed R2 processing metadata |
| Immediate deletion could break shared references or an ambiguous database commit | Deletion is deferred to a scheduled worker, with locked committed reference checks and retry on later sweeps |
| Replaced staff/avatars and abandoned successful PUTs could accumulate | Newly managed, unreferenced objects are swept hourly after a minimum 24-hour object age |
| Every backend upload re-encoded identical processed bytes | Exact server-output hashes under the same MIME/policy/pixel limit can skip re-encoding; no client flag or image bytes are cached |
| A lost owner PUT response required a new grant/upload | One transient frontend retry reuses the same encoded bytes and grant; backend identical PUT retries succeed safely |
| Retrying gallery attachment could create duplicate rows | Same active URL attachment returns its existing row under the publication lock |
| Docs and generated descriptions still said direct R2 PUT | Descriptions now specify the backend gateway; request/response fields are unchanged |

Critical review caught two additional cases and corrected them: a stale auth avatar
snapshot could reassign a retired URL, and staff creation could reuse a gallery image
above the staff policy. Unchanged URLs are now compared under a URL lock with the current
record; gallery photos used for staff creation must meet the stricter staff policy.
Regression tests cover both. New external/unproven URL assignment intentionally returns
422; this behavior change is needed to close the publication bypass. Existing unchanged
legacy URLs and bundled avatars remain supported.

Further review found that baseline RLS permits direct Supabase media-field writes.
API-only locks would therefore be insufficient. Revision `0020_media_reference_guards`
adds shared locks to all seven tables and requires direct anon/authenticated clients to
assign new hosted URLs through the backend. This is a justified migration rather than
a new upload-session table. The worker refuses to scan/delete until the guards exist.
The migration is prepared locally and has not been applied to any database.

## Upload-path matrix

"Verified" here means source tracing plus local automated tests with mocked storage and
native image APIs. It does not mean real-device, staging or production verification.

| Path | Client processing | Backend processing | New-reference bypass protection | Verification |
| --- | --- | --- | --- | --- |
| Customer camera/gallery avatar → multipart `image` | Shared customer `processImage` | Pillow before R2 | Actor-specific key and direct profile update | Picker/service tests, real 4K HTTP/encoder test with mocked R2 |
| Owner/profile avatar → upload-url → PUT → PATCH | Shared owner `processImage(..., 'avatar')` | Signed backend gateway | Actor namespace + stored processing proof | Real gateway HTTP/encoder/publication tests with mocked R2 |
| Salon gallery/cover/profile photo | Shared owner `processImage(..., 'salon')` | Signed backend gateway | Salon namespace + proof | HTTP/encoder/publication and owner uploader/editor tests |
| Staff photo | Shared owner `processImage(..., 'staff')` | Signed backend gateway | Salon/staff namespace + proof and staff policy | HTTP/encoder, replacement and ownership tests |
| Owner service photo | Existing service uploader uses salon processing | Same gallery gateway | Salon namespace + proof | Service repository tests and backend publication tests |
| Admin category/subcategory image URL | No separate binary uploader | Must reuse a proven gallery object | Super-admin authorization + proof, with publication lock | All four catalog create/update mutations tested |
| Customer style archive | Device-local persistence | No R2 upload | Outside server media flow | Existing archive tests pass |
| Walk-in/owner QR | Server-generated response | No R2 upload | Existing QR authorization | Existing QR regression tests pass |

The source scan found no frontend privileged R2 SDK path or binary/base64 writes to
Redis. Backend regression coverage verifies processed pixels are sent to R2 and that
the tested media flows do not call Redis writes. Native camera/HEIC decoding and
orientation behavior still require device verification; mocked Expo tests are limited.

## Files changed by this task

Backend repository (`D:/salon/salon-backend`):

- API: `backend/app/api/v1/routes/admin.py`, `customer.py`, `owner.py`; `backend/app/api/v1/schemas/platform.py`.
- Application ports: `backend/app/application/ports/storage_gateway.py`, `media_references.py`.
- Application use cases: `backend/app/application/use_cases/admin.py`, `media.py`, `platform.py`, `media_publication.py`, `media_cleanup.py`.
- Infrastructure/config: `backend/app/core/config.py`; `backend/app/infrastructure/db/repositories/platform_repository.py`; `backend/app/infrastructure/media/pillow_processor.py`, `cleanup_worker.py`; `backend/app/infrastructure/r2/storage.py`.
- Operations: `backend/.env.example`, `backend/.env.gcp.example`, `backend/docker-compose.yml`, `backend/scripts/gcp-vm-deploy.sh`.
- Migration: `backend/migrations/versions/0020_media_reference_guards.py`, `backend/migrations/README.md`.
- Tests: `backend/tests/conftest.py`; `backend/tests/unit/test_image_processing.py`, `test_image_upload_replay.py`, `test_owner_use_cases.py`, `test_service_presentation.py`, `test_media_publication_safety.py`, `test_media_guard_migration.py`; `backend/tests/integration/test_media_reference_locking.py`, `test_service_presentation_migration.py`.
- Documentation: `backend/docs/DOCKER_DEPLOYMENT.md`, `IMAGE_MEDIA.md`, `IMAGE_INTEGRATION_REPORT.md`; `docs/database-plan.md`, `docs/Customer-App-Backend-API-Document.md`, `docs/Salon-Owner-App-Backend-API-Document.md`.

Owner repository (`D:/salon/salon-owner-APP`):

- `src/api/image-storage.ts`, `src/api/image-storage.test.ts`.
- `src/lib/image-processing.ts`, `src/lib/image-processing.test.ts`.
- Description-only update to `src/api/generated/schema.ts`.
- `docs/image-upload-integration.md`.

Customer repository (`D:/salon/Salon-Customer-APP`):

- Description-only update to `customer-app/src/services/api/openapi.generated.ts`.
- `docs/image-upload-integration.md`.

The customer image processors, picker changes, test files and dependency changes were
already present in the working tree before this task. They were inspected and tested,
not rewritten or attributed to this task. Existing local work was preserved.

## Actual verification results

| Repository/check | Command | Result |
| --- | --- | --- |
| Backend suite | `.venv/Scripts/python.exe -m pytest -q -rs` | 380 passed, 4 skipped, one upstream TestClient deprecation warning |
| Backend lint | `.venv/Scripts/python.exe -m ruff check --no-cache app tests migrations` | Passed |
| Migration chain | `.venv/Scripts/python.exe -m alembic heads` | Single head: `0020_media_reference_guards`; no migration applied |
| Owner full suite | `npm.cmd test -- --runInBand --watch=false` | 574 passed, 12 failed; 74 suites passed, one failed |
| Owner image tests | `npx.cmd --no-install jest --runInBand --watch=false --runTestsByPath src/api/image-storage.test.ts src/lib/image-processing.test.ts src/lib/image-picker.test.ts src/lib/image-picker.test.tsx src/api/repositories/service.repository.test.ts src/hooks/useBusinessPhotoEditor.test.ts` | 45 passed in six suites |
| Owner TypeScript | `npm.cmd run typecheck` | Passed |
| Owner lint | `npm.cmd run lint` | Passed with two warnings in unchanged onboarding code |
| Customer suite | `npm.cmd test -- --watch=false` | 233 passed, 44 suites, one snapshot passed |
| Customer TypeScript | `npx.cmd --no-install tsc --noEmit --incremental false` | Passed |
| Customer full lint | `npm.cmd run lint` | Failed: 231 errors, 78 warnings across the existing checkout |
| Customer image lint | `npx.cmd --no-install eslint src/utils/image-processing.ts src/services/supabase/profile.service.ts src/services/supabase/__tests__/profile-upload.test.ts src/services/supabase/__tests__/profile.service.test.ts src/utils/__tests__/image-processing.test.ts src/services/api/openapi.generated.ts` | No errors; generated schema is ignored by ESLint |
| Both frontend web builds | `npx.cmd --no-install expo export --platform web --output-dir .tmp/image-integration-build` in each app | Passed; customer generated artifact removed afterward |
| Shell syntax | Git Bash `-n scripts/gcp-vm-install-docker.sh` and `-n scripts/gcp-vm-deploy.sh` | Passed |
| Compose config | `docker compose --env-file .env.gcp.example config --quiet` | Passed; local Docker config access warnings |
| Docker image | `docker build -t salon-platform-api .` | Failed: Docker daemon unavailable |
| Working-tree whitespace | `git diff --check` in each repository | Passed |

Owner failures are in unchanged `tests/screens/complete-profile.test.tsx`, which expects
eight onboarding steps while the unchanged screen renders seven. No onboarding UI/test
file was changed for this task. Customer lint errors include existing ref/animation
patterns, display-name and unescaped-entity rules; they were not hidden or disabled.

All four backend skips require disposable localhost PostgreSQL: existing approval,
service-presentation and website integration tests, plus the new media lock/reference
test using `MEDIA_TEST_DB`. This limits confidence in real PostgreSQL locking, RLS and
reference SQL. R2 integration was mocked; no staging or production bucket was accessed.

## Deployment requirements and remaining limits

No new dependency or frontend API shape change was added. Review and explicitly apply
`0020_media_reference_guards` before enabling cleanup; it preserves existing media rows
and URLs. Keep
`PUBLIC_API_BASE_URL` reachable, preserve environment-driven CORS and deploy the API
together with Compose's `media-cleanup` service. Defaults are
`MEDIA_CLEANUP_GRACE_SECONDS=86400`, `MEDIA_CLEANUP_INTERVAL_SECONDS=3600`; templates
document them. The worker needs R2 List/Get/Put/Delete and an unfiltered database view
of every media reference. Cloud Run requires a separately scheduled sweep.

See [media operations](IMAGE_MEDIA.md) for policies, secret rotation and staging checks.
Legacy/unmarked objects are preserved and need a reviewed inventory before retirement.
Database triggers coordinate direct SQL/Supabase writes and block new client URL
assignments after the migration is applied. Until then, the worker refuses to delete,
and direct Data API URL bypasses remain an explicit deployment limitation. The exact-output cache
is per process: another worker or restart can still re-encode. HEIC support depends on
existing client decoder capabilities; backend HEIC rejection remains explicit.

All changes are local and uncommitted. Backend branch: `image-publication-safety`.
Both frontend branches: `image-integration-safety`. No commit, push, staging deployment,
production deployment or real-device verification was performed. The whole platform
is not claimed production-ready while these integration checks and unrelated failures
remain unresolved.
