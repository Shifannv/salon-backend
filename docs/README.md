# Salon Shared API Knowledge Base

This folder contains the main project knowledge for the shared salon platform backend.

Use this folder as the single place for backend decisions, stack details, database notes,
folder structure, and developer task ownership.

## Documents

| File | Purpose |
| --- | --- |
| [project-overview.md](./project-overview.md) | Shared API goal, clients, scope, and team roles |
| [tech-stack.md](./tech-stack.md) | Backend technologies and how each one is used |
| [features.md](./features.md) | MVP feature list and future feature ideas |
| [folder-structure.md](./folder-structure.md) | Backend-only repository structure |
| [database-plan.md](./database-plan.md) | Supabase schema, relationships, and security notes |
| [git-workflow.md](./git-workflow.md) | Branch, commit, pull request, and sync workflow |

## Repository Decision

This repository is for the shared backend API only.

Frontend apps should live in separate repositories and connect to this backend through
environment-configured API base URLs.

```txt
salon-shared-api/      FastAPI backend
salon-customer-app/    Expo customer app
salon-barber-app/      Expo barber/owner app
salon-admin-portal/    Future web admin portal
salon-walkin-web/      Future walk-in QR web app
```

## Current Rule

```txt
One Jira task = one branch = one pull request
```

## Task Source of Truth

Jira is the source of truth for all task status, ownership, priority, and acceptance criteria.

The task files in this folder should only mirror Jira keys and summaries. Do not add extra task lists here without creating or updating Jira first.

## Frontend Integration

Frontend apps live in separate repositories. Use this guide when connecting a frontend app
to the shared backend API:

[frontend-integration.md](./frontend-integration.md)
