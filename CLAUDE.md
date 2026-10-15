# salon-backend

Shared FastAPI backend for a salon booking platform. Four clients (customer app, owner app, admin website, walk-in QR website, all in separate repos) call this one `/v1` API.
Stack: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 async + asyncpg, Supabase Postgres/Auth, Alembic, Redis, R2, FCM/Expo, Docker Compose on a GCP VM.

`AGENTS.md` is binding and holds the full rules. Read `docs/README.md` first for project docs; `backend/docs/` for architecture detail.

## Layer map

```
api -> application -> domain
infrastructure -> application/domain ports
```

- `backend/app/domain/`: pure Python, no framework imports.
- `backend/app/application/`: use cases (authorization here), ports.
- `backend/app/infrastructure/`: DB, Supabase, R2, push, payments, cache, email, workers.
- `backend/app/api/`: routers, schemas, `deps.py` auth and wiring.

## Key rules

1. Schema changes only through reviewed Alembic migrations. Never run them at container startup.
2. Create bookings only via Postgres `create_booking()`; get availability only from `get_available_slots()`. No direct inserts into `bookings`/`booking_services`, no slot math in Python.
3. Role comes from `profiles` in the DB, never from JWT claims. Super-admin needs `aal2`.
4. Ownership and authorization checks live in use cases, not routers or repositories.
5. Soft delete via `is_active`. Hard delete only for verified account erasure.
6. Never expose raw Postgres errors, SQL or constraint names over HTTP.
7. Secrets never go in Git, logs, docs or frontend env. Never read `.env` files.
8. Every endpoint has an explicit `response_model` and status code.
9. One branch = one PR = one coherent change. Never commit to `main` directly.

## Commands (run from `backend/`)

- Lint: `python -m ruff check app tests migrations`
- Test: `python -m pytest -q`
- Run: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Migrate (explicit, local DB only): `alembic upgrade head`
- More: `docs/agent-memory/shared/commands.md`

## Session protocol

Run `/start` first and `/wrap` last. `/checkpoint` saves mid-session. Memory lives in `docs/agent-memory/` (per-branch `progress/`, durable `shared/`, index `SESSIONS.md`). Read the `agent-memory` skill before editing it.

## Skills (`.claude/skills/`)

- `karpathy-guidelines`: always apply when writing or reviewing code.
- `agent-memory`: when reading or writing docs/agent-memory.
- `fastapi-endpoint`: adding or changing an endpoint.
- `auth-and-roles`: anything touching JWT, roles, MFA or ownership.
- `alembic-migration`: any schema change.
- `booking-and-payments`: booking, availability, payment or webhook work.
- `pytest-testing`: writing or fixing tests.
- `workers-and-deploy`: workers, Compose, CI or deploy.

## Agents (`.claude/agents/`)

- `code-refactorer`: review and harden code on the branch before commit.
- `refactorer`: behavior-preserving refactor under tests.
- `code-reviewer`: diff review against the key rules.
- `security-reviewer`: auth, IDOR, leaks, secrets, webhooks.
- `performance-analyst`: queries, indexes, caching, pooling.
- `migration-reviewer`: any new Alembic revision.
- `test-writer`: add tests to existing code.
- `debugger`: reproduce and fix a failing behavior.

Commands: `/start`, `/wrap`, `/checkpoint`, `/review`, `/new-endpoint`, `/new-migration`, `/check`.
