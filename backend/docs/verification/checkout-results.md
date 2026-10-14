# Local verification evidence ? 14 October 2026

Status: backend implemented and verified locally; browser and native end-to-end checks have
failures/blockers. This is not staging or production acceptance.

No production payment, production migration, live email, credential change, or destructive live
test was run. Runtime backend/.env and the pre-existing root README edit were preserved.

## Environment and commands

Windows host; Docker Python 3.12 API, disposable PostgreSQL 18 on 55439, Redis 7 on 56389;
API on 8055. Local Auth test double on 8050 signs ephemeral RSA JWTs; normal backend signature,
profile, role and ownership verification run. It does not verify hosted Supabase Auth, SMS,
SMTP or Realtime. The phone accesses only localhost through adb reverse.

Run from backend unless indicated otherwise:

```powershell
$env:MIGRATION_TEST_DB='postgresql://postgres@127.0.0.1:55439/postgres'
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check --no-cache app tests migrations
docker build -t salon-platform-api:checkout-test .
docker run --rm -v D:/salon/salon-backend/backend/scripts:/checks:ro salon-platform-api:checkout-test bash -n /checks/gcp-vm-install-docker.sh /checks/gcp-vm-deploy.sh
.venv/Scripts/python scripts/api_performance.py --requests 50 --concurrency 5 --output .artifacts/api-performance-final-small-cache.json
.venv/Scripts/python scripts/api_performance.py --requests 50 --concurrency 20 --output .artifacts/api-performance-final-medium-cache.json
```

The earlier write benchmark additionally used --allow-test-writes. It created synthetic bookings
on distinct fixture dates; collection was sequential. Do not repeatedly run that benchmark
against the same fixture dates. Disposable preparation and Compose commands are documented in
[PRODUCTION_VERIFICATION.md](../PRODUCTION_VERIFICATION.md).

## API and database checks

Final full suite: **923 passed, 14 skipped, 1 dependency deprecation warning**, in 132.76 seconds.
Ruff: all checks passed with --no-cache (the existing local cache directory denied writes).
Subsequent focused verification after payment-retry and dependency-wiring review: 77 passed.
Real Postgres coverage includes:
concurrent daily booking limit, trial cap/expiry, history access after expiry, concurrent collection
and completion, idempotency mismatch/replay, immutable payment/audit records, direct UPI collection,
unpaid completion rejection, no-show block, quote calculation, support authorization/replies,
backend-only table privileges and fee-aware payment capture/refund. Outbox tests exercise parallel
claims and stable-key retries with a fake email gateway, not live Resend.

Docker build and deployment shell syntax checks passed. Alembic upgrade/empty rollback/re-upgrade
was exercised only in disposable databases. Migrations 0034?0037 require review and staging rollout.

## Measured API performance

50 samples per read/quote case, one separate warmup, concurrency 5 (small) and 20 (medium).
All final measured responses succeeded: error rate 0%. These measurements use a tiny synthetic
catalog, a single local API worker, warm caches, and host-to-Docker networking. They do not
establish staging capacity or production latency. Full JSON includes throughput, database/app
p95 and query counts. Provider calls: zero; provider latency is unmeasured.

| Endpoint | Small p50 / p95 / p99 ms | Medium p50 / p95 / p99 ms | Mean DB queries |
| --- | --- | --- | --- |
| health | 7.27 / 14.68 / 15.88 | 34.73 / 96.84 / 122.81 | 0.0 |
| readiness | 27.06 / 42.57 / 48.65 | 54.73 / 100.28 / 141.19 | 1.0 |
| search | 27.27 / 74.75 / 76.75 | 86.46 / 155.54 / 188.49 | 1.0 |
| authenticated_read | 23.82 / 54.59 / 58.51 | 116.74 / 175.22 / 184.06 | 1.0 |
| salon_detail | 31.18 / 100.12 / 117.99 | 73.17 / 127.95 / 179.05 | 1.0 |
| slots | 36.19 / 50.63 / 57.46 | 84.17 / 141.72 / 161.6 | 3.0 |
| quote | 69.44 / 100.89 / 112.0 | 249.52 / 410.87 / 425.97 | 6.0 |

[Small report](checkout-small.json), [medium report](checkout-medium.json),
[initial pool-starvation run](checkout-before.json),
[earlier booking/collection write report](checkout-writes.json).
Earlier 20-sample booking creation p50/p95/p99: 198.54/399.07/446.00 ms; collection:
89.38/134.76/150.52 ms (concurrency 1). Medium concurrent writes were not measured.
Detail-cache hit rate was 100% in the final warm runs; routes without observed cache reads use
null rather than an invented hit rate. Redis durations appear in structured logs; standalone
Redis percentile, hosted Auth, Resend and Cashfree timing are not measured.

The initial medium run exposed a connection-pool starvation bug: auth held one session while
waiting for a second throttle session. Quote error rate was 60%, p95 about 20 seconds. The fix
persists throttling in the authenticated session and restores actor context. Quote now executes
6 queries instead of 9 by selecting only required salon/service data and querying slot existence
through get_available_slots. The final medium quote p95 is 410.87 ms, the slowest measured route.
Concurrent Android builds produced a separate noisy run with target misses; that run is retained
under ignored .artifacts/api-performance-final-medium.json. No claim of consistent staging SLO
compliance is made. Trial counts use a salon_id/created_at index and a bounded 120-row scan;
customer/day and append-only audit lookup indexes are included in migration 0035.

## Website browser checks

Separate repo: D:/salon/salon-QR-Walking-Web/walking-customer-web. Command:

```powershell
npx playwright test --project=desktop --reporter=list,html --output D:/salon/salon-backend/backend/.artifacts/playwright-results --trace=retain-on-failure
```

Result: 14 passed, 1 skipped, 1 failed. Existing Playwright webServer starts a mock backend and
Next.js, so these are website regression checks, not real database or staging E2E evidence.
Failure: account-deletion public page expected noindex/no-store (site.spec.ts:177).
HTML: backend/.artifacts/playwright-html/index.html; failed screenshot/trace:
backend/.artifacts/playwright-results. These ignored artifacts are local and not committed.

## Native Android checks

Connected physical Infinix phone. Customer package com.salonbooking.customer; owner package
com.salonplatform.owner. Both local test APKs built and installed successfully. No Maestro/Detox
runner was present; tests used adb navigation, screenshots and app-process logs.

Generated MainApplication.kt files in the separate projects were adjusted for this local test:
explicit useDevSupport=false loads the embedded localhost-only bundle. This is a local build
setting, not a production configuration change. APK assets were checked for localhost API/Auth
and a synthetic public key. Cached BridgelessReactNativeDevBundle.js files were removed from
these two test packages so old development bundles could not mask the test configuration.
Account/application data were not cleared.

Passed: customer cold startup/onboarding, synthetic phone OTP login, normal JWT/profile reads,
one Local test salon in discovery, salon details and the server-priced 250 INR haircut service.
The fixed OTP is implemented only in tests/manual/local_fixture_server.py; no SMS was sent.

Failed: continuing from service selection opened a blank date/time screen. The customer process
logged Reanimated RetryableMountingLayerException / missing SurfaceMountingManager warnings.
These are diagnostic observations; the exact frontend root cause is not established. Native
booking creation, quote presentation, cancellation and payment collection were not completed.
The phone subsequently switched to another app during the cold-restart follow-up. Device input
was stopped; further native verification needs an uninterrupted test session.

Owner startup passed and reached Google-only sign-in. Authenticated owner flows are blocked by
lack of a local Google test-login path; no real Google account or production session was used
for mutations. Owner cash/direct-UPI collection/completion and subscription-wall UI remain
unverified on-device. Their API/database behavior has separate passing tests above.

Local screenshots: backend/.artifacts/native-customer-screen.png (local discovery),
native-customer-booking.png (service selection), native-customer-slots.png (blank failure),
native-owner-local.png (Google login). No production customer screenshot is included in this report.

## Release blockers and known gaps

No staging URLs were supplied; staging URLs tested: none. Required server settings are listed
with blank credentials in ../PRODUCTION_VERIFICATION.md and the environment templates.

Separate clients still need the quote/5% charge wording, no-charge Pay at Salon instructions,
upi_direct collection adapter, typed error handling and owner wall contracts. Hosted Supabase
RLS/auth/reset mail delivery, verified Resend domain/Custom SMTP/outbox delivery, Cashfree sandbox,
Sentry intentional-error delivery/alerts, both mobile Crashlytics test crashes, and browser-only
Clarity consent/masking remain unverified. Cashfree is explicitly disabled by default. Existing
Easy Split capabilities remain dormant; no new split/disbursement workflow was added.

Resolve the native rendering and local owner-auth blockers, website assertion failure, and client
contract gaps before staging customer/owner flows. Review migrations and the outbox queue before
enabling delivery. Production smoke testing requires the user's explicit approval.
