# Folder structure

```text
salon-backend/
  backend/
    app/
      api/              HTTP routes, schemas, dependency wiring
      application/      use cases and gateway ports
      domain/           pure business types and rules
      infrastructure/   database and external-service adapters
    migrations/         SQL baseline and Alembic revisions
    tests/              automated tests
    docs/               backend technical and operational notes
    Dockerfile
    docker-compose.yml
    requirements*.txt
  docs/                 concise project-level decisions
  .github/workflows/    CI, deployment on main pushes, and manual deployment
```

Frontend source does not belong in this repository. Do not move code between the four
application layers without an explicit architecture change.
