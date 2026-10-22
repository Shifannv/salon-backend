# Agent Instructions

At the start of each chat and when the task changes, read
`docs/agent-skill-routing.md` for task-relevant skill selection across the backend,
customer app and owner app. Keep the backend-first working standard below.

This repository contains the shared FastAPI backend API for the salon platform.

It is backend-only. Customer, barber/owner, admin, and walk-in frontend apps should live
in separate repositories and consume this API through environment-configured base URLs.
Do not pull frontend app code into this repository unless the team explicitly changes to
a monorepo.

Before anything else in a new chat, read `.claude/skills/senior-backend-engineer/SKILL.md`. It is the binding working standard for investigating errors, improving code, cleaning up and reporting results.

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
5. `backend/docs/DOCKER_DEPLOYMENT.md`

## Source of Truth

Project documentation and verified repository behavior describe the project direction
and current implementation status. Keep implemented features, limitations, and future
ideas clearly distinguished. No external task tracker is required.

## Tech Stack

- Shared API: Python 3.12+, FastAPI, Pydantic v2
- Database access: SQLAlchemy 2.x async with asyncpg
- Backend/database: Supabase Postgres
- Authentication provider: Supabase Auth JWTs
- Migrations: Alembic, with the v3 SQL schema as the raw SQL baseline
- Push notifications: Firebase / FCM
- Container/runtime deployment: Docker, Docker Compose, GCP Compute Engine VM, optional GCP Cloud Run
- Tests: pytest and pytest-asyncio

## Code Ownership

- Thameem owns backend work in `backend/app/`, `backend/migrations/`, `backend/tests/`, and `backend/docs/`.
- Backend deployment/config ownership also includes `backend/Dockerfile`, `backend/docker-compose.yml`, `backend/.dockerignore`, `backend/.env.example`, `backend/.env.gcp.example`, `backend/scripts/`, `backend/requirements*.txt`, and `backend/pyproject.toml`.
- Shifan owns frontend apps in their separate repositories.
- Docs in `docs/` describe shared project decisions and should stay aligned with backend reality.

## Secrets And Environment

- Never commit real environment files or secrets. `backend/.env` must stay ignored.
- Commit only templates such as `backend/.env.example` and `backend/.env.gcp.example`.
- Treat Supabase service-role keys, database URLs, JWTs, Firebase credentials, and private keys as secrets even if a user pastes them into chat.
- Do not copy real secrets into docs, tests, Dockerfiles, Compose files, examples, logs, or final answers.
- Runtime secrets for GCP VM deployment belong in `backend/.env` on the VM, or in the hosting provider's secret/environment settings.
- Keep `BACKEND_CORS_ORIGINS` environment-driven; do not hard-code frontend production URLs in application code.

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
- Keep the v3 SQL baseline in `backend/migrations/sql/001_supabase_schema.sql` as the schema source of truth.
- Do not hand-translate the baseline SQL into ORM migrations.
- Bookings must be created only through the Postgres `create_booking` function.
- Availability must come only from the Postgres `get_available_slots` function.
- Do not insert directly into `bookings` or `booking_services` from Python.
- Do not compute available slots in Python.
- Use soft delete through `is_active`; do not add hard-delete behavior for platform data.
  The one scoped exception is verified, user-confirmed account erasure (`backend/docs/ACCOUNT_DELETION.md`),
  which hard-deletes the account's profile and Supabase Auth identity and anonymizes retained records.
  Do not extend it to other entities.
- Do not expose raw Postgres errors, constraint names, or SQL fragments in HTTP responses.

## Deployment Rules

- The current backend deployment target is GCP VM Instance + Docker Compose, with optional GCP Cloud Run support.
- Render deployment files should not be reintroduced unless the project owner explicitly asks for Render again.
- Docker build context should be `backend/`; do not build images from the repository root unless the Dockerfile and ignore rules are intentionally changed.
- Keep the backend image backend-only. Do not copy frontend app code into the Docker image.
- Use `backend/Dockerfile` for the API image and `backend/docker-compose.yml` for GCP VM runtime.
- Use `backend/scripts/gcp-vm-install-docker.sh` to bootstrap Docker on an Ubuntu/Debian GCP VM.
- Use `backend/scripts/gcp-vm-deploy.sh` to build and run/update the API container on the VM.
- Do not run Alembic migrations automatically in the container startup command. Migrations must be a reviewed, explicit deploy step.
- For VM deployment, `backend/.env` should be created from `backend/.env.gcp.example` and filled on the VM only.
- The API container must bind to `0.0.0.0` and read `PORT`, defaulting to `8000`.
- Keep health checks pointed at `/health`.

## Dependency And Setup Files

- Keep runtime dependencies in `backend/requirements.txt` and development-only tools in `backend/requirements-dev.txt`.
- Keep pytest and Ruff configuration in `backend/pyproject.toml`.
- Prefer `pip install -r requirements.txt` for production container builds.
- Prefer `pip install -r requirements-dev.txt` for local development.

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

Use one focused branch and pull request per coherent change:

```txt
one coherent change = one branch = one pull request
```

Use descriptive branch names:

```txt
thameem/backend-foundation
thameem/superadmin-website-contract
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
./.venv/bin/pip install -r requirements-dev.txt
```

For deployment-file changes, additionally check what is feasible locally:

```bash
bash -n scripts/gcp-vm-install-docker.sh
bash -n scripts/gcp-vm-deploy.sh
docker build -t salon-platform-api .
```

If Docker is not installed or the daemon is unavailable, say that clearly and still run the Python tests/lint and shell syntax checks.
