# Docker deployment

Use `backend/` as the Docker build context.

## Local

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
curl http://127.0.0.1:8000/health
```

The image runs as a non-root user, listens on `0.0.0.0`, respects `PORT`, and checks
`/health`. It contains Alembic and the migration files, but does not apply migrations at
startup.

Apply reviewed migrations separately:

```bash
docker compose run --rm api alembic upgrade head
```

## GCP VM

On a supported Ubuntu/Debian VM, install Docker once and then deploy:

```bash
cd backend
bash scripts/gcp-vm-install-docker.sh
cp .env.gcp.example .env
# Fill .env with real server-side values.
bash scripts/gcp-vm-deploy.sh
```

The manual GitHub Actions deployment builds from `backend/`, pushes to Artifact
Registry, and updates the VM. Runtime secrets belong in `backend/.env` on the VM or in
the hosting platform, never in the image.

For Cloud Run, deploy the same build context and configure all runtime environment
variables in Cloud Run. Keep the container port aligned with `PORT`.
