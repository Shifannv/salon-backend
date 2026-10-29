# Runbook

Run commands from `backend/`.

Current production API: `https://api.salones.in`; Swagger: `/docs`; routes: `/v1`.
It uses the existing Google HTTPS load balancer and Mumbai Cloud Run service
`salon-api-production`. Keep the legacy hostname/certificate for older mobile
builds. See [hostname migration and rollback](verification/API_DOMAIN_MIGRATION_2026-10-27.md).

## Local setup

```bash
python -m venv .venv
# Activate .venv for your shell.
python -m pip install -r requirements-dev.txt
cp .env.example .env
alembic -x migration_policy=portable-ci upgrade 0037_customer_processing_charge
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

Latency diagnostics and measured limits are documented in
[`verification/latency-investigation.md`](verification/latency-investigation.md).
The application shares one PostgreSQL pool per process. Business sessions bind
the READ COMMITTED engine; only real `SELECT 1` reachability probes bind its
AUTOCOMMIT base engine. Keep business sessions transactional. Default pool limits
are 5 persistent plus 5 overflow connections, a 10-second checkout timeout,
1800-second recycle and 10-second asyncpg connection timeout, with pre-ping enabled.
Budget all API and worker processes against the database connection limit.
`Server-Timing` in local/test/staging measures time to response headers; structured
request logs also report total duration and response bytes. Remote DB round trips
can exceed the entire readiness latency budget even when `SELECT 1` executes quickly.

```bash
python -m pytest
python -m ruff check app tests migrations
alembic current
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/db
curl http://127.0.0.1:8000/health/redis
```

## Operational rules

- Normal production releases use the protected [Cloud Run candidate workflow](CI_CD.md).
  Require reviewed latest main, proven image source and separate traffic approval.
  Legacy VM scripts are recovery material; do not dispatch the VM workflow.

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
- Migrations `0020`, `0021` and `0028` (through `alembic upgrade head`) must be applied
  explicitly before enabling the feature.
- The worker has a heartbeat **healthcheck**: `docker compose ps` must show
  `account-deletion-worker` as `healthy`. `unhealthy` means it is dead, wedged, cannot reach
  the database, or is paused because Redis is configured but unreachable - in every case
  confirmed accounts stay locked with their data intact until it recovers. It also refuses to
  start (exit 1, CRITICAL log naming the setting) when Supabase admin credentials or R2
  storage settings are missing or incomplete; fix the `.env` and restart.
- Owner deletions first cancel the salon's future bookings, notify the customers and refund
  online payments, and only then erase. `last_error_code = 'refunds_pending'` with status
  `pending` is normal while refunds settle (it is not a failure).
- Full procedure and data matrix: `ACCOUNT_DELETION.md`.

Stale or stuck requests (anything not completed an hour after it was requested):

```sql
select id, role, status, attempts, last_error_code, requested_at, next_attempt_at, updated_at,
       (select array_agg(k order by k) from jsonb_object_keys(step_state) k) as steps_done
from account_deletion_requests
where status <> 'completed' and requested_at < now() - interval '1 hour'
order by requested_at;
```

The same data is on `GET /v1/admin/account-deletions` (`attempts`, `last_error_code`,
`next_attempt_at`, `updated_at`). `steps_done` shows how far it got
(`bookings_cancelled`, `refunds_issued`, `refunds_settled`, `auth_banned`, `db_erased`, ...).
Fix the cause named by `last_error_code`; never edit rows to force `completed`.

**Failed closure refunds.** When an owner deletes their account, online payments on the
cancelled bookings are refunded automatically. If that cannot be done after
`ACCOUNT_DELETION_REFUND_MAX_ATTEMPTS` claims, erasure proceeds anyway and the worker logs
an ERROR (`Closure refund ... could not be issued` / `... still unsettled`). Find them:

```sql
select r.id, r.status, r.failure_code, r.amount, r.provider, r.refund_ref, r.created_at,
       p.payment_ref, p.booking_id
from payment_refunds r join booking_payments p on p.id = r.payment_id
where r.idempotency_key = 'salon_closed' and r.status in ('failed', 'created')
order by r.created_at;
```

- `failed` + `refund_call_failed` / `provider_unavailable`: the provider was unreachable or
  not configured. Refund the customer from the provider dashboard against `payment_ref`
  (amount shown), then note it; do not insert a second `payment_refunds` row for that payment.
- `failed` + a provider code: the provider declined; investigate with the provider.
- `created` older than a few hours: the provider accepted it but the settlement webhook never
  arrived. Check `refund_ref` in the provider dashboard; if processed, the refund webhook
  (or a replay) will close the row. The customer's money is not at risk, only the ledger.
- An online payment captured *after* the closure (a checkout in flight) is not auto-refunded:
  look for `booking_payments` with `status = 'captured'` on bookings with
  `cancellation_reason = 'salon_closed'` and no `payment_refunds` row, and refund by hand.

## Payments

Env vars: see `.env.example` (`PAYMENT_*`, `RAZORPAY_*`, `CASHFREE_*`,
`SUBSCRIPTION_*`). Default `PAYMENT_PROVIDER=none` and `SUBSCRIPTION_PROVIDER=none` are dormant. The
`payment-webhook-worker` Compose service runs always and idles while dormant. Apply
`alembic upgrade head` (0026-0031) explicitly **before** deploying code. Webhook URLs to register
at the provider: `https://<api>/v1/webhooks/cashfree` (payments, refunds, vendor, settlement) and, for
subscriptions, `https://<api>/v1/webhooks/razorpay` (signed with `SUBSCRIPTION_RAZORPAY_WEBHOOK_SECRET`;
events `payment.captured`, `order.paid`, `payment.failed`, `refund.processed`, `refund.failed`).

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

**Over-collection.** Real money is never dropped. When an online capture exceeds what the booking
was owed (typically cash was recorded first), the capture IS recorded: the ledger row is `captured`
with `overcollected_amount` > 0, the booking is NOT counted paid twice, an ERROR
(`OVERCOLLECTION ...`) is logged and a `payment_anomalies` row (`kind = 'overcollection'`) appears.
Refund the excess with `POST /v1/bookings/{id}/payments/{payment_id}/refund` (omit `amount`; the
excess is refunded first and does not reduce the booking's paid state). Cash recorded AFTER an
online capture is refused by the database (`payment_overcollection`, 409 to the salon).
Do not edit `bookings.payment_status` by hand: a trigger rejects it.

```sql
-- everything an operator must look at
select kind, provider, salon_id, booking_id, payment_id, amount, detail, created_at
from payment_anomalies where resolved_at is null order by created_at;
-- close one after handling it
update payment_anomalies set resolved_at = now() where id = '<id>';
-- payee registration trail (references and statuses only, never KYC data)
select * from payment_provider_account_audit where salon_id = '<salon>' order by created_at desc;
```

**Settlement failure / reversal** (`settlement_failed`, `settlement_reversed` anomalies): the
vendor's payout failed at the provider; no ledger money moves. Fix the vendor's bank details
(owner re-registers) or resolve in the provider dashboard.

**Refund `created` for long.** The worker asks the provider for it by OUR refund id every
`PAYMENT_RECONCILE_AFTER_SECONDS`. A `refund_onhold` anomaly means the provider holds it for
insufficient balance: top up the provider balance.

**Unknown outcome after a timeout.** Intent/refund/vendor rows are committed BEFORE the provider
is called. An open intent whose `provider_order_confirmed_at` is null is resumed by the customer's
retry (same booking, purpose, amount) or reconciled by the worker through its order id.

**Amount mismatch.** The row is failed (`failure_code = amount_mismatch`), the booking is
not marked paid, and an ERROR is logged. Investigate with the provider.

**Lost webhook.** The worker reconciles open intents older than
`PAYMENT_RECONCILE_AFTER_SECONDS` via the provider API automatically.

**Rotating the webhook secret** requires changing it in the provider dashboard and `.env`
together; deliveries in between fail signature (400) and are retried by the provider.

Unverified: all of the above SQL and triggers were not run against a live Postgres.

### Owner subscription billing (stage 2, dormant)

Enable only after a Razorpay **test-mode** run (see `SUBSCRIPTIONS.md`, UNVERIFIED list). Env:
`SUBSCRIPTION_PROVIDER=razorpay`, `SUBSCRIPTION_RAZORPAY_KEY_ID`, `SUBSCRIPTION_RAZORPAY_KEY_SECRET`,
`SUBSCRIPTION_RAZORPAY_WEBHOOK_SECRET` (>= 32 chars), `SUBSCRIPTION_GRACE_DAYS` (explicit; `0` allowed),
`SUBSCRIPTION_ALLOW_LIVE=true` only for `rzp_live_` keys. Migrations 0030 (billing) and 0031 (plan seed) first.
The same `payment-webhook-worker` runs the subscription pass; alert on log lines starting
`ALERT subscription_billing`. Recovery queries and the duplicate/mismatch/blocked procedures are in
`SUBSCRIPTIONS.md` ("Operator recovery"). Turning billing off (`none`) leaves history, cancel and entitlement
reads working and never touches booking collection.

## Encrypted database backup preparation and recovery

Source code is not a database backup. The existing schema-only exports contain no
customer/booking rows. Database archives also do not include R2 object bytes,
provider settings, Google Cloud IAM/DNS or runtime secrets; inventory and protect
those separately before claiming complete disaster recovery.

`scripts/backup_database.py` streams `pg_dump --format=custom` directly into GPG
encryption. It never writes a plaintext dump or reads an application environment
file. Existing PostgreSQL18 tools and Git's GnuPG2.4.9 were verified on this Windows
machine; Git GPG's MSYS path conversion is handled by the script.

Preparation:

1. Create a password-protected recovery encryption key in a keyring outside the
   checkout, using an interactive GPG terminal. Keep its private key and passphrase
   under the operator's control, with a recoverable off-device copy. The unattended
   backup machine only needs the matching public encryption key. Never send private
   keys/passphrases through chat or put them beside an archive.
2. Configure libpq process settings securely: `PGHOST`, `PGPORT`, `PGDATABASE`,
   `PGUSER`, `PGPASSWORD` or `PGPASSFILE`, `PGSSLMODE=verify-full`, and a trusted
   `PGSSLROOTCERT`. Use a direct/session-pooler endpoint; transaction port6543 is
   refused. The script pins the source to the separately supplied expected hostname.
3. Run from `backend/` (placeholders below are intentionally nonfunctional):

   ```text
   .venv/Scripts/python.exe scripts/backup_database.py --check-tools
   .venv/Scripts/python.exe scripts/backup_database.py --execute --expected-host EXPECTED_DB_HOST --output-dir .backups --gpg-home KEYRING_OUTSIDE_CHECKOUT --recipient FULL_PUBLIC_KEY_FINGERPRINT
   ```

`backend/.backups/` is ignored by Git. Other destinations inside the checkout must
also be ignored; the script refuses to store private keys in this repository.
Successful exports have an encrypted `.dump.gpg` archive plus a SHA256/size/scope
manifest. Failed `.partial` files are not backups. A successful export remains
explicitly **restore unverified** until tested. Do not configure a schedule before
the first real export and restoration have passed.

Recovery rehearsal must decrypt through a pipe to `pg_restore` on a fresh,
isolated target, never the current production database. Confirm checksum/decryption,
schema/functions/roles/permissions, row counts and representative booking/financial
invariants. Supabase managed schemas, Auth identities/providers, OAuth callbacks,
JWKS, storage and role ownership need their own restore/migration review. Do not
blindly replay a full Supabase archive over another managed project. Restore media
bytes separately and test their URLs. For an API-only server move, retain the same
Supabase/Auth, R2, Redis and public API hostname whenever possible; do not restore
the database merely because the compute host changes.

Keep a second encrypted archive off this laptop and rehearse using the separately
stored recovery key. Choose backup frequency and retention from an agreed recovery
point objective, and include erasure/retention rules when restoring old data. A
synthetic local toolchain rehearsal is not proof of a production backup or a tested
full-account restoration. Current acceptance evidence is in deployment assessment33.

### Local recovery configuration verified on 25 October 2026

The operator authorized local encrypted archives under `backend/.backups/` and
references in the ignored `backend/.env`. Its `BACKUP_OUTPUT_DIR`,
`BACKUP_GPG_HOME`, `BACKUP_RECIPIENT_FINGERPRINT`, `BACKUP_EXPECTED_HOST`,
`BACKUP_SSL_ROOT_CERT` and `BACKUP_PASSPHRASE_DPAPI_FILE` entries are local backup
configuration, not application runtime settings or an automatic backup schedule.
The export helper still accepts explicit arguments and libpq process variables;
it does not automatically load these entries from `.env`.

The separate keyring is under
`%LOCALAPPDATA%/SalonRecovery/database-keyring/`. The GPG private key and its
armored export are password protected. The saved password is encrypted with
Windows current-user DPAPI in `passphrase.dpapi`; folder access is restricted to
the current Windows user and SYSTEM. The public recipient and Supabase root CA
are stored there too. No private key or password was added to `.env`.

**This is currently laptop/account-bound recovery.** Copying a DPAPI file to a
different machine does not establish password recovery there. Before relying on
this for laptop loss, the operator must establish an independent, secure recovery
password/private-key copy and keep a second encrypted archive off device. Do not
send either through chat. No off-device copy or scheduled backup exists yet.

The first real Mumbai database archive passed SHA256, decryption after closing
the GPG agent cache, and an isolated restore using the installed Supabase
PostgreSQL17 image. The target had no network or exposed port and was removed
after verification. Restore omitted original owners and ACLs; managed role,
permission and full hosted-project recovery still require review. Five key table
counts matched production. Assessment35 records the evidence and remaining scope.
Failed `.partial` files are not usable archives. R2 media bytes and runtime/cloud
configuration are not included in this database export.

## Prepared Cloud Run maintenance passes

`python -m app.infrastructure.maintenance_job TASK --limit 20 --timeout-seconds 240`
is a **local, tested entrypoint**, not an enabled production schedule. Tasks are
`email`, `account-deletion` and `media-cleanup`. It reuses existing workers and
does not add a public maintenance endpoint. There is no payment/subscription queue
task. Owner erasure can nevertheless require refunds through its existing closure
workflow; review those prerequisites before running it.

Queue results count **attempts**, including deferred/failed items. Inspect their
durable queue statuses to establish delivery or erasure completion. Media passes
propagate candidate failures. The time budget is cooperative: it stops between
items and finishes current work before closing its database session. Do not add
`wait_for` around threaded object deletion: cancellation can release publication
locks while a storage call continues. The blocking-thread unit regression covers
this boundary. Hard platform termination remains a separate operational risk.

Proposed jobs should use an immutable reviewed image, the existing production
runtime identity, a pinned runtime-secret version, one task/parallelism1,
max-retries0, and a platform timeout with room beyond the cooperative budget.
Prepare and manually validate each task before enabling a schedule. A Cloud Run
job runs and exits; creating one does not itself schedule it. Keep the working
notification worker unchanged until push continuity is separately accepted.

Deployment gates still open:

- Account erasure: full target-schema privacy tests and provider/storage/cache
  prerequisites. A zero-length current deletion queue does not prove processing.
- Email: configured verified sender, permission for the intended sends, and queue
  review. The production sample has13 pending events,10 outside the worker's23-hour
  delivery window; none were sent or modified by this investigation.
- Media: deletion/publication acceptance before scheduling sweeps. The bounded job
  now requires reachable Redis and saves/verifies one enumeration checkpoint per
  pass, advancing past referenced/unmarked objects and resetting after a complete
  traversal. Tests cover reaching a later orphan and preserving in-flight locks.
  Keep one execution at a time; overlapping jobs can duplicate enumeration work.
  Existing full continuous sweeps retain their original behavior.

No Cloud Run job, Scheduler schedule or new continuously allocated worker was
created during this preparation. The new image was built locally only.

The later original-owner/ACL restore matched captured production effective
permissions with zero differences. An actual encrypted R2 media export also now
exists beside the database archive:24 objects/8564415 source bytes, all object
hashes verified after decryption in memory. Object HTTP/custom metadata is inside
its encrypted manifest. No object was uploaded or deleted. The archive does not
include bucket configuration or prove restoration to a different storage provider.
The user selected local storage only; independent off-device recovery is still
unconfigured. Assessment36 records the exact archive identities and acceptance.
