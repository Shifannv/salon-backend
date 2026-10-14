# API latency investigation — 2026-10-14

Status: backend optimization and local benchmarks verified; full E2E completion remains open. No independent staging environment was supplied. http://127.0.0.1:8000 is local, even though it connects to remote Supabase.

## Finding and evidence

The historical Postman request has no trace ID, so its exact cold/warm state cannot be proved retrospectively. Its warm latency was reproduced independently of Postman: /health/db median 1794.523 ms after 10 excluded warmups. This rules out an exclusively Postman display/proxy problem or exclusively first-request cold start for the reproduced behavior.

The existing API already had a module-scoped async SQLAlchemy/asyncpg pool and no Uvicorn reload in Docker. Diagnostic profiling reused one physical connection across 15 sessions and ended with zero checkouts. Pool exhaustion and per-request engine creation did not explain sequential latency. The pooler is in ap-southeast-2; an individual held-connection SELECT 1 costs about 307 ms transport time, while EXPLAIN ANALYZE reports only 0.026 ms execution before and 0.017 ms after. No index or migration was added: SELECT 1 has no table access to optimize.

The default transactional asyncpg pre-ping plus probe transaction/cleanup incurred repeated network round trips. A shared AUTOCOMMIT base pool now performs probes/pings; the business engine is a READ COMMITTED option engine sharing that same pool. All business sessions, workers, actor context, booking creation and payments remain transactional. A real-Postgres regression verifies rollback, actor context, shared pool identity and business transaction isolation after probes. Warm measured checkout median fell from 1264.62 to 625.36 ms. Remote /health/db median fell to 909.255 ms (49.3% reduction); its 949.872 ms p95 still misses the 100 ms target. A roughly 307 ms network round trip alone prevents that target from this computer. Deployment near the DB needs separate verification; this report does not claim that unmeasured improvement.

Host resources also affected tails: one snapshot had about 209 MB physical memory free and under 1 GB commit available, with Node allocation failures and Gradle crashes. The original remote baseline retains a 27775 ms client outlier versus server p99 2202.2 ms. These are separate observations, not proof that memory alone caused that outlier. Host DNS warm probes were sub-millisecond to roughly 1 ms after the first 51 ms lookup; remote TCP was about 300 ms. Container DNS initially cost 249 ms and returned IPv4; no evidence established an IPv6 fallback delay. Container-loopback /health p95 was 1.112 ms sequential and 35.791 ms at concurrency 20, both without errors. Windows-to-Docker client timings are materially higher. No synchronous DB driver was found; the measured remote wait dominates this endpoint. This is not a claim that every route is free of blocking work.

## Method and limits

Each listed case has 10 excluded sequential warmups followed by 50 measured samples. Concurrent reads use 20 clients; booking creation and collection run sequentially only against disposable localhost synthetic data. Client measurements are HTTPX wall time, not a newly captured Postman session. Server-Timing app measures time to response headers; structured logs separately measure total ASGI duration including response completion and dependency cleanup. db is cursor time, db_acquire is measured session connection acquisition; these do not include all transaction cleanup. External and Redis spans are separate. Never subtract percentile values to infer a matched request's overhead.

Synthetic Auth signs ephemeral JWTs; the backend signature verifier, database profile roles and use-case ownership checks remain active. This does not verify hosted Google/Supabase delivery. Benchmark writes generated 60 synthetic bookings (10 warmup + 50 measured), 60 manual captured receipts and 120 booking/payment audit events. Quote uses a separate free date; a preliminary quote run against an already-booked fixture returned 409 and was discarded as an invalid fixture, not hidden as a performance success.

## Local synthetic API, sequential

| Endpoint | Before p50 / p95 / p99 ms | After p50 / p95 / p99 ms | After min / max ms | After errors | After req/s | After server app p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| health | 2.395 / 3.763 / 5.226 | 2.53 / 4.155 / 5.816 | 1.94 / 5.816 | 0% | 357.00 | 0.2 |
| health_db | 14.946 / 36.821 / 116.272 | 10.147 / 48.913 / 65.114 | 7.764 / 65.114 | 0% | 68.25 | 38.82 |
| authenticated_read | 21.594 / 26.034 / 30.0 | 19.02 / 21.68 / 27.738 | 16.733 / 27.738 | 0% | 51.75 | 12.48 |
| search | 24.051 / 27.01 / 38.704 | 20.039 / 24.1 / 30.277 | 16.39 / 30.277 | 0% | 48.84 | 13.83 |
| salon_detail | 25.08 / 31.567 / 33.358 | 20.749 / 22.955 / 34.573 | 18.875 / 34.573 | 0% | 47.10 | 13.96 |
| slots | 29.291 / 35.417 / 37.449 | 25.954 / 31.452 / 35.626 | 23.348 / 35.626 | 0% | 37.43 | 20.87 |
| quote | 48.917 / 60.748 / 80.562 | 44.033 / 55.573 / 196.254 | 39.953 / 196.254 | 0% | 20.11 | 45.98 |
| create_booking | 58.437 / 75.073 / 86.785 | 59.357 / 83.004 / 176.71 | 52.198 / 176.71 | 0% | 15.77 | 75.12 |
| collection | 63.825 / 82.7 / 101.812 | 64.396 / 73.607 / 79.392 | 59.028 / 79.392 | 0% | 15.32 | 65.59 |

## Local synthetic API, 20 concurrent safe reads

| Endpoint | Before p50 / p95 / p99 ms | After p50 / p95 / p99 ms | After min / max ms | After errors | After req/s | After server app p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| health | 38.166 / 85.928 / 93.138 | 42.757 / 84.335 / 136.879 | 12.753 / 136.879 | 0% | 344.92 | 0.5 |
| health_db | 74.791 / 149.971 / 165.024 | 56.224 / 187.121 / 250.804 | 25.947 / 250.804 | 0% | 169.79 | 65.57 |
| authenticated_read | 60.109 / 157.43 / 183.129 | 86.361 / 180.848 / 261.86 | 26.671 / 261.86 | 0% | 154.37 | 148.13 |
| search | 83.918 / 190.376 / 236.916 | 85.432 / 220.802 / 238.495 | 33.116 / 238.495 | 0% | 167.25 | 168.54 |
| salon_detail | 60.412 / 162.466 / 176.618 | 83.596 / 165.875 / 193.305 | 45.39 / 193.305 | 0% | 188.05 | 96.18 |
| slots | 65.749 / 133.177 / 143.643 | 107.882 / 226.896 / 311.944 | 38.188 / 311.944 | 0% | 144.16 | 156.59 |
| quote | 132.358 / 233.789 / 272.23 | 177.573 / 429.173 / 571.528 | 56.278 / 571.528 | 0% | 84.42 | 420.0 |

The first final concurrent quote run reached client p95 891.864 ms while a website build overlapped; its server app p95 was 98.37 ms. Both that run and the controlled idle repeat are retained in latency-measurements.json. The idle repeat still misses the client health 50 ms and DB-health 100 ms targets under concurrency 20. Several concurrent endpoints got slower than baseline. No blanket speedup or all-targets-met claim is justified. Sequential synthetic business endpoints meet the requested budgets; remote database health does not.

## Local Docker API connected to remote Supabase, sequential read-only health

| Endpoint | Before p50 / p95 / p99 ms | After p50 / p95 / p99 ms | After min / max ms | After errors | After req/s | After server app p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| health | 1.98 / 3.067 / 3.744 | 3.346 / 4.39 / 6.378 | 1.723 / 6.378 | 0% | 301.55 | 0.54 |
| health_db | 1794.523 / 2211.156 / 27775.325 | 909.255 / 949.872 / 1057.764 | 877.09 / 1057.764 | 0% | 1.10 | 941.34 |

After remote DB-health server app p50/p95/p99: 907.43 / 941.34 / 1056 ms. DB cursor p95: 314.09 ms; connection acquisition p95: 629.59 ms. The benchmark artifact contains matched per-request network/server observations in ignored local artifacts. Postman screenshot TTFB is not comparable to its Process field as backend execution time; Process is client processing.

## Pool and observability

Defaults per process: pool_size=5, max_overflow=5, pool_timeout=10 s, pool_pre_ping=true, pool_recycle=1800 s, asyncpg connect timeout=10 s, statement_cache_size=0. Size/overflow/timeout bounds are validated. Size workers against the total DB budget: observed max_connections=60 and approximately 17 existing sessions at baseline; worker pools also consume connections. Do not blindly increase pool size. No pool exhaustion appeared in the sequential profile; concurrency queueing is included in measured acquisition time.

Request logs contain request_id, templated route, HTTP status, total duration, header time, DB/acquire/query counts, Redis/external provider timing, connection creation/peak checkouts and response byte count. No tokens, request bodies, raw SQL or provider payloads are added. Server-Timing is restricted to local/test/staging. External adapters retain timeout behavior; HTTP connection reuse across provider requests was not implemented or benchmarked, and remains a follow-up. No provider was called by the booking/payment load benchmark.

## Changed files and reasons

- app/infrastructure/db/session.py: shared pool with transactional business and lightweight real probe bindings; measure acquisition.
- app/api/v1/routes/health.py and tests/test_health.py: SELECT 1 probe dependency and test wiring, no cached or hardcoded DB success.
- app/core/config.py, .env.example, .env.gcp.example: bounded pool settings and recycle/connect timeout templates. Real environment files unchanged.
- app/core/telemetry.py and app/core/security.py: request/DB/provider/response size metrics and JWKS timing.
- infrastructure/email/resend.py, payments/cashfree.py, payments/razorpay.py, supabase/auth_gateway.py: provider timing. Auth gateway additionally corrects phone OTP verification to /auth/v1/verify per the official Supabase client contract (https://github.com/supabase/auth-py/blob/main/supabase_auth/_async/gotrue_client.py).
- tests/unit/test_phone_otp_contract.py: HTTP boundary regression for valid and rejected OTPs.
- tests/integration/test_checkout_safety_sql.py: real database transaction/pool regression.
- tests/manual/local_fixture_server.py: verified synthetic phone identities and isolated Redis reset for newly prepared fixtures; no real SMS/email.
- scripts/latency_benchmark.py, scripts/profile_database.py: repeatable guarded benchmarks and read-only transport/pool/query profiler.
- docs/RUNBOOK.md and this verification report/JSON: operational interpretation and measured evidence.
- Separate website repo: exact deletion-heading selector, fully local server/client Auth/Redis test settings, and separate live-local browser test/config. Frontend code remains outside this backend image.
- Separate customer/owner repos: explicit localhost-only E2E entrypoints that restore synthetic sessions without changing normal production auth. Customer Reanimated patch candidate remains subject to device validation; do not treat the candidate as a proven fix.

## Backend skipped-test audit

Final normal full suite: **926 passed, 14 skipped**, 65.60 s. Two warnings: upstream Starlette/AnyIO deprecation and Windows pytest-cache permissions. A preceding rerun had 16 Windows temp-directory setup errors; a fresh workspace `--basetemp` resolved them. Ruff passed. The skips require explicitly configured disposable database fixtures. Running those 14 with opt-in local PostgreSQL enabled produced 9 passed and 5 failed. None was changed to pass or weakened. Paths below are relative to tests/integration/; the first ten are in test_account_deletion_sql.py.

| Test | Opt-in result | Risk and next action |
|---|---|---|
| account deletion: test_every_text_column_is_classified | FAIL | 43 newer text/JSON columns lack erasure classification. Review retention/PII classification and scrubbing; do not blindly mark nonpersonal. |
| account deletion: test_every_cascade_fk_to_salons_is_emptied_by_the_owner_scrub | PASS | Preserve disposable-DB coverage in CI. |
| account deletion: test_owner_erasure_leaves_no_residual_personal_data_anywhere | PASS | Existing seeded columns covered; expand for newer columns above. |
| account deletion: test_customer_erasure_leaves_no_residual_personal_data_anywhere | PASS | Same newer-column coverage limitation. |
| account deletion: test_worker_cancels_notifies_refunds_once_and_erases | PASS | Local provider doubles only; keep opt-in CI job. |
| account deletion: test_unsettled_refund_requeues_then_proceeds_after_the_cap | PASS | Preserve queue/retry regression in isolated DB job. |
| account deletion: test_unissuable_refund_is_recorded_failed_and_erasure_proceeds | PASS | Preserve failed-refund accounting regression. |
| account deletion: test_no_provider_makes_the_refund_phase_a_clean_noop | PASS | No-provider path only; no live refund verified. |
| account deletion: test_repeated_confirmation_is_idempotent_and_wrong_hash_is_rejected | FAIL | Fixture cancellation includes completed bookings; terminal-state DB guard correctly rejects it. Cancel only eligible fixture bookings and rerun handshake checks. |
| account deletion: test_an_owner_with_open_bookings_is_not_blocked | PASS | Preserve async erasure behavior in isolated job. |
| test_media_reference_locking.py::test_publication_lock_and_reference_scan_protect_shared_object | PASS | Keep explicit MEDIA_TEST_DB isolated in CI. |
| test_salon_approval_migration.py::test_upgrade_business_gates_owner_protection_and_downgrade | FAIL | Fixture string replacement rewrites SQL PUBLIC role into a nonexistent schema-named role. Preserve role tokens and isolate namespace rewriting/migration scope. |
| test_service_presentation_migration.py::test_migration_and_service_api_round_trip | FAIL | Created service missing from an expected listing; exact cause unresolved. Identify failing surface and align isolated schema dependencies before claiming contract regression/fix. |
| test_website_migration.py::test_discovery_migration_review_and_qr_round_trip | FAIL | Shared auth schema collides with scratch fixture setup. Isolate fixture Auth objects safely and rerun. |

To unskip the passing nine routinely, supply their explicit local-only opt-in variables in a separate disposable PostgreSQL CI job. The five failures are outstanding, not silently excluded successes.

## E2E and safety status

Website regression: 30 passed, two optional visual-capture skips, Chrome desktop and emulated mobile. These use a mock API. A separate real-local Playwright test passed in 14.2 s after exposing and fixing the incorrect OTP provider route. The actual website UI selected a service/staff/time, verified the synthetic phone OTP through the real backend gateway, and created a booking with HTTP 201. A separate PostgreSQL read verified the same booking ID/customer, source=qr_walkin, status=confirmed, payment_status=unpaid, total_price=250.00, and one audit event. This increased the synthetic customer's booking count from 60 to 61. No browser payment was collected.

Docker: final salon-platform-api:latest image and healthy backend-api-1 both use sha256:2e58285a02fa7f317da0e7611fd68826f72c82d357c73e9d6171ad113964eb7f. The local API was rebuilt/recreated only; no migrations or workers were started or changed by this update.

Owner device: normal JWT verification and authenticated profile/salon/staff/bookings endpoints returned 200, and the real Staff Members workspace rendered the synthetic staff record. This verifies local test-session authentication, not Google's provider flow or device payment collection.

Customer: the real date/time screen rendered slots in one device run, but blank/skeleton mounting failures recurred with RetryableMountingLayerException (missing SurfaceMountingManager). A Reanimated patch candidate is under validation; no stable fix or completed customer device booking is claimed. Native component suite: 4 passed, 2 failed because tests expect the old global payment config route while the screen calls the salon-specific payment-options route. These failures were not proved to be caused by the patch. Jest reported open handles. No Maestro/Detox suite exists in these repos; ADB device runs are not a substitute for a nonexistent automated native suite.

No feature, authorization, RLS validation, audit event, booking function, availability function, Decimal validation or business transaction safety was removed. Business load used synthetic disposable data only. No production data mutation, production migration, real payment/collection/refund, or intentional real email was used. Remote DB diagnostics were read-only. Earlier browser runs did not explicitly isolate server-side provider settings, so zero external provider traffic or email delivery cannot be attested retrospectively; final browser configuration uses local Auth/no-op recovery and blank external Redis settings. Real hosted-provider behavior remains unverified.
