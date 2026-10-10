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

## Account deletion worker

- Compose service `account-deletion-worker` drains `account_deletion_requests`. If it is not
  running, confirmed accounts are locked but not erased; start it and check logs.
- A request stuck in `failed` retries with backoff (30 s doubling to 1 h) and records only an
  error class in `last_error_code` (for example `ServiceUnavailableError` = Supabase down,
  `ErasureVerificationError` = a post-condition failed). Fix the cause; do not edit rows to
  force `completed`.
- Migrations `0020` then `0021` must be applied explicitly before enabling the feature.
- Full procedure and data matrix: `ACCOUNT_DELETION.md`.
