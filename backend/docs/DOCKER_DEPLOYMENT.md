# Docker deployment

Deploy with GitHub Actions to the GCP VM, or manually with Docker Compose.
The workflow verifies branch pushes and pull requests; only `main` can deploy.
See [CI/CD setup](CI_CD.md) for the required GitHub secrets and VM configuration.

Use `backend/` as the Docker build context.
Use Docker Compose v2 with `up --wait` and `--wait-timeout` support.

## Local

```bash
cp .env.example .env
docker compose build
docker compose run --rm api alembic upgrade head
docker compose up -d --wait --wait-timeout 120
docker compose ps
curl http://127.0.0.1:8000/health
```

The image runs as a non-root user, listens on `0.0.0.0`, respects `PORT`, and checks
`/health`. It contains Alembic and the migration files, but does not apply migrations at
startup.

Compose also runs `notification-worker` from the same image. It retries persisted push
events every 15 seconds and exposes no port. Apply migration `0013_booking_action_requests`
before starting code that uses the worker.

The worker disables the image's API-only HTTP health check. Compose waits for API and
Redis health and for the worker process to start; this does not verify successful push
delivery. Check worker logs and notification delivery records when diagnosing push.
Redis is accessible only inside the Compose network at `redis:6379`, not on a VM port.
The API and all workers wait for Redis health before starting and share runtime settings.

Compose also runs `media-cleanup` from the API image. Explicitly review/apply migration
`0020_media_reference_guards` first; cleanup refuses to delete without its seven guards.
It retires only new, proven,
unreferenced media after a 24-hour minimum age, checking database references before
every delete and retrying failures on subsequent hourly sweeps. Keep this service running
with the API. See [media operations](IMAGE_MEDIA.md) for permissions and retention rules.

The migration command is an explicit deploy step, not part of API or worker startup.
Review it before running it against a populated database.

## GCP VM

Clone the repository onto a supported Ubuntu/Debian VM. Install Docker once:

```bash
cd ~/salon-backend/backend
bash scripts/gcp-vm-install-docker.sh
```

Log out and back in after Docker group membership changes. Then create the runtime
environment file on the VM:

```bash
cd ~/salon-backend/backend
cp .env.gcp.example .env
chmod 600 .env
# Fill .env with real server-side values on the VM.
```

Runtime secrets belong in `backend/.env` on the VM or in the hosting platform, never
in Git or the image. Local builds on the VM do not require Artifact Registry or
GitHub Actions secrets.

Before each deployment, use the reviewed release checkout, build it, inspect the
database revision, apply reviewed migrations, and deploy. The subshell below stops
on the first error, including a failed migration:

```bash
(
set -e
cd ~/salon-backend/backend
docker compose build
docker compose run --rm --no-deps api alembic current
docker compose run --rm --no-deps api alembic upgrade head
docker compose run --rm --no-deps api alembic current
bash scripts/gcp-vm-deploy.sh
docker compose ps
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/health/db
curl --fail http://127.0.0.1:8000/health/redis
)
```

Stop if a migration fails. A new VM can still connect to an existing database; if its
schema was installed without Alembic tracking, follow the [migration guide](../migrations/README.md)
before applying migrations. Changes must remain compatible with any old services
while migrations run. Neither container startup nor the VM deploy script runs migrations.
Health checks confirm service connectivity; they do not verify the Alembic revision.

If an upgrade fails with `cannot insert multiple commands into a prepared statement`,
use the release containing the corrected migration statement boundaries, rebuild the
image, and retry the explicit upgrade. Do not stamp past the failed revision. The
`0018` and `0021` corrections preserve their revision IDs and SQL schema; databases
already at those revisions do not rerun them.

To test the `0014`-to-head deployment path locally, set `MIGRATION_TEST_DB` to an
explicitly disposable localhost PostgreSQL admin URL with database/role creation
permissions, then run `python -m pytest tests/integration/test_deployment_migration_chain.py`.
The test creates and removes its own database, supplies minimal Supabase Auth
prerequisites, and exercises online Alembic upgrade, repeat upgrade, and `0021`
downgrade/re-upgrade through asyncpg. It never uses the runtime `DATABASE_URL`.

For automated GitHub Actions testing and VM releases, follow [CI/CD setup](CI_CD.md).
Once enabled, use that guide's release wrapper for manual operations.

The deploy script builds from the local checkout by default (`--build`), pulls
`SALON_API_IMAGE` with `--pull`, or uses an already loaded image with `--local-image`.
It validates Compose and updates the API, Redis and all worker services,
waiting up to 120 seconds for readiness. It exits nonzero on failure without an
automatic rollback.

If using an independently published image, authenticate the VM to its registry,
set `SALON_API_IMAGE` to the reviewed image digest, pull it, and apply migrations from
that exact image before calling `bash scripts/gcp-vm-deploy.sh --pull`. Save the digest
and set it again for later manual Compose commands. To restore an earlier image,
set its digest and rerun with `--pull` only after checking database compatibility.

For an alternate runtime env file, set `COMPOSE_ENV_FILE` before calling the script.
It uses that file for both Compose interpolation and container environment settings.
For direct Compose commands, also pass `--env-file "$COMPOSE_ENV_FILE"`.

## Cloud Run

For Cloud Run, deploy the same build context and configure all runtime environment
variables in Cloud Run. Keep the container port aligned with `PORT`.
Cloud Run needs a separately scheduled notification worker or equivalent outbox drainer;
the API process alone does not poll the outbox.

## Payment webhook worker

`docker-compose.yml` has a `payment-webhook-worker` service
(`python -m app.infrastructure.payments.webhook_worker`) alongside `notification-worker`,
`media-cleanup` and `account-deletion-worker` (unchanged here; the deletion worker has its own
heartbeat healthcheck, see `ACCOUNT_DELETION.md`). It retries stored webhook
events, reconciles stale open payment intents and prunes expired idempotency keys. Its HTTP
health check is disabled like the other pollers. It is harmless while
`PAYMENT_PROVIDER=none`.

New environment variables (all optional; defaults in `.env.example`): `PAYMENT_PROVIDER`,
`PAYMENT_SETTLEMENT_MODEL`, `PAYMENT_CURRENCY`, `PAYMENT_ADVANCE_PERCENT`,
`PAYMENT_INTENT_TTL_SECONDS`, `PAYMENT_IDEMPOTENCY_TTL_SECONDS`,
`PAYMENT_WEBHOOK_MAX_BODY_BYTES`, `PAYMENT_WEBHOOK_MAX_ATTEMPTS`,
`PAYMENT_PLATFORM_FEE_PERCENT` and `PAYMENT_COMMISSION_BASE` (**no defaults**: a real provider
refuses to boot without them), `PAYMENT_COMMISSION_POLICY_VERSION`, `PAYMENT_ALLOW_LIVE`,
`PAYMENT_PROVIDER_TIMEOUT_SECONDS`, `PAYMENT_WORKER_POLL_SECONDS`, `PAYMENT_RECONCILE_AFTER_SECONDS`,
and provider credentials: `RAZORPAY_*`, `SUBSCRIPTION_RAZORPAY_WEBHOOK_SECRET`, `CASHFREE_CLIENT_ID`,
`CASHFREE_CLIENT_SECRET`, `CASHFREE_ENVIRONMENT`, `CASHFREE_API_VERSION`, `CASHFREE_WEBHOOK_VERSION`,
`CASHFREE_EASY_SPLIT_ENABLED`, `CASHFREE_RETURN_URL`, `CASHFREE_WEBHOOK_TOLERANCE_SECONDS`.
Subscription billing (separate credentials, default off): `SUBSCRIPTION_PROVIDER`,
`SUBSCRIPTION_RAZORPAY_KEY_ID`, `SUBSCRIPTION_RAZORPAY_KEY_SECRET`, `SUBSCRIPTION_RAZORPAY_WEBHOOK_SECRET`
(>= 32 chars), `SUBSCRIPTION_GRACE_DAYS` (required when enabled, `0` allowed), `SUBSCRIPTION_ALLOW_LIVE`,
`SUBSCRIPTION_ORDER_TTL_SECONDS`, `SUBSCRIPTION_RECONCILE_AFTER_SECONDS`. The same worker service also
reconciles subscription orders and sweeps lapsed periods (migrations 0030-0031 first).
`CASHFREE_ENVIRONMENT=production` fails boot unless `PAYMENT_ALLOW_LIVE=true`. A configured provider with
missing credentials, or `PAYMENT_SETTLEMENT_MODEL=direct_to_salon`, fails container boot on
purpose. Enabling a provider also needs the provider webhook URL
`https://<api>/v1/webhooks/<provider>` registered with the provider (`cashfree`; `razorpay` only for the
separately-secreted subscription hook). The webhook route exists when a payment provider or
`SUBSCRIPTION_PROVIDER` is enabled. Migrations 0029-0031 must be applied before the code.

BUILT: service + env. DORMANT: until a provider is configured. NOT BUILT: a worker
health check (the compose service has none).
