# Technology stack

| Area | Technology |
| --- | --- |
| API | Python 3.12+, FastAPI, Pydantic v2 |
| Database | Supabase Postgres, SQLAlchemy 2 async, asyncpg |
| Authentication | Supabase Auth JWT and JWKS |
| Migrations | Alembic with a raw SQL baseline |
| Media | Cloudflare R2 |
| Push notifications | Firebase Cloud Messaging |
| Cache & Idempotency | Redis 7, redis-py async |
| Tests and lint | pytest, pytest-asyncio, Ruff |
| Runtime | Docker, Docker Compose, GCP VM; optional Cloud Run |

Runtime dependencies are listed in `backend/requirements.txt`. Development tools are
listed in `backend/requirements-dev.txt`; `backend/pyproject.toml` contains only tool
configuration.
