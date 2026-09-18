# Docker Deployment

The backend Docker image is portable across GCP Compute Engine VM instances and
GCP Cloud Run. Build with `backend/` as the Docker context.

## Local Docker

```bash
cd backend
docker build -t salon-platform-api .
docker run --env-file .env -p 8000:8000 salon-platform-api
```

Open `http://127.0.0.1:8000/health`.

## GCP VM Instance

Use this option when you want a normal Compute Engine VM running Docker Compose.

### 1. Create VM

Recommended starting point:

- OS: Ubuntu LTS
- Machine: e2-small or e2-medium
- Firewall: allow TCP `8000` for direct API access, or only `80/443` if you put
  Nginx/Caddy in front later.

### 2. Install Docker On VM

SSH into the VM, clone the repo, then run:

```bash
cd backend
bash scripts/gcp-vm-install-docker.sh
```

Log out and back in if the script says your user was added to the `docker`
group.

### 3. Configure Env

```bash
cd backend
cp .env.gcp.example .env
nano .env
```

Fill in real Supabase values. Never commit `.env`.

### 4. Deploy Or Update

```bash
cd backend
bash scripts/gcp-vm-deploy.sh
```

Useful commands:

```bash
docker compose ps
docker compose logs -f api
docker compose restart api
docker compose down
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

If the VM has a public IP and firewall allows port `8000`, use:

```bash
curl http://YOUR_VM_EXTERNAL_IP:8000/health
```

### Manual GitHub Actions Deployment

The `.github/workflows/deploy.yml` workflow is manual-only. A push or successful CI run
does not deploy the backend. To deploy the version currently on GitHub:

1. Open the repository's **Actions** tab.
2. Select **Deploy**.
3. Choose **Run workflow**, select the branch to deploy, and confirm.

The workflow builds that branch's current commit, pushes the image to Google Artifact
Registry, and restarts the GCP VM container. Push the intended commit and confirm CI
before starting this workflow.

## GCP Cloud Run

From the `backend/` folder:

```bash
gcloud run deploy salon-platform-api \
  --source . \
  --region YOUR_REGION \
  --allow-unauthenticated
```

Set runtime environment variables in Cloud Run, not in the image. Required
values are listed in `.env.example`.

## Migrations

Do not run Alembic migrations automatically during container startup. Run them
as a separate deploy step after reviewing the target database:

```bash
alembic upgrade head
```
