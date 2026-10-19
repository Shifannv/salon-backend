# salon-backend

Shared FastAPI backend for a salon booking platform. Four clients (customer app, owner app, admin website, walk-in QR website, all in separate repos) call this one `/v1` API.
Stack: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 async + asyncpg, Supabase Postgres/Auth, Alembic, Redis, R2, FCM/Expo, Docker Compose on a GCP VM.

`AGENTS.md` is binding and holds the full rules. Read `docs/README.md` first for project docs; `backend/docs/` for architecture detail.

## Layer map

```
api -> application -> domain
infrastructure -> application/domain ports
```

- `backend/app/domain/`: pure Python, no framework imports.
- `backend/app/application/`: use cases (authorization here), ports.
- `backend/app/infrastructure/`: DB, Supabase, R2, push, payments, cache, email, workers.
- `backend/app/api/`: routers, schemas, `deps.py` auth and wiring.

## Key rules

1. Schema changes only through reviewed Alembic migrations. Never run them at container startup.
2. Create bookings only via Postgres `create_booking()`; get availability only from `get_available_slots()`. No direct inserts into `bookings`/`booking_services`, no slot math in Python.
3. Role comes from `profiles` in the DB, never from JWT claims. Super-admin needs `aal2`.
4. Ownership and authorization checks live in use cases, not routers or repositories.
5. Soft delete via `is_active`. Hard delete only for verified account erasure.
6. Never expose raw Postgres errors, SQL or constraint names over HTTP.
7. Secrets never go in Git, logs, docs or frontend env. Never read `.env` files.
8. Every endpoint has an explicit `response_model` and status code.
9. One branch = one PR = one coherent change. Never commit to `main` directly.

## Commands (run from `backend/`)

- Lint: `python -m ruff check app tests migrations`
- Test: `python -m pytest -q`
- Run: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Migrate (explicit, local DB only): `alembic upgrade head`
- More: `docs/agent-memory/shared/commands.md`

## Session protocol

Run `/start` first and `/wrap` last. `/checkpoint` saves mid-session. Memory lives in `docs/agent-memory/` (per-branch `progress/`, durable `shared/`, index `SESSIONS.md`). Read the `agent-memory` skill before editing it.

## Skills (`.claude/skills/`)

- `senior-backend-engineer`: **read first in every new chat**, and again on any error, bug, review, refactor or cleanup. Strict working standard.
- `karpathy-guidelines`: always apply when writing or reviewing code.
- `agent-memory`: when reading or writing docs/agent-memory.
- `fastapi-endpoint`: adding or changing an endpoint.
- `auth-and-roles`: anything touching JWT, roles, MFA or ownership.
- `alembic-migration`: any schema change.
- `booking-and-payments`: booking, availability, payment or webhook work.
- `pytest-testing`: writing or fixing tests.
- `workers-and-deploy`: workers, Compose, CI or deploy.
- `supabase`: Supabase queries, RLS, storage, auth integration.
- `supabase-postgres-best-practices`: Postgres schema design, indexing, query patterns.
- `interview`: when requirements are unclear or a new feature needs scoping before planning.
- `mcp-builder`: building or modifying MCP servers (`.mcp.json` is in this project).
- `ste`: writing technical documentation, comments, or explanations that need clarity.
- `webapp-testing`: testing API endpoints via HTTP/browser, or writing Playwright tests.

### Founder skills (feature building and planning)

Whenever building a new feature or planning anything new, apply the founder skills before writing code or a plan. Technical rules above still win on any conflict.

- `founder-board`: always first on a new feature idea (verdict: fund, conditions, pass).
- `founder-competitors`: what rivals offer and the gap we can own.
- `founder-consumer`: would salon customers/owners actually use it.
- `founder-offer` and `founder-pricing`: what to include and what to charge (plans, fees, commissions).
- `founder-cfo`: unit economics and break-even of the feature.
- `founder-marketing`, `founder-brand`, `founder-launch`: positioning, naming and rollout.
- `founder-ops`: how it runs day to day (support, staffing, risk).
- `founder-plan`: compile the above into one plan with a computed verdict.

Skip the ones that clearly don't apply (e.g. a pure refactor or bug fix needs none).

## Agents (`.claude/agents/`)

### Core backend agents
- `code-refactorer`: review and harden code on the branch before commit.
- `refactorer`: behavior-preserving refactor under tests.
- `code-reviewer`: diff review against the key rules.
- `python-reviewer`: Python-specific review (PEP 8, type hints, idioms) — use alongside `code-reviewer` for all Python changes.
- `security-reviewer`: auth, IDOR, leaks, secrets, webhooks.
- `performance-analyst`: queries, indexes, caching, pooling.
- `migration-reviewer`: any new Alembic revision.
- `database-reviewer`: SQL queries, schema design, Postgres/Supabase optimization.
- `test-writer`: add tests to existing code.
- `tdd-guide`: write new features test-first (tests before implementation).
- `debugger`: reproduce and fix a failing behavior.

### Planning and architecture agents
- `architect`: system design, scalability decisions, cross-service architecture.
- `planner`: complex multi-step feature planning before coding starts.
- `code-architect`: design a new feature's file/module structure before writing code.
- `code-explorer`: trace an unfamiliar execution path or map a codebase area.

### Maintenance agents
- `doc-updater`: update architecture docs and codemaps after a feature is complete.

### Meta / situational agents
- `agent-sdk-verifier-py`: verify a Python Agent SDK app after building or modifying it.
- `harness-optimizer`: tune Claude agent config for reliability and cost.
- `loop-operator`: manage and monitor autonomous agent loops.

### Optional / non-backend agents

Files exist in `.claude/agents/` but are built for JS/TS, browser or non-backend work. Use them only when the task really fits; for this Python backend prefer `debugger`, `python-reviewer`, `code-refactorer` and `ruff`.

- `build-error-resolver`: TypeScript-oriented build and type-error fixer (optional).
- `refactor-cleaner`: dead-code cleanup built around JS tools (knip, depcheck, ts-prune) (optional).
- `e2e-runner`: browser end-to-end tests via Vercel Agent Browser or Playwright (optional, mostly for the separate frontends).
- `chief-of-staff`: email/Slack communication triage, not backend work (optional).

Commands: `/start`, `/wrap`, `/checkpoint`, `/review`, `/new-endpoint`, `/new-migration`, `/check`.
