# Salon Shared API Knowledge Base

This folder contains the main project knowledge for the shared salon platform backend.

Use this folder as the single place for backend decisions, stack details, database notes,
folder structure, and developer task ownership.

---

## 1. Core Project Documents

| File | Purpose |
| --- | --- |
| [project-overview.md](./project-overview.md) | Shared API goal, clients, scope, and team roles |
| [tech-stack.md](./tech-stack.md) | Backend technologies and how each one is used |
| [features.md](./features.md) | MVP feature list and future feature ideas |
| [folder-structure.md](./folder-structure.md) | Backend-only repository structure |
| [database-plan.md](./database-plan.md) | Supabase schema, relationships, and security notes |
| [frontend-integration.md](./frontend-integration.md) | Canonical frontend setup, auth, R2 media, QR, reports, API flows, and connection checklist |

---

## 2. Walk-in QR Web System Docs

| File | Purpose |
| --- | --- |
| [web-architecture.md](../backend/docs/walkin/web-architecture.md) | Walk-in QR Web App Next.js architecture |
| [barber-app-changes.md](../backend/docs/walkin/barber-app-changes.md) | Barber App QR Code generator & screen setup |
| [backend-changes.md](../backend/docs/walkin/backend-changes.md) | Backend QR endpoints & DB resolution |

---

## 3. Backend Technical & Integration Docs

| File | Purpose |
| --- | --- |
| [API_AND_INTEGRATION.md.md](../backend/docs/API_AND_INTEGRATION.md.md) | Environment variables, API request/response formats, and frontend connection |
| [ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md) | Layered clean architecture design rules |
| [AUTHORIZATION.md](../backend/docs/AUTHORIZATION.md) | Supabase JWT authentication and role-based authorization |
| [BOOKING_FLOW.md](../backend/docs/BOOKING_FLOW.md) | Booking creation & slot availability rules |
| [RUNBOOK.md](../backend/docs/RUNBOOK.md) | Development runbook, running tests, and troubleshooting |

---

## 4. Repository Decision

This repository is for the shared backend API only.

Frontend apps live in separate repositories and connect to this backend through
environment-configured API base URLs:

```txt
salon-backend/         FastAPI backend (this repo)
salon-customer-app/    Expo customer app
salon-barber-app/      Expo owner/barber app
salon-walkin-web/      Walk-in QR web app (Next.js)
```

---

## 5. Workflow Rules

- **Branch naming**: `one Jira task = one branch = one pull request`
- **Source of truth**: Jira is the source of truth for task status, ownership, priority, and acceptance criteria.
