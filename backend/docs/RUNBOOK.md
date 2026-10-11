# Runbook

Run commands from `backend/`.

## Local setup

```bash
python -m venv .venv
# Activate .venv for your shell.
python -m pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Required production settings are `DATABASE_URL`, `SUPABASE_URL`,
`SUPABASE_ANON_KEY`, `SUPABASE_JWKS_URL`, `SUPABASE_JWT_AUDIENCE`,
`SUPABASE_SERVICE_ROLE_KEY`, and `BACKEND_CORS_ORIGINS`. R2 and Firebase settings are
required only when those integrations are enabled.

`CUSTOMER_CANCELLATION_CUTOFF_MINUTES` defaults to `120`.
`ALLOW_LATE_CANCELLATION_REQUESTS` controls whether customers may request a salon
exception after that cutoff.

## Verification

```bash
python -m pytest
python -m ruff check app tests migrations
alembic current
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/db
curl http://127.0.0.1:8000/health/redis
```

## Operational rules

- Apply reviewed migrations explicitly before deploying code that requires them.
- Keep the Compose `notification-worker` running so missed or failed push attempts
  are retried. Notifications remain readable in the API even when push is delayed.
- Do not run migrations in the container startup command.
- Restrict production CORS origins.
- Keep service-role, database, R2, and Firebase credentials outside Git and logs.
- A booking conflict is expected under concurrency; clients should refresh slots.
- If database connections are exhausted, inspect pool settings and Supabase pooler
  limits before increasing application concurrency.

## Super-admin provisioning

Run this **from a trusted machine** (your local workstation or a secure bastion) — never from a shared CI runner where logs may be captured.

```bash
# From backend/
python -m scripts.provision_super_admin --email admin@example.com --yes
```

- `--email` is the super-admin's login address (required).
- `--yes` is a safety gate; the script refuses without it.
- The password is read from `SUPER_ADMIN_PASSWORD` (env var) or an interactive `getpass` prompt.
  It is **never** passed on the command line, never logged, and never written to disk.
- The script is idempotent: re-running it updates the password and re-asserts
  `role='super_admin'` and `is_active=true` on the profiles row.
- The script refuses to convert an existing customer, owner, or staff profile. Use a
  dedicated admin email so provisioning cannot detach an owner from their salon.

### Where the credentials live

- **Password** — stored as a hash in Supabase Auth only.  Not in any `.env`, Vercel secret,
  or document.
- **Change the password** after the first successful login.
- **Enrol TOTP** at `/superadmin/login` on first sign-in to the website.
- Once TOTP is enrolled, set `ADMIN_REQUIRE_MFA=true` in the backend environment and
  redeploy.  After that, an `aal1`-only token returns `403 mfa_required`.

### Supabase pre-requisites

Before the first login from the website:

- TOTP MFA must be enabled in the Supabase Auth dashboard.
- The website origin must be in the Supabase redirect allowlist
  (`https://<website>/api/admin/auth/callback`).
- The Supabase Site URL should be set to the website origin.

### Verify after provisioning

```bash
# Confirm role and is_active via the API (replace <token> with a fresh JWT):
curl -H "Authorization: Bearer <token>" http://localhost:8000/v1/auth/me
# Expected: {"role": "super_admin", "is_active": true, ...}
```

## Account deletion worker

- Compose service `account-deletion-worker` drains `account_deletion_requests`. If it is not
  running, confirmed accounts are locked but not erased; start it and check logs.
- A request stuck in `failed` retries with backoff (30 s doubling to 1 h) and records only an
  error class in `last_error_code` (for example `ServiceUnavailableError` = Supabase down,
  `ErasureVerificationError` = a post-condition failed). Fix the cause; do not edit rows to
  force `completed`.
- Migrations `0020` then `0021` must be applied explicitly before enabling the feature.
- Full procedure and data matrix: `ACCOUNT_DELETION.md`.

## Payments

Env vars: see `.env.example` (`PAYMENT_*`, `RAZORPAY_*`). Default `PAYMENT_PROVIDER=none`
is dormant. The `payment-webhook-worker` Compose service runs always and idles while
dormant. Apply `alembic upgrade head` (0026, 0027) explicitly **before** deploying code.

Operator queries:

```sql
-- events that failed and need a human (amount mismatch / overcollection are never retried)
select id, event_type, last_error_code, attempts, received_at
from payment_webhook_events where processing_status = 'failed' order by received_at desc;
-- intents stuck open
select id, booking_id, status, order_ref, updated_at from booking_payments
where channel = 'gateway' and status in ('created','authorized') and updated_at < now() - interval '1 hour';
-- refunds still pending
select * from payment_refunds where status = 'created' and updated_at < now() - interval '1 hour';
```

**Over-collection (`payment_overcollection`).** The system refuses to silently collect
twice. If cash was recorded and an online capture then arrived (or vice versa), the capture
event is `failed` with `last_error_code = 'overcollection'` and the ledger row stays
unsettled. A person must refund the customer (provider dashboard) or the duplicate, then
mark the event handled. Do not edit `bookings.payment_status` by hand: a trigger rejects it.

**Amount mismatch.** The row is failed (`failure_code = amount_mismatch`), the booking is
not marked paid, and an ERROR is logged. Investigate with the provider.

**Lost webhook.** The worker reconciles open intents older than
`PAYMENT_RECONCILE_AFTER_SECONDS` via the provider API automatically.

**Rotating the webhook secret** requires changing it in the provider dashboard and `.env`
together; deliveries in between fail signature (400) and are retried by the provider.

Unverified: all of the above SQL and triggers were not run against a live Postgres.
