# Final Mumbai local staging acceptance - 2026-10-15

**NOT READY for migrations.** 0038-0040 remain unapplied and no Alembic stamp was
run. This run intentionally exits nonzero for a real failed acceptance check.
No Sydney, production, GCP, Cloud Run, DNS, client grants or application-runtime
fixes were made in this turn. Earlier uncommitted refresh work and the concurrent
settings-validator change were preserved. No commit or history rewrite was made.

Authorized local cleanup is recorded separately in
[cleanup results](mumbai-cleanup-results-2026-10-15.md).

## Final result

The combined real Mumbai API/JWT/Redis runner recorded **18 passed,
1 failed, 2 blocked** checks. Its Playwright aggregate
contains **11 passed, zero failed** real-app checks. The separate ordinary backend
suite passed **922 tests, with 62 skips**. Compile, Ruff and 17 migration-tool path
checks passed. Native was not run: `adb devices -l` lists no device/emulator.

| Requested behavior | Observed result |
| --- | --- |
| Two simultaneous HTTP bookings, same slot | 201 and 409; one booking row. Real requests/JWT/Postgres; DB sessions serialize in the rollback fixture. |
| Independent-connection concurrent booking | BLOCKED. No competing committed transaction claim; see fixture limitation below. |
| Same idempotency key retry, Redis healthy | PASS; same booking ID. |
| Same idempotency key retry, Redis unavailable | PASS; two requests, one distinct booking ID and one row for the slot. Isolated Redis was paused, commands timed out, and Postgres replay remained authoritative. |
| Multi-process Redis outage cache coherence | FAIL. Two real runtime-cache processes and dropped TCP commands reproduce stale payload after reconnect. |
| Pending -> confirmed -> checked-in -> collected -> completed | PASS through real HTTP/API/SQL; customer GET observes transitions. Collected is payment_status=paid, not a booking-status enum. |
| Duplicate cash collection / completion guard | PASS; one manual receipt, repeated key stays paid, completion before collection returns 409. |
| Customer cancellation | PASS through API. |
| No-show | PASS; early no-show returns 422, then only the synthetic appointment clock is moved into the past and API marks no_show. |
| Payment/refund disabled boundary | PASS; payment config is disabled, intent/refund endpoints return 503, zero provider calls. |
| Actual gateway payment failure/refund settlement | BLOCKED; no synthetic provider sandbox is configured. A 503 boundary is not settlement coverage. |
| Customer refresh after owner mutation | PASS in API and mounted browser listing/availability. |
| Owner refresh after customer booking | PASS in API and mounted owner browser list. |
| Playwright refresh/failure/retry | PASS, all 11 checks; zero Supabase Realtime sockets, zero page-error events. |
| Native flow | Not run; no real emulator/device attached. |

## Redis failure and decision

Two independent OS processes warm the same real runtime cache payload through two
loopback TCP forwarding gates to the verified isolated Redis at 127.0.0.1:16391.
Both TCP paths are then cut; new invalidation commands are dropped before reaching
Redis. No business response is mocked and this cache-layer test makes no DB writes.

The invalidating process sets its local cache-safe flag false and bypasses payload
reads. The other process experiences a miss during the outage but retains its
cache-safe flag. After TCP recovery it returns the old payload because the shared
epoch never advanced. A later successful global invalidation clears the snapshot
for both processes. Thus the current protection is insufficient across processes
when an invalidation is lost. Availability/bookings remain uncached, and the Redis-off
booking retry did not duplicate a booking; that does not repair stale salon/catalog
read models.

A first paused-server probe was discarded as proof of lost invalidation: Redis can
execute a timed-out SET after unpausing, hiding this failure. The final TCP-drop
probe prevents that false pass. Runtime code was not changed under cleanup/test-only
authorization. Durable/shared invalidation recovery needs a separate fix and rerun.

## Isolation, concurrency limits and cleanup

- Exact Mumbai project: wqjlgpnbiapcrlkxumcp. Auth/JWKS use that project's HTTPS host;
  the guarded local API connects to the project-scoped Mumbai session pooler.
- Real synthetic Auth JWTs are verified by the API. Owner/customer direct booking-table
  reads remain denied; no grants were added. Only synthetic users/records were used.
- Business fixtures share an outer rollback transaction, and API commits release
  savepoints. The fixture serializes sessions to keep that connection valid. Concurrent
  HTTP requests prove one stored result under this harness, not independent transaction
  scheduling or committed lock behavior. Committing fixtures would leave immutable
  audit records; no audit protection or cleanup rule was bypassed to force a pass.
- Final cleanup verified zero synthetic salon fixture rows, deleted all three synthetic
  Auth users and independently observed 404, and removed private session tokens.
- The isolated Redis container was identity/binding checked, restored unpaused/running,
  and flushed to DBSIZE zero. The pre-existing Redis was untouched. TCP gates and child
  cache processes closed; fixture API and both Expo servers stopped.
- Local staging configuration remains ignored. No production/provider credentials
  were passed to app browsers. IDs/results remain in ignored private evidence.

## Evidence and re-run

Live results: `backend/.artifacts/mumbai-refresh/staging-checks.json`,
`browser-results.json`, `multi-process-redis-outage.json`, `redis-cleanup.json`.
Ordinary suite/cleanup evidence: `backend/.artifacts/cleanup-2026-10-15/`.
The final runner is `backend/scripts/mumbai_refresh_checks.py --browser --acceptance`;
start the two local Expo apps using public-only Mumbai configuration first.
`mumbai_acceptance_checks.py` adds lifecycle/outage booking tests;
`mumbai_redis_outage_checks.py` owns the two-process TCP fault probe. These helpers
never call migrations or Alembic. The timestamp count-query error in the first
Redis-off attempt was a test-harness binding error; the final corrected run verifies
both identical response IDs and the single SQL row.

The earlier [refresh report](mumbai-local-refresh-results-2026-10-15.md) records
implementation details, keys and latency. This final report supersedes its previously
unverified outage/lifecycle coverage and its earlier staging counts.

Full migration readiness remains **NO**: resolve the cache-coherence failure, prove
independent-connection concurrency using cleanup-safe isolation, and verify provider
failure/refund settlement with synthetic sandbox resources where required. Native
coverage can run when real hardware/emulation exists. Do not apply 0038-0040 or stamp
history on the basis of the partial passes above.
