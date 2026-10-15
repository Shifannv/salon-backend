# Mumbai local refresh implementation and verification - 2026-10-15
Final follow-up: [2026-10-15 acceptance](mumbai-final-acceptance-2026-10-15.md) verifies lifecycle and Redis-off idempotency but reproduces a cross-process cache-coherence failure. That report supersedes the earlier outage/lifecycle limitations and counts below; migration readiness remains NO.

Acceptance is **held**. Migrations 0038-0040 and Alembic history were not changed. No grants, Sydney, production, Cloud Run or DNS changes were made. No Git write/commit commands were issued by this agent; the owner changed/committed the shared backend checkout during this work. Earlier Git-uncommitted statements are historical, not a description of current HEAD.

## Targets and isolation

- Project: `wqjlgpnbiapcrlkxumcp`; Auth/JWKS: `https://wqjlgpnbiapcrlkxumcp.supabase.co` and `/auth/v1/.well-known/jwks.json`.
- Local API: `http://127.0.0.1:8056`; customer Expo web: `http://localhost:8081`; owner: `http://localhost:8082`.
- Database: Mumbai session pooler `aws-0-ap-south-1.pooler.supabase.com:5432`, with the project-scoped username verified before connection. Direct database DNS was unavailable on this workstation.
- Redis: newly created `salon-mumbai-refresh-redis`, bound to `127.0.0.1:16391`, separate from the pre-existing Redis container. The first attempted port was in a Windows reserved range; no paid infrastructure was created.
- The deliberately inspected Mumbai credential fields were copied into ignored `backend/.env.mumbai-local`. The guarded launcher sets `SALON_ENV_FILE` explicitly; runtime does not fall back to `backend/.env`. Frontend processes receive public configuration only, with `EXPO_NO_DOTENV=1`.
- Service-key claims are screened for the project/role; real Admin authorization is separately verified with a missing synthetic UUID, without reading real users. Wrong Auth/JWKS/database region guards have unit tests and do not depend on Python assertions.
- Client-to-pooler TLS 1.3 verifies the certificate and hostname against Supabase's published CA. That CA lacks keyUsage, so strict-X509 compatibility is disabled only for this staging configuration; certificate/hostname verification remains enabled. `pg_stat_ssl` reports the pooler-to-database hop as non-TLS; do not confuse it with the verified client connection.
- Providers, email and push credentials are disabled in the staging configuration. No workers or real payment/email/push flows were started.

## Implemented refresh behavior

| Surface | Healthy interval | Additional refresh / recovery |
| --- | --- | --- |
| Customer salon lists, detail/status, services, staff, appointment lists, inbox | 30 s, foreground mounted queries | Mount, screen navigation/focus, app resume, browser reconnect, local mutation invalidation |
| Customer availability, including modify-booking availability | 10 s | Staff/date/services change, focus/resume/reconnect, booking result, cancellation, conflict/refetch |
| Customer active booking detail | Existing 10 s opt-in polling | Stops for terminal bookings unless a request remains pending; focus/mutation still revalidates |
| Customer booking confirmation | Existing bounded 3 s loop | Existing confirmation behavior retained |
| Owner bookings, salon/services/staff, access, inbox, requests, ledger | Default 30 s; existing setting bounded 10-120 s | Mount, route focus, resume, NetInfo reconnect, mutations; booking-poll success also invalidates dependent availability/access/ledger/request/inbox queries |
| Owner availability | 10 s | Focus/reconnect and mutation invalidation; independent of bookings polling |

Read retries are bounded to two, with 750 ms then 1,500 ms delays (4 s delay cap). Existing non-retryable auth/validation/conflict/rate-limit behavior remains; writes are not newly queued/replayed. Failed polling backs off up to 120 s; successful reads return to the healthy interval. Queries deduplicate by key and pause background polling. Owner booking/block polling also observes its existing route visibility gate.

Availability failures/paused reads expose no selectable saved slots. Customer and owner have explicit retry controls. Saved display data on other screens follows existing stale/error notices; public listings remain hidden while revalidating or denied. Successful salon detail stays visible while refreshing, preventing the status observer from repeatedly disabling/enabling itself. Errors and revoked visibility still hide detail data.

Customer application-table subscription facade now opens no channels. Owner's former Realtime hook reconciles successful FastAPI polls instead. Supabase Auth/session handling remains. Real client JWTs are denied direct booking-table reads with SQLSTATE 42501; no positive client grants were added. Final source inspection found no application-table subscriptions or direct Supabase table calls in the customer/owner application code.

## Backend cache and booking correctness

- Every shared SQLAlchemy session commit rotates `read-model:epoch:v1` **after** DB commit. API and worker sessions use this factory. This is deliberately broad, including quota commits; assess cache hit/load impact before any production rollout.
- Logical payload families: `salon:<id>:detail`, `salon:<id>:services`, `salon:<id>:staff`, `catalog:categories:active`, `catalog:subcategories:active:<category>`, `walkin:qr:<token>`.
- Physical payload keys: `read-model:v1:<epoch>:<logical-key>`. Atomic Redis compare-and-set rejects a late fill from an old epoch. Retired generations expire at their existing 180/300 s TTLs. Routine commit invalidation is one namespace update, without a keyspace scan. Explicit erasure prefix deletion removes payloads across generations.
- Availability and booking payloads remain uncached. Defensive `availability:`, `slot:`, `slots:`, `booking:`, `bookings:` reads/writes are bypassed. `idempotency:*` and rate-limit keys are not retired by read-model invalidation. Existing Postgres booking idempotency remains authoritative.
- Booking submission continues exclusively through Postgres `create_booking`, which revalidates slots under its concurrency guards. Availability continues exclusively through `get_available_slots`. No Python slot generation or direct booking inserts were added.
- A live browser test exposed a real date-filter bug: `date_from/date_to` compared against the database session date rather than salon-local day bounds. The list query now uses each salon's timezone (including the exclusive next-day bound); the API describes those semantics. A real midnight fixture verifies the booking appears on the correct local day and not the previous day.
- Existing request-ID, Server-Timing and structured request-duration logging are preserved. Three actual health requests verified correlation IDs and DB/Redis/duration fields in sanitized JSON logs.

## Verification

| Check | Result / scope |
| --- | --- |
| Backend pytest | 902 passed, 62 skipped; no staging/prod credentials loaded for the ordinary suite |
| Backend Ruff | Pass for app/tests/migrations and the staging Python launchers |
| Customer selected suites | 46 passed, 0 failed; includes availability failure, duplicate guard, refresh policy, detail-loop and receipt regressions |
| Owner selected suites | 26 passed, 0 failed; includes availability retry, cross-cache invalidation, focus, polling and duplicate walk-in safeguards |
| Customer TypeScript | Pass |
| Owner TypeScript | 16 diagnostics, all in existing `booking.schema.test.ts` marketplace fields; full check is not green |
| Frontend targeted lint | Changed policy/hook/recovery files pass; `SelectDateTimeScreen.tsx` retains the same 16 errors / 4 warnings as HEAD (baseline compared), not a clean full-repository lint claim |
| Real Mumbai API/JWT/Redis | Synthetic Auth, client-table denial, salon/service refresh, booking visibility, customer isolation, duplicate replay, stale-slot rejection, local-day boundary, owner pause/availability, late Redis fill and preserved replay key pass |
| Real Playwright | 11 passed, 0 failed in the final real-app run; zero Supabase Realtime sockets and zero page-error events |
| Independent-connection concurrent booking | Blocked: rollback-only fixtures serialize a shared connection; committed booking audits are immutable and cannot be erased for cleanup without changing protections |
| Native device/emulator | Not run: ADB reports no attached device/emulator |

Business tests use real Mumbai SQL/functions, real Supabase JWT/JWKS and a real local TCP API/Redis. Only synthetic Auth users are created persistently; salon/service/staff/booking/notification changes use an outer rollback transaction with API commits implemented as savepoint releases. This proves HTTP/UI refresh and business behavior under that fixture, **not** independent committed-connection concurrency or durable worker delivery. No actor extraction or business response is mocked in that run.

The browser run blocks non-local/non-Mumbai network destinations and Supabase Realtime is not needed. Expo CI served an older bundle during early attempts; both caches were cleared and the exact served customer bundle checked before the expanded run. Early fixture selectors incorrectly assumed Today, checkbox aria-checked and uppercase time labels; corrected selectors follow the actual UI. The initial network-recovery assertion could match a salon name in booking history; the final run requires the real salon-card action and exercises the visible Retry control. The owner walk-in fixture uses a five-minute synthetic service to retain real late-night slots; it is rolled back. The first customer status-query change introduced a loop, which is fixed with a regression test. Earlier failed attempts were cleaned; only final results determine acceptance.

## Measured latency

Thirty warm in-process health requests per endpoint; milliseconds, nearest-rank percentiles. These include real remote database/local Redis calls, not browser navigation or a production load test.

| Endpoint | p50 | p95 | p99 |
| --- | --- | --- | --- |
| /health | 0.433 | 0.626 | 2.369 |
| /health/db | 145.879 | 153.194 | 153.916 |
| /health/redis | 1.562 | 2.226 | 3.279 |
| /health/ready | 145.614 | 161.396 | 650.562 |

Business API sample counts are only 1-6 per route; their distributions are in the ignored staging-checks.json and must not be treated as production SLO evidence. Final single-sample browser delays from mutation response to visible UI change: salon listing 20,781 ms; new customer booking in the mounted owner list 2,886 ms; owner pause reflected in customer availability 7,464 ms. These are observed flow delays, not percentile estimates.

## Files and evidence

Backend implementation: `app/core/config.py`, `app/infrastructure/db/session.py`, `app/infrastructure/cache/redis.py`, `app/infrastructure/db/repositories/platform_repository.py`, `app/api/v1/routes/bookings.py`, `scripts/mumbai_local.py`, `scripts/mumbai_refresh_checks.py`, `scripts/mumbai_browser.cjs`, `tests/unit/test_refresh_commit.py`, `tests/unit/test_mumbai_local_guards.py`.

Customer checkout (`D:/salon/Salon-Customer-APP/customer-app`): `src/server-state/{queryClient,refreshPolicy,salons,bookings}.ts`, `src/hooks/useSalonOpenStatus.ts`, `src/services/supabase/realtime.service.ts`, `src/application/navigation/AppNavigator.tsx`, `src/screens/booking/{BookingConfirmScreen,SelectDateTimeScreen}.tsx`, `src/components/appointments/ModifyBookingStep.tsx`, `src/components/common/ServerStateNotice.tsx`, `src/utils/receipt.ts`, and associated refresh/bookings/salons/Realtime/modify/notice tests. Receipt's native media module is loaded only after its web guard, fixing the reproduced web startup failure while preserving mobile behavior.

Owner checkout (`D:/salon/salon-owner-APP`): `src/lib/{query-client,operational-polling}.ts`, `src/hooks/{useRealtimeSync,useWalkin}.ts`, `app/add-walkin.tsx`, and associated Realtime/walk-in/query-client tests. Unrelated owner `.claude` edits are preserved.

Ignored evidence directory: `backend/.artifacts/mumbai-refresh/`: configuration-probe.json, staging-checks.json, browser-results.json, customer-tests.json, owner-tests.json, backend-tests.txt, timing-check.json, request-timing.log, implementation-source-manifest.json, lint/typecheck diagnostics and synthetic screenshots. IDs are recorded privately there; session tokens are removed after each run. No secrets are included in this document.

The owner's migration-tool moves were reviewed: flat sibling imports remain together, ROOT resolves with `parents[4]`, and all six 0038-0040 source hashes still match sealed evidence. Historical runners still read normal `.env`; they were not used for the new local staging launch. Existing sealed evidence was not rewritten.

Re-run the guarded read-only configuration check from the repository root with `backend/.venv/Scripts/python.exe backend/scripts/mumbai_local.py --pooler --probe --samples 30`. `--pooler` is required on this workstation. The guarded fixture runner owns synthetic Auth/business cleanup. Plain `app.main` startup does not select the staging file automatically; use the launcher.

## Cleanup and remaining gate

Final run: zero synthetic salon fixture rows remain after rollback; all three synthetic Auth users were deleted and independently returned 404. Private session tokens were removed. Only the verified `salon-mumbai-refresh-redis` container was flushed; DBSIZE is zero. The pre-existing Redis was untouched. The fixture API and both Expo servers were stopped; the empty isolated Redis and ignored staging configuration remain available for local setup.

The final browser checks cover owner booking visibility, customer listing/service rendering, mounted salon polling, actual salon-card network recovery, a second customer's booking appearing in the mounted owner list, mounted customer availability after owner pause, customer availability failure/manual retry, owner availability mutation/failure/manual retry, and absence of Realtime connections. API checks additionally verify isolation, duplicate replay, stale-slot rejection, local-day boundaries and Redis late-fill rejection.

No migration or stamp is authorized. Full acceptance remains held for independent-connection concurrency: the real business fixture uses one serialized rollback connection, so it cannot establish competing committed transaction behavior. A cleanup-safe isolated database/test strategy is needed before that test can pass; immutable booking audit protections were not bypassed. Native flow coverage is blocked by no attached device/emulator. Multi-process Redis-outage recovery, complete booking-status lifecycle UI transitions and production-scale polling load have not been verified. Owner full TypeScript and the existing customer screen lint baseline remain non-green. A skipped, blocked or unverified check is not a pass.
