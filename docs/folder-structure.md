# Folder Structure

## Repository Decision

This repository is backend-only. It contains the shared FastAPI API used by all salon
platform clients.

Do not pull customer, barber, admin, or walk-in frontend code into this repository unless
the team explicitly changes to a monorepo.

Recommended repo layout across the platform:

```txt
salon-shared-api/      This repo: FastAPI backend
salon-customer-app/    Expo customer app
salon-barber-app/      Expo barber/owner app
salon-admin-portal/    Future admin web app
salon-walkin-web/      Future walk-in QR web app
```

## Current Repository Structure

```txt
salon-shared-api/
  README.md
  AGENTS.md
  .gitignore

  docs/
    README.md
    project-overview.md
    tech-stack.md
    features.md
    folder-structure.md
    frontend-integration.md
    database-plan.md
    git-workflow.md

  backend/
    README.md
    pyproject.toml
    alembic.ini
    .env.example

    app/
      main.py

      core/
        config.py
        security.py
        exceptions.py
        logging.py
        pagination.py

      domain/
        entities/
        repositories/
        services/

      application/
        dto/
        ports/
        use_cases/

      infrastructure/
        db/
          session.py
          repositories/
        r2/
        supabase/
        push/

      api/
        deps.py
        v1/
          router.py
          schemas/
          routes/
            media.py
            reports.py

    migrations/
      env.py
      001_supabase_schema.sql
      versions/

    tests/
      unit/
      integration/

    docs/
      ARCHITECTURE.md
      AUTHORIZATION.md
      BOOKING_FLOW.md
      RUNBOOK.md
```

## Backend Code Area

Thameem mainly works in:

```txt
backend/app/
backend/migrations/
backend/tests/
backend/docs/
docs/database-plan.md
```

## API Layering Rule

Dependencies should point inward:

```txt
api -> application -> domain
infrastructure -> domain/application ports
```

- `domain/` contains pure Python entities, repository ports, and rules.
- `application/` contains use cases and gateway ports.
- `infrastructure/` contains SQLAlchemy, Supabase, Firebase, and external adapters.
- `api/` contains FastAPI routes, request/response schemas, and dependency wiring.

## Frontend Integration

Frontend apps connect by API base URL.

Local development examples:

```txt
http://localhost:8000          iOS simulator
http://10.0.2.2:8000           Android emulator
http://YOUR_MAC_IP:8000        Real mobile device on same Wi-Fi
```
