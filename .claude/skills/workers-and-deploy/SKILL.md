---
name: workers-and-deploy
description: Use when changing background workers, Docker Compose, health checks, CI or the GCP VM deploy flow. Lists each service and what it owns, retry rules and deploy ordering.
---

# Workers and deploy

Files: `backend/docker-compose.yml`, `backend/Dockerfile`, `backend/scripts/`, `.github/workflows/backend.yml`, `backend/docs/DOCKER_DEPLOYMENT.md`, `RUNBOOK.md`, `CI_CD.md`.

## Compose services

| Service | Entrypoint | Owns |
|---------|-----------|------|
| api | uvicorn `app.main:app` | HTTP API; binds `0.0.0.0`, reads `PORT` (default 8000) |
| redis | `redis-server --appendonly yes` | cache, rate/idempotency helpers |
| notification-worker | `app.infrastructure.push.outbox_worker` | push notification outbox (FCM/Expo) |
| media-cleanup | `app.infrastructure.media.cleanup_worker` | orphaned R2 media cleanup |
| account-deletion-worker | `app.infrastructure.account_deletion.worker` | durable erasure of Auth identity, profile, media, caches, tokens |
| payment-webhook-worker | `app.infrastructure.payments.webhook_worker` | webhook processing, retry, reconcile |
| email-worker | `app.infrastructure.email.worker` | support/email outbox |

Each worker has a heartbeat healthcheck. Workers refuse to start with incomplete required settings.

## Worker rules

- Idempotent: every job can run twice safely. Claim rows with locks (`FOR UPDATE SKIP LOCKED` style) and record attempts.
- Retries use backoff with a cap; terminal failures are recorded for operators, not retried forever.
- Commit before external calls where a crash must be reconcilable.
- Never log tokens, PII or provider payloads in full.

## Health

`/health` (process), `/health/db`, `/health/redis` in `api/v1/routes/health.py`. Keep Compose and CI checks pointed at `/health`.

## Deploy flow

1. PR: CI runs ruff, `bash -n scripts/*.sh`, pytest with a Postgres 18 service (`MIGRATION_TEST_DB`), then builds the image and smoke tests it (non-root, custom port, Compose config).
2. Push to `main`: tested image packaged as an artifact, then the deploy job SSHes to the GCP VM and runs `scripts/gcp-vm-release.sh`. Superseded releases are rejected.
3. Migrations are a separate, reviewed, explicit step run before code that needs them. Never in the container startup command.
4. Runtime secrets live in `backend/.env` on the VM only (from `.env.gcp.example`). Never commit or print them.
5. Docker build context is `backend/`; image is backend-only.

## Checks

`docker compose --env-file .env.gcp.example -f docker-compose.yml config --quiet`, `bash -n scripts/<name>.sh`, `docker build -t salon-platform-api .` (say so if Docker is unavailable). Do not start containers without being asked.
