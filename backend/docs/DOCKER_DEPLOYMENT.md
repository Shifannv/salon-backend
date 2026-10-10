# Docker deployment

Deploy manually with Docker Compose on the GCP VM. This branch contains no GitHub
Actions workflows. Run verification locally before deploying.

Use `backend/` as the Docker build context.
Use Docker Compose v2 with `up --wait` and `--wait-timeout` support.

## Local

```bash
cp .env.example .env
docker compose build
docker compose run --rm api alembic upgrade head
docker compose up -d --wait --wait-timeout 120
docker compose ps
curl http://127.0.0.1:8000/health
```

The image runs as a non-root user, listens on `0.0.0.0`, respects `PORT`, and checks
`/health`. It contains Alembic and the migration files, but does not apply migrations at
startup.

Compose also runs `notification-worker` from the same image. It retries persisted push
events every 15 seconds and exposes no port. Apply migration `0013_booking_action_requests`
before starting code that uses the worker.

The worker disables the image's API-only HTTP health check. Compose waits for API and
Redis health and for the worker process to start; this does not verify successful push
delivery. Check worker logs and notification delivery records when diagnosing push.
Redis is accessible only inside the Compose network at `redis:6379`, not on a VM port.
The API waits for Redis health before starting. API and worker share runtime settings.

The migration command is an explicit deploy step, not part of API or worker startup.
Review it before running it against a populated database.

## GCP VM

Clone the repository onto a supported Ubuntu/Debian VM. Install Docker once:

```bash
cd ~/salon-backend/backend
bash scripts/gcp-vm-install-docker.sh
```

Log out and back in after Docker group membership changes. Then create the runtime
environment file on the VM:

```bash
cd ~/salon-backend/backend
cp .env.gcp.example .env
chmod 600 .env
# Fill .env with real server-side values on the VM.
```

Runtime secrets belong in `backend/.env` on the VM or in the hosting platform, never
in Git or the image. Local builds on the VM do not require Artifact Registry or
GitHub Actions secrets.

Before each deployment, use the reviewed release checkout, build it, inspect the
database revision, apply reviewed migrations, and deploy:

```bash
cd ~/salon-backend/backend
docker compose build
docker compose run --rm --no-deps api alembic current
docker compose run --rm --no-deps api alembic upgrade head
bash scripts/gcp-vm-deploy.sh
docker compose ps
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/health/db
curl --fail http://127.0.0.1:8000/health/redis
```

Stop if a migration fails. A new VM can still connect to an existing database; if its
schema was installed without Alembic tracking, follow the [migration guide](../migrations/README.md)
before applying migrations. Changes must remain compatible with any old services
while migrations run. Neither container startup nor the VM deploy script runs migrations.

The deploy script builds from the local checkout by default (`--build`), or pulls
`SALON_API_IMAGE` with `--pull`. It validates Compose and updates all three services,
waiting up to 120 seconds for readiness. It exits nonzero on failure without an
automatic rollback.

If using an independently published image, authenticate the VM to its registry,
set `SALON_API_IMAGE` to the reviewed image digest, pull it, and apply migrations from
that exact image before calling `bash scripts/gcp-vm-deploy.sh --pull`. Save the digest
and set it again for later manual Compose commands. To restore an earlier image,
set its digest and rerun with `--pull` only after checking database compatibility.

For an alternate runtime env file, set `COMPOSE_ENV_FILE` before calling the script.
It uses that file for both Compose interpolation and container environment settings.
For direct Compose commands, also pass `--env-file "$COMPOSE_ENV_FILE"`.

## Cloud Run

For Cloud Run, deploy the same build context and configure all runtime environment
variables in Cloud Run. Keep the container port aligned with `PORT`.
Cloud Run needs a separately scheduled notification worker or equivalent outbox drainer;
the API process alone does not poll the outbox.
