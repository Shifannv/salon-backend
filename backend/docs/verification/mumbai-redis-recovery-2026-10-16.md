# Redis recovery verification — 2026-10-16

Implementation and local verification only. Mumbai migration execution remains held.
No 0038–0040 application, stamp, remote database mutation, new client grants, Sydney,
production, GCP, Cloud Run, DNS or production frontend changes were performed.
Only synthetic disposable PostgreSQL data and dedicated loopback Redis were used.
Teardown confirmed no remaining `redis_recovery_*` databases, then removed only the
two identity-verified disposable recovery containers and their test volumes. Existing
backend containers and the earlier Mumbai loopback Redis container were preserved.

## Root cause and design decision

The original two-process TCP-drop reproduction returned the old payload in process B
after process A committed a mutation but failed to change `read-model:epoch:v1`.
A's unsafe flag existed only in its memory; B retained the old Redis epoch. A also
never retried. Pausing Redis is insufficient fault injection because timed-out commands
can execute after unpause; the regression tests drop TCP before commands reach Redis.

The existing implementation now validates cache generations against PostgreSQL
snapshot visibility, retaining the Redis epoch for normal invalidation and recovery.
`get_cache` binds validation to the route's existing primary READ COMMITTED session.
`read_cache_snapshot` reads database name and `pg_current_snapshot()` without assigning
an XID. Its digest is part of each public payload's v2 key. Committed writes change
snapshot eligibility even if the writer is partitioned, exits, or never retries.
Own-XID, repeatable-read/serializable, replica and failed validation paths bypass cache.
Snapshot components and visibility semantics are described in the
[PostgreSQL documentation](https://www.postgresql.org/docs/16/functions-info.html#FUNCTIONS-PG-SNAPSHOT).

The full snapshot matters: using only xmax misses commits of an older in-progress
transaction. A real PostgreSQL regression keeps an older transaction open while another
commits, and checks both the before/during snapshots differ from the after snapshot.

This chooses cache version validation over an outbox. It needs no schema, migration,
new grants or worker. A Redis-only reconnect flush cannot protect a healthy reader
from a partitioned writer that never reconnects. Correctness does not depend on the
pending invalidation flag surviving a crash. There is no claim of a durable retry queue.

On a Redis error the process marks public read generations unsafe. A validated read
or health ping retries the epoch update before admitting payload hits. Failed invalidation
returns false and emits a warning; the already-committed mutation is not reported as
rolled back. Explicit deletes retain warning/pending state and strict erasure failures
propagate. Startup failures retain the client for reconnect. Late fills stay bound to
their original snapshot/epoch; old payloads expire by TTL. No FLUSHDB/FLUSHALL is used.

## Additional gaps closed during review

- Fixed logical-key cleanup after GET failure: the version dictionary is indexed by
  logical keys, not the transformed physical key.
- Added Redis invalidation timing without counting reconnect invalidation twice.
- Aligned `available` with configured-client semantics. The erasure worker now pings
  before destructive work, preserving its pause behavior during startup/runtime outages.
- QR booking retries previously depended entirely on Redis. They now use the existing
  PostgreSQL idempotency ledger, scoped by actor and a SHA-256 hash of the QR token.
  Publication/salon authorization still precedes replay. Redis booking replay is bypassed.
- Replayed bookings carry an internal outcome marker, consumed before HTTP serialization,
  so app/QR retries do not create extra owner/customer notifications.

QR keys now follow the existing database gate's 8–200 character bound and 24-hour
retention. Payload mismatch returns `idempotency_key_reuse`. Old Redis-only QR attempts
have no durable ledger entry; their original 60-second replay window cannot be recovered
from PostgreSQL during cutover. Plan a quiet cutover and replace all older processes.

## Cache keys affected

| Logical keys | Behavior |
| --- | --- |
| `salon:{id}:detail`, `:services`, `:staff` and other `salon:*` | PostgreSQL snapshot + Redis epoch validation |
| `catalog:categories:active`, `catalog:subcategories:active:{id}` | Same validation |
| `walkin:qr:{token}` | Same validation plus current publication checks |
| `availability:*`, `slot:*`, `slots:*`, `booking:*`, `bookings:*` | Payload reads/writes bypass Redis |
| `idempotency:*`, `rate:*` | Not flushed by public generation recovery; bookings use the DB ledger |

Physical public payloads use `read-model:v2:{snapshot_hash}:{epoch}:{logical_key}`.
Erasure prefix deletion scans both v1 and v2 physical generations. The shared Redis
epoch key remains `read-model:epoch:v1`; changing it does not erase replay/rate keys.

## Verification and scope

Dedicated command: `python scripts/mumbai_redis_outage_checks.py --tb=short` from
`backend/`. Requires explicit `MIGRATION_TEST_DB` pointing at disposable loopback
PostgreSQL port 16432 and `RECOVERY_TEST_REDIS=redis://127.0.0.1:16479/0`.
Set `RECOVERY_PLAYWRIGHT_MODULE` to an installed Playwright module if it is outside
this checkout; otherwise Node resolves `playwright`. The launcher does not consume
Mumbai configuration or ordinary environment files. It builds a unique local database
through **0037 only**, and drops it in teardown. It never upgrades to `head` or stamps.

The dedicated suite passed **20 tests**, including:

- Twelve two-process cases: salon/service/staff/catalog logical keys, with both TCP
  paths cut, only the writer cut, and writer exit after commit. B reads before A can
  recover; stale payloads are rejected and A's later invalidation retry is checked.
- PostgreSQL snapshot change with an older transaction kept open.
- App and QR concurrent HTTP bookings during Redis failure: separate booking sessions
  hold distinct PostgreSQL backend PIDs before either proceeds; results are 201/409.
  Duplicate retry returns the same booking, payload mismatch returns 409, one booking
  remains, notifications do not increase, and availability excludes the occupied slot.
- Different customers compete for the same slot through independent committed sessions
  and the actual `create_booking` function: exactly one succeeds. No fixture lock or
  shared rollback/savepoint connection serializes them.
- Four actual HTTP + Playwright refresh cases for salon, catalog, staff and services.
  Browser reload observes the committed mutation while the writer cannot invalidate
  Redis. Request IDs and Server-Timing remain present.

Browser coverage uses a small loopback fixture page fetching the real FastAPI routes.
It does **not** establish a fresh full customer/owner application acceptance run.
Authentication is overridden with synthetic actors in local HTTP tests; this does not
retest Supabase JWT/JWKS. Previously recorded Mumbai/real-app evidence remains historical.
No real customer or payment data or provider calls were used.

Unit coverage additionally exercises late fills, unsafe database contexts, overlapping
request contexts, unavailable validation, startup reconnect, invalidation logging/retry,
strict erasure and erasure-worker pause/recovery. Final ordinary suite: **948 passed,
82 skipped, zero failures** (61.14 seconds); the 82 skips include the 20 dedicated
checks separately opted in above, plus 62 other database integration checks not run
here. One existing Starlette/AnyIO deprecation warning remains. Ruff
`check --no-cache app tests migrations` and `git diff --check` pass.

## Latency

Latest dedicated run: 12 samples per public endpoint (one cold, eleven warm), loopback
HTTP/Redis/PostgreSQL on this Windows host. These are exploratory measurements, not
Mumbai network latency, a production SLO, or a load test.

| Path | Cold ms | Warm p50 ms | Warm p95 ms |
| --- | ---: | ---: | ---: |
| Catalog | 404.37 | 21.95 | 23.59 |
| Salon | 474.07 | 24.01 | 44.73 |
| Services | 494.12 | 22.77 | 25.07 |
| Staff | 371.66 | 25.44 | 64.33 |

Outage HTTP bookings: app 201/409 took 796.55/301.03 ms; QR 907.05/296.77 ms.
Duplicate retries took 33.98/40.34 ms; reconnect epoch retry took 21.01/40.13 ms.
Fault clients use 0.3-second socket settings with immediately dropped TCP commands;
runtime clients retain their existing 2-second socket settings. These results do not
bound stalled-network runtime latency. Measurements are in ignored
`backend/.artifacts/redis-recovery/*-latency.json`.

The design adds one PostgreSQL round trip per eligible cache read and conservatively
misses after unrelated writes. Measure Mumbai latency before any deployment. If this
is too expensive, separately prepare/review a durable per-resource version or outbox
migration; do not replace validation with a Redis-only epoch.

## Migration and rollback

**No migration needed or added. 0038–0040 remain unapplied by this work.** No new
Supabase table grants. Migration sources and sealed review evidence were not modified.

Replace all API/worker processes when deploying; legacy readers do not gain snapshot
validation from new writers. Rotate/clear only public payload namespaces when restoring
a database or switching clusters; database names/snapshot values are not cluster IDs.

Rollback must keep payload caching bypassed: route reads to PostgreSQL and remove
public payload cache reads/writes before restoring a prior build. Do not simply revert
to the unsafe Redis-only reader with old payloads present. Preserve the existing durable
booking idempotency ledger and keep QR retries on its durable path. No SQL downgrade or
stamp is needed. Nothing was deployed during this work.

## Files changed in this continuation

Runtime: `api/v1/routes/walkin.py`, `application/ports/cache_gateway.py`,
`application/use_cases/{platform,walkin}.py`, `infrastructure/cache/redis.py`,
`infrastructure/account_deletion/worker.py`, and
`infrastructure/db/repositories/platform_repository.py` under `backend/app/`.
The snapshot provider/session binding in `infrastructure/db/session.py` and `api/deps.py`
were already committed when this continuation started and were reviewed/tested.

Verification: `backend/scripts/mumbai_redis_outage_checks.py`,
`backend/tests/integration/{test_redis_recovery_sql.py,cache_recovery_worker.py,redis_recovery_browser.cjs}`,
`backend/tests/unit/{test_cache_recovery.py,test_walkin_use_cases.py,test_website_contract.py}`,
this report, `backend/docs/ARCHITECTURE.md`, and current branch/session memory.

Review caught and fixed duplicate notifications, worker reachability semantics,
logical-key cleanup and timing. Early harness failures (extra dependency sessions,
PostgreSQL background-write cache misses and an open Node stdin handle) were corrected;
the final dedicated run has zero failures. No skipped or historical result is counted
as fresh live Mumbai or full-app evidence. Migration execution remains held.
