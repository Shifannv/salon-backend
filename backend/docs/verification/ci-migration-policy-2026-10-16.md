# CI migration policy verification — 2026-10-16

All changes remain uncommitted. No production, Sydney, Cloud Run or GCP resources
were modified. Only disposable local migrations through 0037 were executed, following
explicit user approval. No shared migration, stamp, revision/SQL edit or sealed-evidence
change occurred. Redis recovery work from the preceding task was retained.

## Policy and changed paths

- `app/core/migration_policy.py` centralizes portable revision
  `0037_customer_processing_charge` and true prepared head `0040_fastapi_only_access`.
  The graph, labels and dependencies remain unchanged. CI excludes prepared 0038-0040
  because their Supabase-specific preconditions do not exist on scratch PostgreSQL.
- `migrations/env.py` checks raw targets and operation names before connecting. It
  executes the exact validated process URL, rejects URL query-routing overrides,
  implicit/programmatic head, unsupported drivers, stamp, ensure_version, prepared
  portable starting/current revisions and unapproved Mumbai execution. Mumbai offline
  SQL cannot render from base. Current restored/empty Mumbai history keeps execution held.
- `tests/integration/test_payment_ledger_sql.py`, `test_deployment_migration_chain.py`
  and `test_subscription_billing_sql.py` use the named portable policy constant and
  explicit Alembic policy arguments. The builder validates before creating its DB.
  The misleading/unused `MIGRATION_HEAD` and duplicate `_TEST_HEAD` names are removed.
- `tests/conftest.py` isolates normal dotenv files before application imports.
  The existing pytest configuration and declared asyncpg dependency are retained.
- `.github/workflows/backend.yml` names the portable target, supplies isolated test
  configuration, runs policy regressions and publishes JUnit output on failure too.
  Push/PR events test/build only. Deployment requires a manual request and explicit
  reviewed target/approval. Portable CI is not offered as a production migration policy.
- `.github/workflows/mumbai-migration-validation.yml` is manual-only, uses a separate
  protected environment and Mumbai secret, and has no scratch database service.
  `scripts/validate_mumbai_migrations.py` verifies approval/source/review/preflight
  hashes and uses READ ONLY SQL. It never runs revision SQL. Required GitHub reviewers,
  secret and approved manifest are not configured/manufactured by this local change.
- `scripts/gcp-vm-release.sh` has no automatic upgrade head or default approval. It
  requires explicit policy/revision/approval and mounts Mumbai evidence read-only.
  The guard inside Alembic refuses a mismatched target even if shell variables say Mumbai.
- `scripts/check-container.sh` verifies the true prepared head and checks the exact
  expected implicit-head rejection; an unrelated import/connection failure is not a pass.
  `alembic.ini` adds explicit path splitting and notes that its URL is not approval.
- Canonical migration, CI/CD, runbook and Docker docs now describe the explicit policy.
  Older feature/history references to upgrade head remain historical guidance overridden
  by [the policy](../migrations/MIGRATION_POLICY.md); they are not executable CI paths.

Tests additionally cover programmatic Alembic, cached-settings URL mismatch, routing
overrides, offline ranges, operation direction, approval evidence checksums and release
failure ordering. This is an explicit boundary, not a blanket replacement of head.

## Clean result and failures investigated

Final CI-equivalent local run: **1,031 passed, 34 skipped, zero errors/failures**,
110.06 seconds. JUnit: `.artifacts/ci-policy/portable-ci.xml`, attributes
`tests=1065`, `errors=0`, `failures=0`, `skipped=34`. Ruff, pip check, all shell syntax
checks, workflow YAML parsing, backend Docker build, image smoke and Compose config pass.
The image uses Python 3.12; host pytest used Windows/Python 3.14. This is local evidence,
not a newly executed GitHub Actions run; uncommitted changes cannot be tested by a hosted
workflow yet. One existing Starlette/AnyIO deprecation warning remains.

The 34 skips are explicit: 10 account-erasure DB checks, one media DB check, one other
isolated PostgreSQL check, two other local DB checks, and 20 Redis recovery cases.
The 20 Redis cases were separately opted in and passed, with their own zero-error JUnit.
The remaining 14 opt-in tests are not counted as passes.

The historical 18 setup-error consumers are seven image-archive cases, nine original
release-script cases and two migration-tool temporary-output cases. They all depend
on temporary filesystem fixtures; these tests do not require a real Docker daemon.
Their current suites (37 cases including four new release-guard cases) collect and
pass in the complete run. Protected old temporary directories were observed, but the
exact old failing traceback is not available in the inspected logs. Therefore a specific
historical permission cause is not asserted as proven. Current collection/setup errors: 0.
An earlier claim that these errors required a Docker socket was unsupported and is not
used as the diagnosis.

During this work, two payment logging assertions failed after new in-process Alembic
tests ran. Root cause: Alembic fileConfig disabled existing loggers. Setting
`disable_existing_loggers=False` preserves logging; both assertions and the full suite
pass unchanged. The failed run was 2 failed / 1,026 passed / 34 skipped; it is not hidden
or counted as green. Review also found and closed the URL, alias, traversal and unknown
operation bypasses listed above. No test was xfailed or weakened to hide these defects.

## Redis and fresh Mumbai acceptance

Snapshot validation, reconnect retry, uncached booking/availability and durable app/QR
idempotency remain intact. Dedicated recovery result: **20 passed**, including real OS
processes, dropped TCP commands, a partitioned/exited writer, independent committed
PostgreSQL sessions, app/QR duplicate retry and notification stability, and browser fixtures.

Fresh actual customer and owner apps were launched locally with only public Mumbai
configuration. Real synthetic Supabase JWTs and the local API connected to Mumbai.
All **11 real-app Playwright assertions passed**, with zero Realtime sockets. API checks
include booking/availability refresh, owner visibility/isolation, collection-before-
completion, exactly one manual receipt, cancellation/no-show, and Redis-off duplicate
booking (two requests, one ID/row). Collection is an actual owner API flow, not a claim
that collection was exercised through owner UI controls.

Fresh live report: **18 passed, 2 blocked, zero failed**. The runner correctly exits 1
because blocked checks do not pass acceptance. Blocked: independent committed-connection
concurrency on live Mumbai (rollback fixture serializes one connection), and real provider
failure/refund settlement (no synthetic sandbox, providers disabled). Independent committed
concurrency passed separately on disposable PostgreSQL; that is not live Mumbai evidence.

The initial browser attempt failed due to an outdated date-label selector. The runner
now uses the existing day test ID; frontend source was not changed. Final browser flows
pass, but customer Metro console still reports an existing unexpected text-node error at
`HomeScreen.tsx:207`. Page-error listeners reported zero; that does not prove console-error
absence. This UI issue was not hidden or fixed as part of backend CI policy work.

Cleanup verified zero synthetic salon rows after rollback, all three synthetic Auth users
deleted and independently 404, and private session data removed. Both local Expo servers
and fixture API were stopped. No real customer/payment data or provider calls were used.

## Mumbai latency

Thirty samples per series, measured against the actual Mumbai session pooler/project.
This is a local staging FastAPI process making real Mumbai DB calls, not local PostgreSQL
numbers or a deployed Mumbai API/Cloud Run performance claim.

| Series, milliseconds | p50 | p95 | p99 |
| --- | ---: | ---: | ---: |
| Warm Mumbai SELECT 1, existing session | 43.151 | 46.078 | 46.942 |
| Warm staging FastAPI /health/db against Mumbai | 135.469 | 140.788 | 173.433 |
| Cold DB-pool staging FastAPI /health/db against Mumbai | 884.786 | 1473.618 | 3944.786 |

Cold means a fresh pool/TLS/database connection per request; Python process startup is
excluded. The deployed Mumbai FastAPI cold-start/warm latency remains unmeasured because
no separately authorized deployed staging endpoint was provided. Small-sample p99 is the
maximum of 30 observations, not an SLO. Evidence: `.artifacts/mumbai-refresh/configuration-probe.json`.

Client TLS/hostname validation passed (TLS 1.3). The pooler's database-side pg_stat_ssl
flag was false, separately recorded. Alembic history remains empty. These observations
are not concealed by successful SELECT 1 or browser results.

## Exact verification commands

From `backend/`, using dedicated disposable containers on ports 16432/16479:

```powershell
$env:MIGRATION_TEST_DB='postgresql://postgres:local-ci-only@127.0.0.1:16432/postgres'
$env:PORTABLE_CI_TARGET='0037_customer_processing_charge'
./.venv/Scripts/python -m pip check
./.venv/Scripts/python -m ruff check --no-cache app tests migrations
./.venv/Scripts/python -m pytest -q --tb=short --junitxml=.artifacts/ci-policy/portable-ci.xml
$env:RECOVERY_TEST_REDIS='redis://127.0.0.1:16479/0'
$env:RECOVERY_PLAYWRIGHT_MODULE='D:/salon/salon-QR-Walking-Web/walking-customer-web/node_modules/playwright-core'
./.venv/Scripts/python scripts/mumbai_redis_outage_checks.py --tb=short --junitxml=.artifacts/ci-policy/redis-recovery.xml
docker build -t salon-migration-policy-check:local .
& 'C:/Program Files/Git/bin/bash.exe' scripts/check-container.sh salon-migration-policy-check:local
```

Guarded Mumbai checks, with the existing private configuration consumed only in process:

```powershell
./.venv/Scripts/python scripts/mumbai_local.py --pooler --probe --performance --samples 30
./.venv/Scripts/python scripts/mumbai_frontend.py customer
./.venv/Scripts/python scripts/mumbai_frontend.py owner
./.venv/Scripts/python scripts/mumbai_refresh_checks.py --browser --acceptance
```

The last command exits nonzero for the two explicitly blocked broader acceptance gates.
An early negative CLI stamp test was rejected before connection; no stamp/history write
occurred. Subsequent stamp coverage calls only the pure policy validator.

## Migration readiness

**HELD.** Prepared 0038-0040 remain unapplied. No stamp is authorized. Empty/restored
history needs separate reconciliation review; actual approved source/preflight evidence
and protected-environment reviewer setup are still required. Live concurrency, provider
settlement and deployed staging latency limits remain explicit. No production or Sydney
deployment was triggered. Keep all changes uncommitted for owner review.

Task-owned disposable CI PostgreSQL/Redis containers were removed after verifying exact IDs and that only the default PostgreSQL database remained. Test artifacts and the local validation image remain for review. The API health follow-up is documented in [local Mumbai health recovery](local-mumbai-db-health-2026-10-16.md).
