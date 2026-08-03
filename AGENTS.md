# Agent Instructions

This repository contains the shared FastAPI backend API for the salon platform.

It is backend-only. Customer, barber/owner, admin, and walk-in frontend apps should live
in separate repositories and consume this API through environment-configured base URLs.
Do not pull frontend app code into this repository unless the team explicitly changes to
a monorepo.

Before making code changes, read the project documentation in this order:

1. `docs/README.md`
2. `docs/project-overview.md`
3. `docs/tech-stack.md`
4. `docs/folder-structure.md`
5. `docs/database-plan.md`
6. `docs/features.md`

Then read workflow/integration docs as needed:

- Git/branch work: `docs/git-workflow.md`
- Frontend integration questions: `docs/frontend-integration.md`

For backend architecture details, also read:

1. `backend/docs/ARCHITECTURE.md`
2. `backend/docs/AUTHORIZATION.md`
3. `backend/docs/BOOKING_FLOW.md`
4. `backend/docs/RUNBOOK.md`

## Source of Truth

Jira is the source of truth for task status, assignee, priority, and acceptance criteria.

Do not invent extra tasks in the docs without creating or updating Jira first.

## Tech Stack

- Shared API: Python 3.12+, FastAPI, Pydantic v2
- Database access: SQLAlchemy 2.x async with asyncpg
- Backend/database: Supabase Postgres
- Authentication provider: Supabase Auth JWTs
- Migrations: Alembic, with the v3 SQL schema as the raw SQL baseline
- Push notifications: Firebase / FCM
- Tests: pytest and pytest-asyncio

## Code Ownership

- Thameem owns backend work in `backend/app/`, `backend/migrations/`, `backend/tests/`, and `backend/docs/`.
- Shifan owns frontend apps in their separate repositories.
- Docs in `docs/` describe shared project decisions and should stay aligned with backend reality.

## Backend Architecture Rules

Follow clean architecture layering:

```txt
api -> application -> domain
infrastructure -> domain/application ports
```

- `domain/` must stay pure Python. It must not import FastAPI, SQLAlchemy, Supabase SDKs, Firebase SDKs, or HTTP Pydantic schemas.
- `application/` contains use cases and gateway ports. Authorization belongs in use cases, not routers or repositories.
- `infrastructure/` implements repository/gateway ports and contains database, Supabase, Firebase, and external-service adapters.
- `api/` contains FastAPI routers, request/response schemas, auth extraction, and dependency wiring.
- Every endpoint must declare an explicit `response_model` and status code.
- Typed application exceptions live in `backend/app/core/exceptions.py` and are mapped to HTTP once globally.

## Database And Booking Rules

- Do not modify the database schema through application code.
- Schema changes must be reviewed Alembic migrations.
- Keep the v3 SQL baseline in `backend/migrations/001_supabase_schema.sql` as the schema source of truth.
- Do not hand-translate the baseline SQL into ORM migrations.
- Bookings must be created only through the Postgres `create_booking` function.
- Availability must come only from the Postgres `get_available_slots` function.
- Do not insert directly into `bookings` or `booking_services` from Python.
- Do not compute available slots in Python.
- Use soft delete through `is_active`; do not add hard-delete behavior for platform data.
- Do not expose raw Postgres errors, constraint names, or SQL fragments in HTTP responses.

## Auth Rules

- Supabase remains the identity provider.
- Clients send `Authorization: Bearer <Supabase JWT>`.
- The backend verifies JWT signatures against Supabase JWKS.
- Resolve the verified JWT `sub` to `profiles.id`; do not trust role claims from token bodies.
- Fine-grained ownership checks must happen in use cases.
- For authenticated database work, set actor context with:

```sql
SET LOCAL request.jwt.claims = '{"sub": "<verified-user-uuid>"}';
```

This lets database audit triggers stamp the correct actor.

## Workflow

Use one branch per Jira task:

```txt
one Jira task = one branch = one pull request
```

Use branch names that include the Jira key:

```txt
thameem/SACS-14-backend-foundation
thameem/SACS-48-backend-location
```

Do not commit directly to stable `main` unless explicitly requested by the project owner.

## Verification

Before finishing backend changes, run from `backend/` when possible:

```bash
./.venv/bin/python -m pytest
./.venv/bin/python -m ruff check app tests migrations
```

If dependencies are missing, install with:

```bash
./.venv/bin/pip install -e ".[dev]"
```
