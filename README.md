# Salon Platform API

Backend-only FastAPI service shared by the customer, owner/barber, admin, and walk-in
clients. Frontend applications live in separate repositories.

## Local development


Requirements: Python 3.12+ and a Supabase Postgres project.

```bash
cd backend
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload

or 
Set-Location D:\salon\salon-backend
.\.venv\Scripts\Activate.ps1
Set-Location backend
```

Set the real values in `backend/.env`; never commit that file. Swagger UI is available
at `http://127.0.0.1:8000/docs` and the health endpoint is `/health`.

Run policy tests:
```bash 
$runTemp = Join-Path (Get-Location) (".pytest-tmp-" + [guid]::NewGuid().ToString("N"))

python -m pytest -q tests/unit/test_migration_policy.py `
  --basetemp $runTemp `
  -p no:cacheprovider

Remove-Item -LiteralPath $runTemp -Recurse -Force
```
## Checks

```bash
cd backend
python -m pytest
python -m ruff check app tests migrations
```

## Docker

Use `backend/` as the build context:

```bash
cd backend
docker compose up -d --build api redis
or
docker compose up --build -d
docker compose ps

View API logs:
docker compose logs -f api

Stop the API and Redis:
docker compose stop api redis
run the backend local : 
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000


```

Migrations are an explicit deployment step and are not run by the container startup
command.

## Documentation

- [Project docs](docs/README.md)
- [Backend runbook](backend/docs/RUNBOOK.md)
- [Docker deployment](backend/docs/DOCKER_DEPLOYMENT.md)
- [Database migrations](backend/docs/migrations/README.md)
