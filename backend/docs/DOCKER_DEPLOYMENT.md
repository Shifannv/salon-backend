# Docker deployment

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

On a supported Ubuntu/Debian VM, install Docker once and then deploy:

```bash
cd backend
bash scripts/gcp-vm-install-docker.sh
cp .env.gcp.example .env
# Fill .env with real server-side values.
docker compose build
docker compose run --rm api alembic upgrade head
bash scripts/gcp-vm-deploy.sh
```

The GitHub Actions deployment builds from `backend/`, pushes to Artifact
Registry, and updates the VM. Runtime secrets belong in `backend/.env` on the VM or in
the hosting platform, never in the image.

## GitHub Actions

CI runs on pushes to `main`, `preview`, and `hafiz`, and on pull requests targeting
`main` or `preview`. It checks Ruff,
pytest, shell syntax, Compose configuration, and the Docker image. The image smoke
check verifies `/health` with `PORT=8080`, non-root execution, worker imports, and
packaged Alembic revisions without contacting production services.

The **Deploy** workflow runs automatically on every push to `main`, including merged
pull requests. Pushes to other branches do not trigger deployment. Manual dispatch
remains available on a reviewed ref. Each deployment calls CI first, then
builds and smoke-tests the release image before publishing it with the full commit SHA.
Both API and worker are deployed by the published digest, not a mutable `latest` tag.
Deployments across branches are serialized because they target the same VM.
The workflow copies only `backend/docker-compose.yml` and
`backend/scripts/gcp-vm-deploy.sh` from that ref to `~/salon-backend` on the VM.
It preserves the VM's `.env` and does not update the rest of its Git checkout.

Required GitHub Actions secrets:

| Secret | Purpose |
| --- | --- |
| `GCP_PROJECT_ID` | Project containing Artifact Registry |
| `GCP_REGION` | Artifact Registry repository location, e.g. `us-central1` or `us`; never a VM zone such as `us-central1-a` |
| `GCP_SA_KEY` | Google service-account JSON for the runner; needs registry write access |
| `GCP_VM_HOST` | SSH hostname or IP address |
| `GCP_VM_USER` | VM login user with Docker access |
| `GCP_VM_SSH_KEY` | Private SSH key for that user |

Create the Artifact Registry Docker repository named `salon-backend` before deploying.
The workflow verifies this repository before building an image. If `GCP_REGION` does
not resolve it, the workflow searches the configured project and uses the location of
the single matching repository. Discovery needs permission to list repositories across
locations. Missing, ambiguous, inaccessible, or nonstandard Docker repositories stop
deployment with an explanation. Both the runner and VM authenticate to the verified
registry hostname.

To find the location, open Google Cloud Console, select the deployment project, then
open **Artifact Registry > Repositories** and check the **Location** for `salon-backend`.
Copy it to GitHub **Settings > Secrets and variables > Actions > GCP_REGION**.
An HTML 404 during `blobs/uploads/` can indicate an invalid registry hostname; check
the repository location rather than using the VM zone.

The VM needs `gcloud`, registry read access, Docker Compose, and a configured
`~/salon-backend/backend/.env`. The workflow currently builds Linux amd64 images, so
use an amd64 VM. Bootstrap Docker once with `gcp-vm-install-docker.sh`, then log in
again after Docker group membership changes.

Review Alembic revisions before merging them into `main`. Every deployment runs a
separate migration step using the exact release image before updating services; a
migration failure stops deployment. Neither container startup nor the VM deploy script
runs migrations. Changes must remain compatible with the old services while migrations
run. Revision `0014_repair_cancel_reason` repairs the nullable column
missing from some databases already recorded at revision `0013`.

Alternatively, apply migrations explicitly on the VM using a reviewed published image:

```bash
cd ~/salon-backend/backend
export SALON_API_IMAGE=REGION-docker.pkg.dev/PROJECT/salon-backend/salon-platform-api@sha256:REVIEWED_DIGEST
docker compose pull api
docker compose run --rm --no-deps api alembic upgrade head
bash scripts/gcp-vm-deploy.sh --pull
```

Do not use a stale VM checkout to run new migrations. Save the deployed image digest
from the workflow summary and export `SALON_API_IMAGE` before later manual Compose
commands; the workflow's environment does not persist in a new SSH session.

The deploy script builds from the local checkout by default (`--build`), or pulls
`SALON_API_IMAGE` with `--pull`. It validates Compose and updates all three services,
waiting up to 120 seconds for readiness. It exits nonzero on failure without an
automatic rollback. To restore an earlier image, export its digest and rerun with
`--pull` only after checking database compatibility.

For an alternate runtime env file, set `COMPOSE_ENV_FILE` before calling the script.
It uses that file for both Compose interpolation and container environment settings.

## Cloud Run

For Cloud Run, deploy the same build context and configure all runtime environment
variables in Cloud Run. Keep the container port aligned with `PORT`.
Cloud Run needs a separately scheduled notification worker or equivalent outbox drainer;
the API process alone does not poll the outbox.
