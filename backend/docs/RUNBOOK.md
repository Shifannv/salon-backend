# Runbook

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

## Migrate

```bash
alembic upgrade head
```

The first migration executes `migrations/001_supabase_schema.sql`, which is the v3
baseline schema.

## Common Failures

- Missing Supabase auth settings: required outside `ENVIRONMENT=local` or `test`.
- `GET /health/db` fails: database URL is unreachable or migrations were not applied.
- Auth fails: JWT must verify against Supabase JWKS and the `sub` must exist in
  `profiles`.
