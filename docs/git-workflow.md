# Git Workflow

## Repository Setup

The project uses GitHub with a fork-based workflow.

Expected setup:

```txt
Original repo: Shifannv/salon-customer-app
Thameem fork: Thameempp/salon-customer-app
```

## Main Branches

```txt
main
dev
feature branches
```

### main

Stable branch.

Use for:

- Tested code
- Demo-ready code
- Release-ready code

Do not directly work on `main`.

### dev

Integration branch.

Use for:

- Combining frontend and backend work
- Testing features together
- Preparing for merge into `main`

### Feature Branches

Use one branch per Jira task.

Examples:

```txt
shifan/SACS-47-frontend-location
thameem/SACS-48-backend-location
```

## One Task Rule

```txt
One Jira task = one branch = one pull request
```

## Daily Workflow

Start from latest branch:

```bash
git checkout dev
git pull origin dev
```

Create task branch:

```bash
git checkout -b thameem/SACS-48-backend-location
```

Work on the task.

Check changes:

```bash
git status
```

Add only task-related files:

```bash
git add customer-app/supabase
git add customer-app/src/services/supabase
git add docs/database-plan.md
```

Commit:

```bash
git commit -m "SACS-48 Add Supabase nearby salon query"
```

Push:

```bash
git push origin thameem/SACS-48-backend-location
```

Open pull request:

```txt
from: Thameempp/salon-customer-app:thameem/SACS-48-backend-location
to: Shifannv/salon-customer-app:dev
```

If there is no `dev` branch, open PR to:

```txt
Shifannv/salon-customer-app:main
```

## Fork Sync Rule

Do not click Sync Fork blindly if the original repo accidentally deleted important files.

Before syncing, check:

- Does original repo have `customer-app`?
- Does original repo have required docs?

If original repo is missing important files, create a restore branch and PR first.

## Pull Request Checklist

Every PR should mention:

- Jira task key
- What changed
- Files/folders changed
- How it was tested
- Any environment variables added
- Any database changes added
