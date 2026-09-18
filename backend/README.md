# Salon Platform API

Shared FastAPI backend for all salon platform clients — customer app, barber/owner app,
and the walk-in QR web app. Frontend apps live in separate repositories and consume
this API through a configured base URL.

---

## Quick Start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env               # then fill in your Supabase + Firebase values
uvicorn app.main:app --reload
```

API docs (Swagger): `http://127.0.0.1:8000/docs`

> **Database migrations** are managed as raw SQL against Supabase Postgres.
> The baseline schema is in `migrations/001_supabase_schema.sql`.
> Incremental changes use Alembic: `alembic upgrade head`.

### Docker

```bash
cd backend
docker build -t salon-platform-api .
docker run --env-file .env -p 8000:8000 salon-platform-api
```

The same Docker image can deploy to GCP Cloud Run. For a GCP VM instance, use
Docker Compose:

```bash
cd backend
cp .env.gcp.example .env
bash scripts/gcp-vm-deploy.sh
```

See [`docs/DOCKER_DEPLOYMENT.md`](docs/DOCKER_DEPLOYMENT.md).

---

## Environment Variables

See the canonical **[Frontend Integration Guide](../docs/frontend-integration.md)** for
required variables, authentication, media uploads, QR rendering, and connection steps.

Minimum required in `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_JWKS_URL=https://xxx.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_SERVICE_ROLE_KEY=eyJ...
BACKEND_CORS_ORIGINS=["http://localhost:19006","http://localhost:8081","http://localhost:3001"]
```

---

## Health

```
GET /health       → { "status": "ok" }
GET /health/db    → { "status": "ok", "database": "reachable" }
```

---

## API Groups

| Prefix | Who uses it | Auth |
|---|---|---|
| `POST /v1/auth/refresh` · `GET /v1/auth/me` | All clients | Public / Bearer JWT |
| `POST /v1/customer/profile/avatar` · `/v1/reports` | Customer app | Bearer JWT |
| `GET /v1/salons` · `/{id}` · `/services` · `/staff` | Customer app | Public |
| `GET /v1/availability` | Customer app, walk-in web | Public |
| `GET/POST /v1/bookings` · `/cancel` · `/approve` · `/reject` | Customer & owner apps | Bearer JWT |
| `GET/PATCH /v1/salons/me` · `/services` · `/staff` · `/blocks` | Owner/barber app | Bearer JWT (owner) |
| `GET /v1/salons/me/qr` · `/images/upload-url` | Owner/barber app | Bearer JWT (owner) |
| `GET /v1/walkin/{token}` · `/verify-phone` · `/bookings` | Walk-in QR web | Public / Phone OTP JWT |
| `GET /v1/notifications` · `/devices` | All apps | Bearer JWT |
| `POST /v1/admin/salons` · `/categories` · `/subcategories` | Admin only | Bearer JWT (super_admin) |

---

## Auth

Clients authenticate through Supabase Auth. The backend verifies Supabase JWTs against
the project JWKS endpoint and resolves the verified `sub` to `profiles.id`.

```
POST /v1/auth/refresh        → { access_token, refresh_token }
GET  /v1/auth/me             → Profile
```

Google sign-in is started by the frontend through Supabase Auth. The backend does not
accept email/password login; clients send the Supabase access token returned after
Google OAuth.

All protected requests require:

```
Authorization: Bearer <supabase_access_token>
```

---

## Walk-in QR Flow

Each salon has a unique `qr_token` (auto-generated in the database). The barber app
displays a QR code encoding:

```
https://walkin.yourdomain.com/s/{qr_token}
```

Scanning opens the walk-in web app. The customer picks a slot, verifies by phone OTP,
and books — no app install required. The booking lands in the same `bookings` table the
barber app reads from.

---

## Architecture

Clean layered architecture — see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

```
api/ → application/ → domain/
infrastructure/ → domain/application ports
```

- `domain/` — pure Python, no external dependencies
- `application/` — use cases, authorization, gateway ports
- `infrastructure/` — SQLAlchemy repo, Supabase gateways, FCM gateway
- `api/` — FastAPI routers, Pydantic schemas, dependency wiring

---

## Key Rules

- Do not modify the database schema through application code — use Alembic migrations.
- Booking creation must call the Postgres `create_booking` function.
- Availability must come from the Postgres `get_available_slots` function.
- Authorization belongs in use cases, not routers or repositories.

---

## Tests

```bash
cd backend
.venv/bin/python -m pytest          # run all tests
.venv/bin/python -m ruff check app  # lint
```

115 tests — all passing at the latest documented verification.

---

## Further Reading

| Document | Contents |
|---|---|
| [`../docs/frontend-integration.md`](../docs/frontend-integration.md) | Canonical frontend connection guide |
| [`docs/salon-platform-api-reference.md`](docs/salon-platform-api-reference.md) | Detailed endpoint reference |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Layer diagram and rules |
| [`docs/AUTHORIZATION.md`](docs/AUTHORIZATION.md) | Role-based access, JWT flow |
| [`docs/BOOKING_FLOW.md`](docs/BOOKING_FLOW.md) | Booking lifecycle, approval modes |
| [`docs/RUNBOOK.md`](docs/RUNBOOK.md) | Deployment, startup, troubleshooting |
