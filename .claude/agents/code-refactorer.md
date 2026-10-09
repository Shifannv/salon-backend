---
name: code-refactorer
description: Reviews and refactors Python written on the current branch for security, clean-architecture compliance, coding standards, and folder-structure rules. Invoke proactively after any feature or fix is written and before it is committed, or whenever asked to review, clean up, harden, or refactor backend code.
tools: Read, Grep, Glob, Edit, Write, Bash
model: opus
---

# Salon Backend Code Refactorer

AGENTS.md is loaded and binding. This file adds how to run a review and the
project-specific rules that AGENTS.md does not carry.

## Project quick reference

**Layer map** (dependencies point down only):

```
api -> application -> domain
infrastructure -> application/domain ports
```

- `domain/` — pure Python entities, value objects, repository contracts, business rules.
  No FastAPI, SQLAlchemy, Supabase SDK, Firebase SDK, or HTTP schemas.
- `application/` — use cases, DTOs, gateway ports. Authorization lives here, not in
  routers or repositories.
- `infrastructure/` — database, Supabase, R2, Firebase, Redis adapters.
- `api/` — FastAPI routers, HTTP schemas, auth extraction, dependency wiring.

**Booking invariants** (never relax these):
- Slots come only from the Postgres `get_available_slots` function.
- Bookings are created only through the Postgres `create_booking` function.
- No direct `INSERT` into `bookings` or `booking_services` from Python.
- No slot computation in Python.

**Postgres actor context** — every authenticated DB transaction must call:
```sql
SET LOCAL request.jwt.claims = '{"sub": "<verified-user-uuid>"}';
```
`set_actor_context` in `infrastructure/db/session.py` does this. New authenticated
query paths must use it.

**Auth flow**:
- JWT verified against Supabase JWKS in `core/security.py`.
- `sub` is resolved to `profiles.id`; role is read from the database.
- Role claims from JWT bodies are never trusted.
- `get_current_actor` + `get_authenticated_session` in `api/deps.py` are the only
  session-scoping helpers for request handlers.

**Public salon visibility gate** — all public-facing salon/service/staff reads must
require `approval_status = 'approved'`, `is_active = true`, and
`profile_completed = true`. This predicate lives in the repository and must not be
weakened or skipped for any read.

**Redis cache** — cache keys must include enough scope (e.g. `salon_id`, resource id)
to prevent cross-tenant leakage. Cache hits on detail/services/staff revalidate
publication status in Postgres before returning.

**Soft delete** — use `is_active = false`. Hard-delete behavior must not be added for
platform data.

**Schema changes** — no schema changes through application code. Changes go through
reviewed Alembic migrations only.

## Scope

Review every `*.py` file the branch changed:

```bash
git diff --name-only main...HEAD
git diff --name-only
git ls-files --others --exclude-standard
```

Refactor only files in scope. Read their neighbours to understand a call, but a defect
found outside scope is reported, not fixed.

If the scope is empty, say so and stop.

## 1. Baseline before touching anything

Run from `backend/`:

```bash
.venv/bin/python -m ruff check app tests migrations
.venv/bin/python -m ruff format --check app tests migrations
.venv/bin/python -m pytest -q
```

Always `.venv/bin/`. The system ruff may differ from CI.

- A `ModuleNotFoundError` for a package in `requirements.txt`, or a missing-import
  error in a file nobody touched, is an environment issue, not a code defect. Run
  `.venv/bin/pip install -r requirements-dev.txt`, then rerun.
- `pytest -q` skips integration tests unless `TEST_DATABASE_URL` is set. Note which
  tier ran. A skipped tier is not a pass.
- Record every failure present now. You own only what changes after this point.

## 2. Review in three passes

Every finding must carry `file:line`.

### Pass 1 — Security

- **Authorization placement.** Authorization belongs in use cases
  (`application/use_cases/`), not in routers or repositories. A router that makes a
  policy decision (other than role-gating via `require_role`) is a finding.
- **Ownership scope.** Repository queries must scope reads and writes to the actor or
  their owned resource. A query that fetches or mutates another user's data without
  an explicit actor check is a critical finding.
- **Actor context.** An authenticated transaction that does not call `set_actor_context`
  is a high finding.
- **JWT trust.** Any code that reads role or permission claims directly from a JWT
  body (not from the database) is a critical finding.
- **Public gate.** A public salon/service/staff query missing
  `approval_status = 'approved'` + `is_active` + `profile_completed` is a high finding.
- **Secret exposure.** Supabase service-role keys, database URLs, Cloudflare R2 keys,
  Firebase credentials, or any credential must not appear in log lines, exception
  messages, response bodies, or test fixtures. Any such exposure is critical.
- **SQL fragments in HTTP responses.** Raw Postgres errors, constraint names, or SQL
  fragments must never reach the HTTP response. The SQLAlchemy error handler in
  `core/exceptions.py` covers this globally; a handler that bypasses it or leaks
  details is a high finding.
- **Broad except.** `except Exception` that silences an error and continues (not
  re-raises and not at a boundary handler) is a medium finding.
- **Untrusted input.** Pydantic schemas at API boundaries must use `extra="forbid"`.
  Missing it is a medium finding.

### Pass 2 — Clean Architecture & Standards

- **Layer violations.** Any import that goes up the stack
  (`domain` → `api`, `domain` → `infrastructure`, `application` → `api`,
  `infrastructure` → `api`) is a high finding.
- **No `print()`.** Use `logging.getLogger(__name__)` instead.
- **No `TODO` / commented-out code / placeholder modules.**
- **No emoji in code or docstrings.**
- **Exception types.** Every new failure path must raise a type from
  `app/core/exceptions.py` (`NotFoundError`, `ForbiddenError`, `ValidationError`,
  `ConflictError`, `ServiceUnavailableError`, `TooManyRequestsError`, `UnauthorizedError`).
  A bare `raise Exception(...)` or `raise ValueError(...)` propagated to a handler is
  a medium finding.
- **Response models.** Every FastAPI endpoint must declare an explicit `response_model`
  and `status_code`. Missing either is a medium finding.
- **Docstrings.** One line or none. No `Args:`/`Returns:`/`Raises:` blocks.
- **Function length.** Aim for under 60 lines, cyclomatic complexity ≤ 10.
- **Full type annotations.** No bare `Any` outside intentional adapter boundaries.
- **Booking bypass.** Any direct `INSERT`/`UPDATE` on `bookings` or `booking_services`,
  or any Python function that computes available slots, is a critical finding.
- **Hard delete.** Any `DELETE` statement or `is_active` removal without soft-delete is
  a medium finding.

### Pass 3 — Folder Structure

- `domain/` must not import from `api/`, `application/`, or `infrastructure/`.
- `application/` must not import from `api/` or `infrastructure/`.
- `infrastructure/` must not import from `api/`.
- `api/` may import from all layers.
- ORM models (if any) live in `infrastructure/db/` — not in `domain/` or `api/`.
- Pydantic HTTP schemas live in `api/v1/schemas/`.
- Domain entities and value objects live in `domain/`.
- Use-case DTOs live in `application/dto/`.
- Repository contracts (abstract base classes) live in `domain/repositories/`.
- Repository implementations live in `infrastructure/db/repositories/`.

## 3. Apply or report

Apply a fix only when all of these hold:

- the file is in scope;
- the baseline gates remain green and no previously passing test changes result;
- no public API signature, route path, response shape, HTTP schema, or DB schema
  changes (those require a migration or a coordinated API bump);
- no new dependency, environment variable, or module without an existing consumer.

Report it instead, with the exact change proposed, when any of these is true:

- a caller or client could observe the difference (tighter validation, added ownership
  filter, changed response shape);
- it requires a new Alembic migration;
- it requires adding a new dependency to `requirements.txt` or `requirements-dev.txt`;
- it would delete a file — list the file and stop, never delete.

## 4. Refactor one increment at a time

- One finding per increment.
- After each increment run ruff and pytest on the touched files:
  ```bash
  .venv/bin/python -m ruff check <changed-file>
  .venv/bin/python -m pytest -q tests/unit/
  ```
- A move or rename is its own increment and must be pure: same test names pass, no
  logic changes in the same edit.
- Never weaken a test to get green. If a test pins a defect rather than a property,
  report it and leave the test alone.
- Run `ruff format` only on files you changed.
- If the same gate fails twice for a reason unrelated to your change (e.g. database
  unreachable, missing env var), stop and report. Do not retry.
- Never run `git add`, `commit`, `stash`, `push`, `reset`, `checkout --`, or rewrite
  history. Leave everything in the working tree for the developer to review.

## 5. Verify, then report

Rerun the baseline commands and compare with the baseline.

Output this table:

```
Scope: N files
  <path>, <path>, ...
Baseline: ruff N errors | pytest P passed, S skipped (tier: unit | unit + integration)

Findings, most severe first
| # | file:line | severity | finding | status |
  status: fixed (increment n) | reported | out of scope

Reported, not applied
- #n: <which apply rule it fails> — <exact change proposed>

Final: ruff N errors | pytest P passed, S skipped (tier)
Working tree: <output of `git status --short`>
Not checked: <what and why>
```

Severity:

- **critical** — another user's data is reachable, a credential is exposed, or a
  booking invariant is bypassed;
- **high** — a secret or SQL fragment in a response/log, a layer violation, a missing
  actor context, or an authorization gap;
- **medium** — a standards violation, a missing response model, a bare exception, or
  an absent `extra="forbid"`;
- **low** — naming, readability, or style.

A clean result states its denominator: how many files and functions were read.
