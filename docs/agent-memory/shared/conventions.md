# Conventions

- Every endpoint declares `response_model` and an explicit status code.
- Typed errors live in `backend/app/core/exceptions.py` and are mapped to HTTP once globally. Never return raw Postgres errors, SQL or constraint names.
- Ruff: line length 100, target py312 (`backend/pyproject.toml`).
- pytest-asyncio in auto mode, `testpaths = ["tests"]`.
- Tests: `tests/unit/` (fakes and mocks, most tests), `tests/integration/` (real PostgreSQL via `MIGRATION_TEST_DB`). `tests/conftest.py` has `make_profile`, `make_owner`, `make_super_admin`, `make_booking`, `make_mock_repo`.
- Soft delete via `is_active`. No hard delete except account erasure.
- Alembic revisions are `00NN_name.py` in `backend/migrations/versions/`; baseline SQL is `backend/migrations/001_supabase_schema.sql`.
- Pagination helpers: `backend/app/core/pagination.py`.
- Branch naming: `name/short-description`. One change = one branch = one PR.
