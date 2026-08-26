# Runbook

Operational procedures for the Salon Platform API.

---

## Prerequisites

```bash
cd backend
source .venv/bin/activate  # or: .venv/bin/python for one-off commands
```

---

## Running Locally

```bash
# Install dependencies (first time or after pyproject.toml changes)
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Edit .env with your Supabase project values

# Run the dev server with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The OpenAPI docs are at http://localhost:8000/docs.

---

## Running Tests

```bash
# Unit tests only (no database required)
./.venv/bin/python -m pytest tests/unit/ -v

# All tests (requires a running Postgres)
./.venv/bin/python -m pytest -v

# Lint
./.venv/bin/python -m ruff check app tests migrations
```

---

## Database Migrations

> **Source of truth:** `migrations/001_supabase_schema.sql` is the authoritative schema baseline.
> Never hand-translate the baseline SQL into ORM code.

### Apply pending migrations

```bash
./.venv/bin/alembic upgrade head
```

### Create a new migration

```bash
./.venv/bin/alembic revision --autogenerate -m "describe_the_change"
# Review the generated file in migrations/versions/ before committing.
```

> **Rule:** Never modify `migrations/001_supabase_schema.sql` after it has been
> applied to production. Add new migrations as separate version files.

### Roll back one migration

```bash
./.venv/bin/alembic downgrade -1
```

### Show migration history

```bash
./.venv/bin/alembic history --verbose
```

---

## Environment Variables

| Variable | Required in prod | Purpose |
|---|---|---|
| `DATABASE_URL` | ✅ | asyncpg connection string |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | Public anon key (safe for clients) |
| `SUPABASE_JWKS_URL` | ✅ | JWKS endpoint for JWT verification |
| `SUPABASE_JWT_AUDIENCE` | ✅ | Usually `authenticated` |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Service-role key — NEVER expose to clients |
| `FIREBASE_CREDENTIALS_JSON` | ❌ optional | Service account JSON string for FCM push. FCM is a no-op if absent. |
| `BACKEND_CORS_ORIGINS` | ✅ | JSON list of allowed origins |
| `ENVIRONMENT` | ✅ | `local` / `test` / `production` |

---

## Common Failure Modes

### Server refuses to start

**Symptom:** `ValueError: Missing required production settings: SUPABASE_SERVICE_ROLE_KEY`

**Fix:** Add the missing env var to the deployment configuration. In `local` / `test`
environments this validation is skipped.

---

### 401 Unauthorized on all endpoints

**Possible causes:**

1. **JWKS URL misconfigured** — `SUPABASE_JWKS_URL` points to the wrong project.
   Check: `curl $SUPABASE_JWKS_URL` should return a `{"keys":[...]}` JSON.

2. **Token audience mismatch** — `SUPABASE_JWT_AUDIENCE` must match the `aud` claim
   in the Supabase JWT (usually `authenticated`).

3. **Clock skew** — The server clock is more than 60 seconds off from Supabase.
   Check `date` on the server.

---

### 409 Slot Unavailable on booking creation

**This is expected behaviour** — the `create_booking` Postgres function detected
that the slot was taken between the availability check and the booking call.

**Client behaviour:** Re-fetch `/availability` and prompt the user to choose again.

**Not a bug unless** the 409 fires even when no competing booking exists.
In that case, query the `blocked_slots` table for the staff member and the time range.

---

### Push notifications not delivered

1. Check `FIREBASE_CREDENTIALS_JSON` is set and is valid JSON. Store the service-account
   JSON as an environment variable on the server; do not commit the JSON file.
2. Query `notification_deliveries` for `delivered = false` rows and inspect `error`.
3. Expo app tokens start with `ExponentPushToken[` and are sent through Expo's push API.
   Raw FCM registration tokens require `FIREBASE_CREDENTIALS_JSON`.
4. If `error` contains `registration-token-not-registered` or Expo reports
   `DeviceNotRegistered`, the device token is stale. The gateway deactivates it
   automatically on first failure — no action needed.

---

### Database pool exhausted

**Symptom:** `asyncpg.exceptions.TooManyConnectionsError` or timeouts.

**Short-term fix:** Restart the server to flush the pool.

**Long-term fix:** Increase `DB_POOL_SIZE` and `DB_MAX_OVERFLOW`, or switch to Supabase
Pooler (PgBouncer transaction mode) by using the pooler URL format:
```
DATABASE_URL=postgresql+asyncpg://postgres.PROJECT_REF:PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

---

## Deployment Checklist

- [ ] All required env vars are set
- [ ] `alembic upgrade head` ran successfully
- [ ] `GET /health/db` returns `{"status": "ok"}`
- [ ] At least one admin user exists in `profiles` with `role = 'super_admin'`
- [ ] CORS origins are restricted to the production app domains
- [ ] `FIREBASE_CREDENTIALS_JSON` is set if push notifications are required
