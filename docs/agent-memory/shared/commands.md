# Commands

Run from `backend/` unless noted. AGENTS.md uses `./.venv/bin/python`; on Windows use `.venv/Scripts/python` or plain `python`.

- Install: `pip install -r requirements-dev.txt`
- Run API: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Lint: `python -m ruff check app tests migrations`
- Test: `python -m pytest -q` (CI also sets `MIGRATION_TEST_DB` so integration tests run)
- Migrate (explicit, local DB only): `alembic upgrade head`; check with `alembic current`
- Compose config check: `docker compose --env-file .env.gcp.example -f docker-compose.yml config --quiet`
- Shell script syntax: `bash -n scripts/gcp-vm-deploy.sh`
- Deploy: push to `main` -> GitHub Actions `.github/workflows/backend.yml` (lint and test -> image build and smoke test -> deploy to GCP VM over SSH). Migrations are a separate explicit step.
- Base branch: `main`.
