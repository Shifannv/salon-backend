# FastAPI + Supabase Database Guide

Yes, this backend can connect to a Supabase database.

Supabase is PostgreSQL, and FastAPI can connect to it through SQLAlchemy using a normal Postgres connection string.

## Recommended Setup

Use FastAPI as the backend API layer and Supabase as the PostgreSQL database.

```txt
Customer App / Barber App
  -> FastAPI API
  -> SQLAlchemy
  -> Supabase PostgreSQL
```

In this setup:

- FastAPI handles API routes.
- FastAPI handles JWT auth and role checks.
- SQLAlchemy reads and writes the Supabase Postgres tables.
- Supabase stores the real production data.

## Environment Variables

In `backend/.env`, set:

```env
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/postgres
AUTO_CREATE_TABLES=false
SECRET_KEY=replace-with-a-strong-secret
ACCESS_TOKEN_EXPIRE_MINUTES=1440
BACKEND_CORS_ORIGINS=["http://localhost:19006","http://localhost:3000"]
```

For Supabase pooler, the URL usually looks similar to:

```env
DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:YOUR_DB_PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

Use the exact connection string from:

```txt
Supabase Dashboard -> Project Settings -> Database -> Connection string
```

## Why `AUTO_CREATE_TABLES=false`

Local SQLite development can use:

```env
AUTO_CREATE_TABLES=true
```

But for Supabase production, use:

```env
AUTO_CREATE_TABLES=false
```

Reason:

The schema should be created by SQL migrations, not by `Base.metadata.create_all()`.

Your prompt SQL file contains PostgreSQL-specific features like:

- extensions
- enums
- triggers
- RLS policies
- Supabase `auth.uid()`
- RPC functions
- exclusion constraints

Those should be applied directly to Supabase as SQL migrations.

## Important Difference: Direct DB vs Supabase RLS

Your prompt schema is designed for Supabase with Row Level Security.

When FastAPI connects directly to PostgreSQL with SQLAlchemy, RLS does not automatically behave like the Supabase client unless you design for it.

There are two possible approaches.

## Option A: FastAPI Enforces Permissions

This is the current backend approach.

```txt
FastAPI validates the token
FastAPI checks role/ownership
FastAPI writes to Supabase Postgres
```

Pros:

- Simple for custom backend APIs.
- Easy to debug.
- Works well for customer app and barber app.
- Keeps all business rules in Python services.

Cons:

- You must be careful to enforce permissions in FastAPI.
- Supabase RLS is not the main protection layer for API requests.

Current files that enforce permissions:

```txt
app/api/deps.py
app/services/permissions.py
app/api/routes/barber.py
app/api/routes/bookings.py
```

## Option B: Supabase RLS Enforces Permissions

In this approach, FastAPI would call Supabase using user JWTs or configure the database session so `auth.uid()` works correctly.

Pros:

- RLS remains the main security source.
- Matches Supabase-style app development.

Cons:

- More complex with SQLAlchemy direct connections.
- Requires careful JWT/session claim handling.
- More difficult than Option A for a custom FastAPI backend.

## Recommended For This Project

Use Option A first:

```txt
FastAPI permissions + Supabase PostgreSQL storage
```

This matches the backend already built.

Later, when the backend is stable, we can add:

- exact PostgreSQL migrations from your prompt SQL
- database-level booking overlap constraint
- stronger audit fields
- optional RLS for extra protection

## Schema Compatibility Status

The current SQLAlchemy models follow your prompt schema closely, but they are not exact 1:1 yet.

Already represented:

- `profiles`
- `salons`
- `salon_images`
- `salon_holidays`
- `service_categories`
- `service_subcategories`
- `services`
- `staff`
- `languages`
- `staff_services`
- `staff_service_languages`
- `blocked_slots`
- `bookings`
- `booking_services`
- `notifications`
- `device_tokens`

Not exact yet:

- Supabase `auth.users` relationship
- RLS policies
- trigger functions
- audit columns like `created_by` and `updated_by`
- `notification_deliveries`
- PostgreSQL exclusion constraint for no-overlap bookings
- Supabase RPC functions

## Best Next Step For Exact Supabase Schema

Create a migration file from your prompt SQL:

```txt
backend/migrations/001_supabase_schema.sql
```

Then apply it to Supabase:

```txt
Supabase Dashboard -> SQL Editor -> paste/run migration
```

Or use Supabase CLI:

```bash
supabase db push
```

After the exact SQL schema is applied, update SQLAlchemy models to match it exactly.

## Install Dependencies

The backend now includes the PostgreSQL driver:

```txt
psycopg[binary]
```

Install/update:

```bash
cd backend
source .venv/bin/activate
pip install -e ".[dev]"
```

## Test Connection

After setting `DATABASE_URL`, run:

```bash
python - <<'PY'
from sqlalchemy import text
from app.db.session import engine

with engine.connect() as conn:
    print(conn.execute(text("select now()")).scalar())
PY
```

If this prints a timestamp, FastAPI can connect to Supabase.

## Run API With Supabase

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open:

```txt
http://127.0.0.1:8000/docs
```

## Short Answer

Yes:

```txt
FastAPI + Supabase database is possible.
```

The clean architecture is:

```txt
FastAPI for APIs and business rules
Supabase PostgreSQL for database storage
SQL migrations for exact schema
SQLAlchemy for queries
```

