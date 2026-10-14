# Checkout safety, email and verification

Work dated 14 October 2026. Source changes are implemented locally. No production deployment,
production migration, live payment, bulk email, credential change or destructive live test was run.
The user's existing root README edit and real `backend/.env` were left unchanged.

## User story and boundaries

Customer selects an eligible salon/service/slot -> server quote -> Postgres `create_booking` ->
owner collects cash/direct UPI -> owner completes booking. Support requests/replies persist in
Postgres and queue Resend delivery. Supabase continues to own password reset tokens.

This repository remains backend-only. Mobile/website repositories remain separate.

## Implemented API contract

| Endpoint | Behavior |
| --- | --- |
| `GET /health/ready` | Checks Postgres and configured Redis connectivity |
| `POST /v1/bookings/quote` | Authenticated, server-priced services/overrides and Postgres slot validation; no provider call |
| `POST /v1/bookings` | Existing creation function, with transaction-backed idempotency and fraud/trial guards |
| `POST /v1/bookings/{id}/check-in` | Owning salon only; preserves slot occupation |
| `POST /v1/bookings/{id}/no-show` | Owning salon only; rejects before appointment start |
| `POST /v1/bookings/{id}/payment` | Existing collection endpoint, `payment_method: cash\|upi_direct` |
| `POST /v1/bookings/{id}/complete` | Rejects unpaid Pay at Salon with `409 payment_collection_required` |
| Existing owner access-state endpoint | Adds trial facts, subscription wall flag and the requested owner messages |
| `POST /v1/support/tickets` | Stores ticket/message and email outbox entries; requires Idempotency-Key |
| `GET /v1/support/tickets/{id}` | Customer, owning salon owner, or authorized admin |
| `POST /v1/support/tickets/{id}/reply` | Owning salon owner/admin, idempotent reply and customer email |
| `GET /v1/email/events/{id}` | Only the event's customer can read safe delivery status |
| `POST /v1/auth/forgot-password` | Rate-limited Supabase recovery request; generic acknowledgement |

Supply `Idempotency-Key` for booking creation, collection and completion. Existing clients that
omit it still receive transaction/state guards; retries with it replay the saved response.
Reusing a key for a different payload returns `idempotency_key_reuse`. Redis cannot authorize a
booking replay. Support and provider money operations require keys.

Quote example: service 250.00 -> PAY_ONLINE processing charge 12.50 and total 262.50;
PAY_AT_SALON -> processing charge 0.00 and total 250.00. Money remains Decimal/Postgres numeric.
The customer label is **Online payment processing charge**. Online checkout stays disabled
while `CASHFREE_ENABLED=false`; the quote can show its price without creating an order.

Public discovery, details/cache revalidation and availability enforce trial/subscription
eligibility. Customers receive availability flags or a generic unavailable/not-found response,
never the trial/subscription lock reason. Existing booking history and owner collection/completion
remain available after a subscription lock. Owner pause (`accepting_bookings`) remains separate.

Calendar rules: trial is two calendar months or 120 created bookings, whichever comes first;
later cancellation does not replenish the trial. The trial limit is sticky. Pay at Salon's
one-active-booking limit uses the appointment's **Asia/Kolkata calendar date**, globally per
customer across salons. Active means pending/confirmed/checked_in. Manual walk-ins without a
customer identity are outside that customer quota. Two no-shows start a seven-day Pay at Salon
block; after expiry a new pair starts a new block. Online remains independently eligible.

The existing `payment_status=unpaid|paid` cache remains for compatibility. Ledger responses add
the requested uppercase checkout `payment_status`, payment_mode, collection_method,
service_amount, online_processing_charge, total_payable, provider references and collected fields.
Booking responses add `checkout_payment_status` and pending amount/instructions. Existing
bookings retain their legacy fee policy; new bookings snapshot `customer_processing_v1` so a
future provider activation does not retroactively add fees to old appointments.

## Schema prepared for review

No baseline/history rewrite. New Alembic revisions:

| Revision | Change |
| --- | --- |
| 0034 | Adds checked_in/no_show enum labels in an explicit enum preparation transaction |
| 0035 | Trial gates, calendar-date quota, no-show restrictions, collection/completion guards, append-only booking/payment audit |
| 0036 | support_tickets, support_messages, email_events outbox and hashed rate-limit counters |
| 0037 | Immutable processing-charge/service snapshots, provider session reference and booking policy snapshot; service-only payment/refund cache |

New tables have RLS enabled and no anon/authenticated privileges. Direct Data API mutation of
bookings/booking_services and execution of create_booking are withdrawn; FastAPI is the authority.
Definer functions use fixed search paths and explicitly revoked public execution.
Audit actor anonymization is allowed only inside the existing confirmed-account-erasure scope.
Downgrade refuses to discard financial, support/email, or audit history; empty development
databases support the existing rollback/re-upgrade checks. Enum labels are retained on downgrade.

Indexes: active Pay at Salon customer/day, full trial salon/created_at (bounded count), subscription
eligibility, trial eligibility, booking audit history, support thread/customer history, and due
email events. Existing provider payment/webhook lookup indexes remain in use.

Migrations were exercised only on uniquely named disposable localhost PostgreSQL databases.
Review and apply explicitly in staging before running this version. Container startup does not migrate.

## Email and observability configuration

Blank secrets only:

```dotenv
CASHFREE_ENABLED=false
CASHFREE_ENV=sandbox
CASHFREE_APP_ID=
CASHFREE_SECRET_KEY=
PAYMENT_PROVIDER=none
CASHFREE_EASY_SPLIT_ENABLED=false
RESEND_API_KEY=
RESEND_FROM_EMAIL=
SUPPORT_EMAIL=
RESEND_DOMAIN_VERIFIED=false
PASSWORD_RESET_REDIRECT_URL=
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.1
```

Legacy Cashfree credential/env names are accepted; use one naming set to avoid ambiguity.
No new Easy Split or disbursement workflow was added. Existing split capability remains dormant
and opt-in. Sandbox activation still requires credentials, provider URL setup and the existing
explicit commission/settlement policy. Production activation requires a separate approval.

Supabase Custom SMTP: host `smtp.resend.com`, port `587`, username `resend`, password supplied
from the server-side Resend key. Configure the verified sender and fixed reset redirect URL in
the staging Supabase dashboard. Do not paste the key into app/frontend settings. Verify SPF,
DKIM and DMARC before setting RESEND_DOMAIN_VERIFIED. No SMTP/account settings were changed here.
References: [Supabase Custom SMTP](https://supabase.com/docs/guides/auth/auth-smtp),
[Resend SMTP](https://resend.com/docs/send-with-smtp),
[Resend email API](https://resend.com/docs/api-reference/emails/send-email).

Compose includes a dormant email-worker. Booking confirmation/cancellation and verified online
payment receipts enqueue atomically; support confirmation/admin/reply emails use the same outbox.
Provider idempotency keys remain stable across retries. Claims use SKIP LOCKED, bounded retry
attempts and stale-claim recovery. Ambiguous deliveries stop before Resend's 24-hour idempotency
window; expired/exhausted events require an operator instead of blind resending. Nothing sends
without a key, sender and explicit verified-domain flag. Do not enable it on an unreviewed queue.

Timing logs contain request_id, normalized route, method, status, duration, DB count/time,
observed Redis read timing/cache hit state, error code and environment. Server-Timing is returned
only for local/test/staging. Raw request bodies, validation input, SQL parameters, query strings,
credentials and user contacts are excluded. Optional Sentry removes request/user/breadcrumb
payloads, locals, exception values and SQL span descriptions, and retains safe request/route tags.

Staging alert setup remains external work requiring its Sentry project: alert on payment webhook
processing failures, booking `5xx`, `ALERT email_delivery`, and route p95 above the targets below.
No intentional error was sent to a real Sentry project. Crashlytics is a mobile integration;
neither mobile repository currently includes its Crashlytics SDK. Clarity was not added to
FastAPI or mobile apps; website consent, masking and privacy review remain prerequisites.

## Reproducible local verification

Windows virtualenv commands from `backend/`:

```powershell
$env:MIGRATION_TEST_DB='postgresql://postgres@127.0.0.1:55439/postgres'
.venv/Scripts/python.exe -m pytest -q --tb=short
.venv/Scripts/python.exe -m ruff check --no-cache app tests migrations
docker build -t salon-platform-api:checkout-test .
```

Disposable services were created explicitly, without loading backend/.env:

```powershell
docker run --detach --name salon-safety-postgres --publish 127.0.0.1:55439:5432 --env POSTGRES_HOST_AUTH_METHOD=trust postgres:18
docker run --detach --name salon-safety-redis --publish 127.0.0.1:56389:6379 redis:7-alpine
```

Test data contains only synthetic identities. The native/load fixture helper is under
`tests/manual/local_fixture_server.py`, never imported by production. Run it from repository root
with PYTHONPATH pointing at backend so no backend/.env is loaded. `--prepare` explicitly creates
a fresh uniquely named local test database, applies migrations and seeds synthetic catalog/users.
Its Supabase Auth **test double** issues ephemeral signed JWTs against local JWKS: the normal
FastAPI verifier, database profile roles and resource ownership still run. It is not evidence of
real Supabase signup, SMTP email delivery or password reset completion.

```powershell
$env:PYTHONPATH='D:/salon/salon-backend/backend'
backend/.venv/Scripts/python.exe -m tests.manual.local_fixture_server --prepare
backend/.venv/Scripts/python.exe -m tests.manual.local_fixture_server
```

From backend, set LOCAL_TEST_DATABASE_NAME to the prepared `salon_local_test_*` database name.
`docker-compose.test.yml` references only the dedicated localhost Docker resources; it does
not include an env_file or production secrets:

```powershell
docker compose --env-file .env.example -p salon-checkout-test -f docker-compose.test.yml up -d --wait --wait-timeout 60
.venv/Scripts/python.exe scripts/api_performance.py --requests 50 --concurrency 5 --allow-test-writes --output .artifacts/api-performance-small.json
.venv/Scripts/python.exe scripts/api_performance.py --requests 50 --concurrency 20 --output .artifacts/api-performance-medium.json
```

The load runner is restricted to localhost and never records tokens or response bodies.
Writes need an explicit flag and the disposable fixture. Staging targets are deliberately not
accepted by this local runner; use a separately reviewed staging load configuration.

## Evidence and outstanding verification

Detailed final results and measured percentiles are in `verification/checkout-results.md`.
Private local HTML/screenshots/traces and fixture manifests live under ignored `.artifacts/`.
Staging URLs were not provided, so no staging URLs were tested. Live email, real Supabase RLS
under its complete hosted configuration, Cashfree sandbox, Sentry delivery and Crashlytics
delivery are not claimed as verified.

Before production: review/apply migrations in staging, update separate clients for upi_direct,
new quote/availability/error contracts and owner wall, run real staging auth/reset/support flows,
verify the Resend domain and email queue, provision/sanitize alert delivery, run full native and
browser customer/owner flows, and measure staging load against representative data.
