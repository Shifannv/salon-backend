# Git Workflow

This repository is for the shared FastAPI backend only.

Frontend apps live in separate repositories and should not be pulled into this repo unless
the team formally changes to a monorepo.

## Branches

```txt
main
feature branches
```

### main

Stable branch.

Use for:

- Reviewed backend code
- Tested migrations
- Deployment-ready API changes

Do not commit directly to `main` unless explicitly requested by the project owner.

### Feature Branches

Use one branch per Jira task.

Examples:

```txt
thameem/SACS-14-backend-foundation
thameem/SACS-29-salon-listing-api
thameem/SACS-37-booking-create-api
```

## One Task Rule

```txt
One Jira task = one branch = one pull request
```

## Daily Workflow

Start from latest `main`:

```bash
git checkout main
git pull origin main
```

Create a task branch:

```bash
git checkout -b thameem/SACS-29-salon-listing-api
```

Check changes:

```bash
git status
```

Add only task-related files:

```bash
git add backend/app backend/tests backend/docs docs
```

Commit with the Jira key:

```bash
git commit -m "SACS-29 Add salon listing API"
```

Push:

```bash
git push origin thameem/SACS-29-salon-listing-api
```

Open a pull request:

```txt
from: thameem/SACS-29-salon-listing-api
to: main
```

## Pull Request Checklist

Every PR should mention:

- Jira task key
- What changed
- API endpoints added or changed
- Database migrations added or changed
- Authorization checks added or changed
- Files/folders changed
- How it was tested
- Environment variables added or changed

## Backend Verification

Before opening a PR, run from `backend/` when possible:

```bash
./.venv/bin/python -m pytest
./.venv/bin/python -m ruff check app tests migrations
```

If dependencies are missing:

```bash
./.venv/bin/pip install -e ".[dev]"
```

## Deployment Rule

Deploy from `main` only after review and merge.

Frontend apps should consume the deployed backend through their own environment variable:

```txt
EXPO_PUBLIC_API_BASE_URL=https://api.yourdomain.com
```
