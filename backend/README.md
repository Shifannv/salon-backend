# Salon Platform API

Shared FastAPI API layer for the salon platform clients.

This repository is backend-only. Customer, barber/owner, admin, and walk-in frontends
should live in separate repositories and consume this API through a configured base URL.

## Quick Start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Open:

```txt
http://127.0.0.1:8000/docs
```

## Health

```txt
GET /health
GET /health/db
```

## Frontend Connection

Frontend apps should use an environment variable such as:

```txt
EXPO_PUBLIC_API_BASE_URL=http://YOUR_MAC_IP:8000
```

After deployment, point the same variable to the deployed API domain:

```txt
EXPO_PUBLIC_API_BASE_URL=https://api.yourdomain.com
```

## Auth

Clients authenticate through Supabase Auth. The API verifies Supabase JWTs against JWKS
and resolves the verified `sub` to `profiles.id`.

```txt
POST /v1/auth/login
POST /v1/auth/refresh
GET /v1/auth/me
```

## Architecture

This backend now follows the new phase-based architecture in `docs/ARCHITECTURE.md`.
Legacy `/api/v1` local-password routes are no longer mounted by `app.main`.

## Migration Notes

- The v3 SQL schema in `migrations/001_supabase_schema.sql` is the baseline.
- Schema changes must be reviewed Alembic migrations.
- Booking creation and availability must call database functions, not Python logic.
