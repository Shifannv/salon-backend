# Image variants review and staging gate — 19 October 2026

**Original result (preserved): changes requested; staging gate closed. Do not approve a commit yet.**

**Current status: see "Post-review update" below.** The two admission findings are
fixed and covered by passing tests, and a third defect (`result_url`) found during the
later workspace partition review is corrected. The staging gate stays closed, and commit
approval stays held pending the items listed in the update.

Reviewed branch `shifan`, HEAD `619a65060c5b404284c0231a2562823db9c6e83f`.
No application code, tests, configuration, dependencies, schema, migration, frontend,
remote resource or deployment was changed during this review. Only review evidence,
this report and session notes were written. Nothing was committed or pushed.

## Findings requiring correction

1. **High — admission errors bypass CORS and request instrumentation.**
   `app/main.py:76` registers admission last, making it wrap CORS and timing.
   An oversized multipart POST from an allowed browser origin returns 413 without
   `Access-Control-Allow-Origin` or `X-Request-ID`. Browser callers cannot read its
   error/Retry-After, and the rejection bypasses normal request timing metrics.
   Put admission inside the CORS/timing wrappers and cover rejected requests with
   a permitted Origin. This does not require letting multipart parsing run first.
2. **Medium — admission errors break the shared error contract.**
   `app/infrastructure/media/admission.py:80` directly returns `{"detail": ...}`
   instead of the API's `{"error": {"code": ..., "message": ...}}` envelope.
   Reordering middleware alone does not repair that payload. Add stable codes and
   shared-envelope tests for 413/415/408/429/503.

Local reproduction used a synthetic origin and an oversized Content-Length, with
TestClient lifespan disabled. No database, Redis or storage connection occurred.
A control validation response had CORS, a request ID and the standard error
envelope; admission's 413 had none of those three properties. Evidence:
[local-review-reproduction.json](../../.artifacts/image-variants-review-20261019/local-review-reproduction.json).
Neither finding was patched because this task requests review first.

## Complete-diff scope and safety checks

The entry snapshot contains **108 changed/deleted/untracked paths**: 36 image-related
paths (including two mixed session-memory files) and 72 pre-existing unrelated
agent-tooling/payment-design paths. The image implementation itself occupies 34
application/configuration/documentation/test paths. Do not include unrelated work
in an image commit. The complete snapshot records exact paths, status, byte counts
and SHA-256 values in [change-manifest.json](../../.artifacts/image-variants-review-20261019/change-manifest.json).

- Tracked diff, untracked image sources, tests, IMAGE_VARIANTS.md, related worker,
  erasure and cleanup paths were reviewed. Existing unrelated changes were
  inventoried separately; they are not approved by this image review.
- No apparent real credentials were found in added-line/untracked-file scanning
  or the image code review. Fixture credentials are explicitly synthetic. No
  environment file was read or changed. No secret values are recorded here.
- No concrete production endpoint or bucket binding was introduced by the image
  change. Runtime R2 base/bucket remain environment supplied; live configuration
  was not inspected and must not be assumed isolated.
- No Sydney connection/project/endpoint was introduced. IMAGE_VARIANTS.md names
  Sydney only to record its exclusion from the previous task.
- No frontend files, requirements, pyproject, Dockerfile, application settings
  definitions, migration revisions, baseline SQL or schema files changed. Existing
  migration-design documentation edits are unrelated pre-existing work.
- New runtime configuration behavior consists of local admission/decoder defaults,
  boto connect/read/retry bounds, immutable object cache headers, and Compose's
  media-cleanup heartbeat check. No new credentials or deployment settings were set.

## Three failing tests: current versus actual HEAD baseline

The baseline was extracted into an ignored directory using a separate Git index
and the normal checkout filters. The real index/worktree was preserved. All three
tests ran in separate current/baseline subprocesses with nonexistent environment
files, localhost-only database settings and no external services.

| Test | Current | HEAD checkout | Classification |
| --- | --- | --- | --- |
| `test_fake_provider.py::test_webhook_bytes_are_deterministic_and_tampering_is_rejected` | FAIL | FAIL | Baseline checkout-sensitive test defect: `.rstrip(b"\n")` leaves CR from CRLF fixture |
| `test_fake_provider.py::test_refund_fixture_only_exists_after_explicit_simulated_processing` | FAIL | FAIL | Same baseline JSON fixture CRLF problem |
| `test_migration_tool_paths.py::test_offline_bundle_matches_sealed_files` | FAIL | PASS | Current sealed CSV has raw CRLF byte drift; not a failing clean-HEAD test |

For the CSV, current bytes contain 1215 CRLF line endings; the HEAD checkout/blob
contain 1215 LF endings. Normalizing only for comparison yields identical hashes:
`8754b967e9744bb9b816f9fe3f56bc1e1269f4d93dca014ac3a4f6a1cdb1ae3f`.
Current `.gitattributes` already requires LF for this CSV. Git's normalized diff
does not show the raw-byte drift. The generator/test and fixture source are
unchanged by image work. No sealed evidence or fixture was rewritten. The third
failure must not be described as a reproduced failing HEAD baseline.

Evidence: [current log](../../.artifacts/image-variants-review-20261019/current-three-failures.log),
[HEAD baseline log](../../.artifacts/image-variants-review-20261019/head-baseline-three-failures.log),
and the byte comparison in local-review-reproduction.json. The earlier broad unit
run's 1085 passed/3 failed count remains historical; this review reran the three
failures and focused image selection rather than claiming a new full-suite run.

## Tests and object-family results

| Check | Result and boundary |
| --- | --- |
| Focused image/ownership/profile/service/API tests | **298 passed**, one upstream TestClient deprecation warning |
| Ruff `app tests migrations`, no cache | PASS |
| Scoped whitespace check | PASS |
| CORS/request-ID/error-envelope reproduction | Confirmed regressions above |
| Three-test comparison | Current 3 failed; HEAD baseline 2 failed/1 passed |
| Mumbai staging checks | **BLOCKED / NOT RUN** by review gate |

The 298 local tests use synthetic images and stateful mocked R2. They cover avatar
512; staff 512/1024; gallery/service 400/800/1600; WebP signatures; byte caps;
orientation; transparency; EXIF/GPS removal; malformed/spoofed/SVG/animated/truncated
sources; body limits; deterministic and concurrent duplicate uploads; conditional
writes; failures at every variant/compatibility upload; lost acknowledgements;
reference rollback; cross-account rejection; shared-family protection; partial
cleanup; missing reference guards; worker heartbeat; and erasure retry.

**R2 family result:** canonical hashes/keys, signed metadata and immutable retries
pass against the fake. Signed uploads create the approved variants plus one
processed compatibility image; multipart avatar creates its one canonical variant.
No real R2 object was created, replaced or deleted. Live object/family counts: no
operations performed; no live inventory claimed.

**Publication/legacy result:** source tracing and mocks show complete-family HEAD
validation under family locks before reference writes. Failed saves preserve the
previous reference; partial families cannot be newly attached. Legacy URL fields
remain; old keys are not rewritten; v1 proofs and unchanged unmarked URLs retain
their compatibility behavior. New compatibility objects can have `.jpg`/`.png`
suffixes while serving WebP. Device compatibility remains unverified.

**Cleanup result:** mocked complete/partial retirement, shared references, grace,
retry and erasure checks pass. Family locks precede alias inventory. Existing
seven-table reference guards remain required. The real worker scans all three
managed root prefixes and has **no test-prefix filter**: never point it at a shared
bucket for isolated tests. The deletion metric counts retired candidates/families,
not individual R2 objects. No live cleanup worker was run.

**Database result:** no database contacted; no schema, migration or business-data
change. Replacement concurrency uses an explicit transaction-lock model. It is
not evidence of PostgreSQL concurrency or deployed guards. Media bypasses Redis;
local mocks assert that image bytes do not enter Redis. Live Redis/worker behavior
was not tested.

## Staging target and blocked prerequisites

The documented candidate is
`https://salon-api-mumbai-staging-jmqpp743pa-el.a.run.app`, service
`salon-api-mumbai-staging`, region `asia-south1`. This is a **documentation-derived
candidate**, not a currently verified target. No request or control-plane call was
made because review did not pass.

The 16 October deployment report records source `5df98ee...`, an older image and
no R2 configuration or media worker. It cannot establish that the present local
uncommitted family implementation is available remotely. No Cloud Run deployment
or configuration change is authorized by this task.

After fixes and a clean re-review, testing still requires proof of the serving
code, a dedicated nonproduction R2 bucket/credential binding, synthetic actor/salon
IDs (the supported namespace prefixes), and scoped worker/fault-injection access.
Arbitrary `staging/...` key roots are rejected by the current namespace validator.
The staging API alone does not provide safe knobs to force partial R2 failures or
DB rollback. No real users, shared production bucket, migrations, CDN purge or
deployment may be used to manufacture that evidence.

## Remaining risks and commit recommendation

Hold commit approval until the two admission regressions are corrected and tested.
Resolve the sealed CSV checkout-integrity issue separately without silently
rewriting sealed evidence. Keep unrelated changes out of the image commit.

Residual design limits are process-local rate/capacity controls and proxy-IP
aggregation; native-thread timeout without termination; 10000-object namespace
inventory cutoff/cost; old-writer rollout coordination; and unverified origin/CDN
erasure behavior under one-year immutable cache headers. A future policy version
also needs family-lock detection updated: it currently hardcodes `/webp-v2/`.
An externally removed erasure anchor leaves siblings to ordinary cleanup.

No claim is made about production R2 safety, CDN purge behavior, Cloud Run behavior,
PostgreSQL concurrency, device compatibility, or a successful staging release.

## Post-review update — 19 October 2026 (later session)

The sections above are the original review and are kept as evidence. Nothing above was
edited except the status banner at the top. This update records what changed afterwards
and what was re-verified. It is a self-check by the implementer, not an independent
re-review.

### Admission findings 1 and 2: resolved, verified by tests

The fix changed `app/main.py` (middleware order is timing, then CORS, then admission),
`app/core/exceptions.py` (new `PayloadTooLargeError`, `UnsupportedMediaTypeError`,
`RequestTimeoutError` and a shared `app_error_response`), `app/infrastructure/media/admission.py`
and `tests/unit/test_media_admission_http.py`. `exceptions.py` and the HTTP test were
**not** in the entry file list below because they were added after this review.

Re-verified now: `test_media_admission_http.py` asserts the standard
`{"error": {"code", "message"}}` envelope, `Access-Control-Allow-Origin` for an allowed
origin (and its absence for a disallowed one), the request ID, `Retry-After`, shared
handling for 413, 415, 408, 429 and 503, and unchanged production Server-Timing privacy.
Those tests pass, so findings 1 and 2 are marked resolved. The original reproduction
evidence is unchanged.

### New defect found by the partition review: `result_url` was an upload capability

`result_url` was set equal to the signed PUT `upload_url`, so the "read" link carried the
upload capability and the GET endpoint lived on the upload path. Corrected:

- `result_url` is now a separate read-only URL on `/v1/media/results/{token}`, signed in
  its own domain (`image-result-v1:`), so it cannot upload and an upload token cannot read.
  It expires with the grant (300 seconds).
- The GET route moved from `/v1/media/uploads/{token}` to `/v1/media/results/{token}`; the
  upload path is PUT-only. The PUT response `Link` header now points to the result URL,
  never to the upload URL.
- Files changed for this: `app/api/v1/routes/media.py`, `app/api/v1/schemas/platform.py`,
  `app/application/ports/storage_gateway.py` (new `get_result_url`),
  `app/application/use_cases/platform.py`, `app/infrastructure/r2/storage.py`,
  `app/infrastructure/r2/families.py`, `app/infrastructure/media/admission.py`
  (metadata admission now matches the results path), `docs/IMAGE_VARIANTS.md`, and tests
  `test_image_families.py`, `test_media_admission_http.py`, `test_media_additional_guards.py`
  and `test_owner_use_cases.py`. New tests cover: a result token cannot PUT, an upload
  token cannot read results, the result URL expires with the grant, and the `Link` header.
- Remaining limit: the upload token itself stays valid for repeat PUTs until its 300-second
  expiry, as before (repeating the same upload is idempotent by design).

### Compose healthcheck: risk documented, behaviour not verified

The `media-cleanup` healthcheck in `docker-compose.yml` is unchanged in this update. The
deploy script runs `docker compose up -d --wait --wait-timeout 120`, and the heartbeat is
written only when a full sweep completes, so a slow first sweep, a missing
`0020_media_reference_guards`, or one persistently failing object can fail an otherwise
good deployment. The risk is written up in `docs/DOCKER_DEPLOYMENT.md`. Verifying it needs a
disposable Compose project and is not done here. Until then the healthcheck hunk should
not be committed with the image fix.

### Test results in this update

| Check | Result |
| --- | --- |
| Focused image/media/ownership/R2/owner selection (13 files) | 252 passed |
| Full `tests/unit` | 1099 passed, 3 failed (the same three known failures below) |
| Ruff `app tests migrations` | passed |
| The three failures | unchanged: two `test_fake_provider` CRLF-fixture tests and `test_offline_bundle_matches_sealed_files` (sealed CSV CRLF drift). Not touched; sealed evidence not edited. |

Pytest's default temp directory is not writable in this Windows profile, so tests that use
`tmp_path` were run with `--basetemp` pointing at a scratch directory. This is an
environment issue, not a code issue.

### Blockers that remain

1. The sealed CSV checkout-integrity issue (separate task; no sealed file rewritten).
2. The Compose healthcheck decision above.
3. An independent re-review of the admission fix and the `result_url` change.
4. All staging prerequisites in the "Staging target and blocked prerequisites" section:
   serving-code proof, a dedicated non-production R2 bucket (none is documented or
   verified), and scoped worker and fault-injection access. No staging traffic was sent.

### Files changed after review entry (in addition to the entry list)

```text
backend/app/core/exceptions.py
backend/tests/unit/test_media_admission_http.py
backend/tests/unit/test_owner_use_cases.py
```

The other `result_url` files listed above were already in the entry list.

## Addendum — independent review blockers fixed (19 October 2026)

An independent review of the update above found two blockers. Both are corrected. The
text above is unchanged and remains the history.

- **PUT could store objects and then return 422.** `routes/media.py` derived the result
  link from `str(request.url)`, and `get_result_url` re-checked the upload token's expiry.
  A query string on the PUT URL, or the clock crossing the 300-second boundary while the
  family was being stored, produced a 422 after a committed upload. Now the link is derived
  from the validated path token; `get_result_url` verifies signature, bucket and path
  policy but not expiry (the result token carries the original expiry, so nothing is
  extended); and a failure to derive the link can never become an error response.
  Expiry crossed *during processing* (before storage) still fails closed with 422 and
  stores nothing. Upload and result tokens remain separate signature domains.
- **Regression tests added** (`tests/unit/test_image_families.py`): PUT with a query
  string; expiry crossed during processing (nothing stored); expiry crossed during storage
  (204 and a link, with the upload capability and the result link then expired); link
  derivation failure; and token-purpose separation. The query-string and storage-crossing
  tests were confirmed to fail against the previous behaviour.
- **Compose healthcheck removed from the image work.** `docker-compose.yml` and
  `docs/DOCKER_DEPLOYMENT.md` are back to HEAD, so `media-cleanup` keeps its healthcheck
  disabled. `health.py` and the heartbeat write remain in the image code but nothing in
  Compose checks them. The deploy-script risk described above stays valid and
  unverified; wiring the healthcheck needs its own change after a disposable Compose test.
- **Still open:** independent re-review of this fix, the sealed CSV newline issue, and all
  staging prerequisites listed above. No staging traffic was sent.

## Exact image-related files at review entry

```text
backend/app/api/v1/routes/media.py
backend/app/api/v1/schemas/image_family.py
backend/app/api/v1/schemas/platform.py
backend/app/application/ports/image_processor.py
backend/app/application/ports/storage_gateway.py
backend/app/application/use_cases/account_erasure.py
backend/app/application/use_cases/media.py
backend/app/application/use_cases/media_cleanup.py
backend/app/application/use_cases/media_publication.py
backend/app/application/use_cases/platform.py
backend/app/infrastructure/db/repositories/platform_repository.py
backend/app/infrastructure/media/admission.py
backend/app/infrastructure/media/cleanup_worker.py
backend/app/infrastructure/media/health.py
backend/app/infrastructure/media/pillow_processor.py
backend/app/infrastructure/r2/families.py
backend/app/infrastructure/r2/storage.py
backend/app/main.py
backend/docker-compose.yml
backend/docs/DOCKER_DEPLOYMENT.md
backend/docs/IMAGE_MEDIA.md
backend/docs/IMAGE_VARIANTS.md
backend/tests/integration/test_account_deletion_sql.py
backend/tests/unit/media_r2_fake.py
backend/tests/unit/test_account_erasure.py
backend/tests/unit/test_image_families.py
backend/tests/unit/test_image_processing.py
backend/tests/unit/test_image_upload_replay.py
backend/tests/unit/test_image_variants_processor.py
backend/tests/unit/test_media_additional_guards.py
backend/tests/unit/test_media_admission.py
backend/tests/unit/test_media_cleanup_health.py
backend/tests/unit/test_media_integration.py
backend/tests/unit/test_media_publication_safety.py
docs/agent-memory/SESSIONS.md
docs/agent-memory/progress/shifan.md
```

This review adds the present report and ignored evidence under
`backend/.artifacts/image-variants-review-20261019/`, and appends the result to the
two session-memory files. Application files are unchanged from the entry manifest.
