# Mumbai staging readiness review — 2026-10-16

Decision: **HELD**. This is an evidence/code review, not a new acceptance run or deployment.
No migrations, stamp, provider calls, synthetic writes, production/Sydney requests,
Cloud Run/GCP/DNS changes or commits were performed during this review.

## Evidence examined

- [Local database health](local-mumbai-db-health-2026-10-16.md).
- [CI migration policy](ci-migration-policy-2026-10-16.md).
- [Redis recovery](mumbai-redis-recovery-2026-10-16.md).
- Older [2026-10-15 acceptance](mumbai-final-acceptance-2026-10-15.md), superseded for
  current results by `.artifacts/mumbai-refresh/staging-checks.json` (2026-10-16).
- Latest browser/configuration JSON and portable/recovery JUnit artifacts.

Latest acceptance JSON has 18 passed, zero failed, two blocked; acceptance_gate_passed
is false. All 11 browser checks pass. Cleanup records zero remaining synthetic business
rows, all three synthetic Auth identities removed, and private sessions removed.
The older cache-coherence failure is covered by the newer 20-test recovery evidence;
it must not be presented as a current failed test. The existing customer HomeScreen
console warning remains a separate UI finding, not a clean-console claim.

## Exact blocked gate 1

**Test name:** `independent_connection_concurrent_booking`.

**Recorded blocker:** "Rollback fixture serializes one database connection; committed
booking audits are immutable and cannot be cleaned without changing protections."
The overlapping HTTP test passes with 201/409 and one booking, but both requests use
the same transaction-bound factory. It cannot establish independent transaction races.

**Affected files:** `scripts/mumbai_refresh_checks.py` (factory bound to one connection
and explicit blocked result), `scripts/mumbai_acceptance_checks.py` (same-slot HTTP
scenario), `tests/integration/test_redis_recovery_sql.py` (existing independent-session
reference test), `migrations/sql/0035_booking_checkout_safety.sql` (immutable audit
protection, reference only; do not edit).

**Code fix needed:** test harness extension, not a proven booking-runtime defect.
The disposable local independent-customer test already uses two backend PIDs, a barrier,
separate sessions and one winner/one 409. Its fixture is restricted to loopback services;
do not point it at Mumbai or relabel its result.

**Environment/access missing:** a disposable isolated Mumbai Supabase test environment
with an approved synthetic-only lifecycle and whole-environment teardown. Existing shared
Mumbai fixtures intentionally roll back; committed audit rows cannot be cleaned by
deleting records under the existing protections.

**Safe fix:** prepare a separate explicitly guarded Mumbai concurrency runner against an
approved disposable Mumbai target/clone. Seed synthetic users/salon, commit setup, run
independent HTTP/session transactions synchronized before booking, record distinct
`pg_backend_pid()` values, assert 201/409 and one stored booking, verify durable replay,
then tear down the isolated environment. Do not disable audit triggers, add grants,
hard-delete shared records or use a shared transaction to claim concurrency coverage.
Provisioning/restoring that environment is separate work; this review does not authorize
schema/migration execution there.

**Existing verification command**, from `backend/`, with explicitly configured disposable
loopback PostgreSQL 16432 and Redis 16479:

```powershell
./.venv/Scripts/python scripts/mumbai_redis_outage_checks.py -k independent_customers_compete_for_same_slot_without_serialized_fixture --tb=short
```

This is local regression coverage only. **No current command closes the live Mumbai
gate.** The new target-specific runner and its cleanup must be prepared/reviewed first.
The current aggregate command below will continue to report this gate blocked.

## Exact blocked gate 2

**Test name:** `provider_payment_failure_and_refund_settlement`.

**Recorded blocker:** "No configured synthetic payment sandbox; providers remain disabled.
HTTP 503 boundaries do not verify payment failure/refund settlement."

**Affected files:** `scripts/mumbai_acceptance_checks.py` (only disabled boundary assertions
plus unconditional blocked entry), `scripts/mumbai_local.py` (`bind` requires both providers
to be `none`), `app/core/config.py`, `app/infrastructure/payments/cashfree.py`,
`app/infrastructure/payments/webhook_worker.py`, `app/application/use_cases/payments.py`,
`app/api/v1/routes/payments.py`. These runtime paths are review/verification scope, not
identified fixes. Cashfree adapter comments explicitly identify sandbox-unverified shapes.

**Code fix needed:** a separate sandbox acceptance harness and configuration guard are
required; credentials alone will not fix this gate. Runtime changes should be driven by
observed sandbox failures, not assumed necessary. Preserve the disabled-provider runner.

**Environment/access missing:** a selected provider's test account/credentials, synthetic
merchant/vendor configuration where applicable, test instruments, signed webhook delivery
to the isolated staging API and worker access for eventual processing/reconciliation.
Secrets must be entered through hidden local/provider interfaces, never chat or reports.

**Safe fix:** prepare a separate sandbox-only runner with production endpoints/live keys
rejected, `PAYMENT_ALLOW_LIVE=false`, synthetic amounts/users and cleanup evidence. Exercise
provider decline/failure, signed and replayed events, refund request plus terminal provider
refund status, ledger transitions and worker retry. Test actual settlement capability
separately: if the sandbox cannot simulate settlement, keep that portion blocked rather
than treating an accepted refund or a mock as settlement. Any temporary webhook route
needs its own reviewed staging setup; no DNS/production changes are authorized.

**Existing verification command**, with the previously prepared private Mumbai local
configuration and customer/owner apps running, from `backend/`:

```powershell
./.venv/Scripts/python scripts/mumbai_refresh_checks.py --browser --acceptance
```

This exercises the current disabled boundary and reports both gates blocked with exit 1.
It is not a provider settlement test. **No existing sandbox command closes gate 2.** A
new runnable command must accompany the reviewed sandbox harness; inventing one now
would misrepresent implementation readiness.

## Hosted CI verification

Repository: `Thameempp/salon-backend`; local branch `shifan`; inspected HEAD
`fd998648c16879d311b67ade0138183706153319`.

Read-only GitHub connector requests actually attempted:

- `fetch_commit_workflow_runs` for that SHA: GitHub API 404.
- `get_commit_combined_status` for that SHA: GitHub API 404.
- `search_branches` for shifan: repository not found.

This does not prove CI failed, passed, or has no runs. Connected-account repository
access/commit visibility is unresolved. The workflow-runs tool additionally filters PR
runs/first page, so an empty result would not establish absence of all runs anyway.
The new policy/Redis changes remain uncommitted and cannot have hosted results for the
current working tree. No workflow was triggered, retried, pushed or deployed.

Local artifacts were independently parsed: portable CI tests=1065, failures=0, errors=0,
skipped=34 (**1031 passed**); recovery tests=20, failures=0, errors=0, skipped=0.
These remain local evidence, not a hosted pass.

## Deployed target and measurements

No confirmed deployed Mumbai staging URL was found. `.github/workflows/backend.yml`
labels `https://apiv1.mudassirmhd.in` as **production**. No requests were sent there.
The ignored local configurations provide localhost API URLs; the probe artifact explicitly
identifies `http://127.0.0.1:8056`. A Supabase project origin is not a deployed FastAPI URL.
The user confirmed after this review that no deployed Mumbai staging API exists or has
been verified. The authorized target is local only: `http://localhost:8000`, backed by
Mumbai Supabase project `wqjlgpnbiapcrlkxumcp` in `ap-south-1`; local `/health/db` is 200.
The production URL remains excluded. A deployed URL must only be reported after a
separately authorized staging deployment is created and verified.

| Requested deployed check | Result |
| --- | --- |
| Mumbai staging API URL | Blocked: no confirmed deployed staging endpoint |
| Deployed `/health` | Not attempted without confirmed target |
| Deployed `/health/db` | Not attempted without confirmed target |
| Deployed Mumbai project binding | Unverified; needs redacted deployment config/log evidence |
| API p50/p95/p99 | Unmeasured for deployed staging |
| DB acquisition time | Unmeasured for deployed staging |
| Redis latency | Unmeasured for deployed staging |
| Error rate | Unmeasured for deployed staging; no traffic denominator |

Existing evidence confirms the **local** API/runner connects to Mumbai project
`wqjlgpnbiapcrlkxumcp`, Session Pooler `aws-0-ap-south-1.pooler.supabase.com:5432`, scoped
user, verified client TLS. It cannot establish a remote deployment's target.

Previously recorded 30-sample percentiles, milliseconds:

| Series | p50 | p95 | p99 | Scope |
| --- | ---: | ---: | ---: | --- |
| Warm SELECT 1 | 43.151 | 46.078 | 46.942 | Real Mumbai DB from this workstation |
| Warm `/health/db` | 135.469 | 140.788 | 173.433 | Local staging FastAPI calling Mumbai |
| Cold DB-pool `/health/db` | 884.786 | 1473.618 | 3944.786 | Fresh DB/TLS pool, excludes Python startup |
| `/health/redis` | 5.630 | 6.821 | 7.042 | Local FastAPI and loopback Redis, whole endpoint |

The Redis series is neither remote Redis command duration nor Mumbai deployment latency.
Local latest one-off health timing recorded app153.88/db-acquire98.22/SQL55.07 ms and
one query; it is not an acquisition percentile series. Existing summaries do not provide
a deployed error-rate denominator. No deployed metric is substituted with these numbers.

After endpoint confirmation, safe measurement is 30 sequential read-only GETs per health
route with no redirects to unconfirmed hosts, recording status/request ID/wall time and
Server-Timing `db_acquire`/`redis`. Use `/health/redis` to exercise Redis: zero `redis` on
`/health/db` merely means Redis was not measured there. Report error count/attempt count
and nearest-rank p50/p95/p99; 30-sample p99 is the maximum and not an SLO. Confirm project
binding through redacted deploy configuration; a health 200 alone cannot identify it.

## Exact next access and approvals

1. Continue local Mumbai verification only. Deployed checks are deferred because no
   deployed staging API exists. Creating one requires separate deployment authorization;
   Cloud Run, production and other remote configuration changes remain outside the
   current scope. After an authorized deployment, verify its project binding and health
   before reporting a URL or remote latency.
2. Enable GitHub connector read access to this repository/provide the relevant hosted
   run. A hosted check of the current changes additionally requires approval to commit
   and push the reviewed test-only branch/PR, with deployment kept disabled. No push is
   authorized now.
3. Separately approve preparation of the disposable Mumbai concurrency environment and
   sandbox-only acceptance harness, then review their exact provisioning/cleanup and
   configuration before execution. Credentials belong in hidden interfaces.

No migration-execution approval is requested or implied. Prepared 0038-0040 remain
unapplied, stamp remains forbidden, and readiness stays held until evidence and review
gates are actually satisfied.
