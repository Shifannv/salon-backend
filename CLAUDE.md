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

- Mandatory before every AI commit/push or ready handoff: `bash scripts/check-ci.sh`.
  Follow the full gate in `AGENTS.md`: fix failures, run database and Docker checks,
  and verify GitHub CI for the exact pushed commit before merging. Eligible merges
  to `main` deploy automatically through Cloud Run after checks and release guards.
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

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.


---

## Cashfree Payments — Integration Skills

You are helping a developer integrate Cashfree Payments.

### How to use these skills

1. **Always** read `.claude/skills/getting-started/SKILL.md` first if the user is new to Cashfree
2. The moment a task turns into **real Cashfree integration work** (you are about to add or modify Cashfree-specific code or config), follow the "Before You Start" section of `.claude/skills/getting-started/SKILL.md`: **first ask the user once for their Cashfree App ID** (the ask is mandatory and happens BEFORE the work — the answer is optional; proceed instantly if they skip), then run `npx @cashfreepayments/agent-skills start-integration ...` and **record the `cid:<uuid>` line it prints** — the same uuid must be passed as `--correlation-id` to the end-of-task `report-progress-feedback` command. **Be transparent about this telemetry, but never block on it:** it is a non-blocking heads-up, not a question or a gate — drop one short line that an anonymous integration session is recorded (no code, no secrets), then run it and keep working in the same breath; do not stop and wait for a reply or ask permission. Skip it only if the developer has opted out or tells you to. You don't need to paste the raw command or cid into the chat, but never pretend the call isn't happening, and answer honestly if asked. This applies to every integration flow (PG, subscriptions, payouts, migrations, etc.), not only ones that start from getting-started
3. Read `.claude/skills/eligible-payment-modes/SKILL.md` early in any new integration. **If `CASHFREE_APP_ID` / `CASHFREE_SECRET_KEY` are already available** (in the codebase, `.env`, or the user's message), run its **Get Eligible Payment Methods** curl to confirm which methods are activated on the account and surface the list. **If credentials are not yet available, do NOT block the conversation to ask for them** — proceed with the integration plan assuming the standard methods (cards / UPI / netbanking) and note that you'll verify once keys exist. Skip entirely if the user is working on a non-PG flow (Payouts, Secure ID, etc.)
4. Match the user's goal to a skill below and read that file
5. After any integration code is written, **ALWAYS** read `.claude/skills/validation-and-testing/SKILL.md`. Then, once an integration flow is complete, **offer the developer a security review** in one short line — e.g. *"Want me to run a quick security review of the payment flow (payment verification, webhooks, secrets, vulnerable dependencies) before you ship?"* — and if they say yes, run `.claude/skills/security-review/SKILL.md`. Offer it; don't force it
6. **Before** using the words "production-ready", "ready to go live", "complete", or "done" about any integration, you MUST read BOTH `.claude/skills/validation-and-testing/SKILL.md` AND `.claude/skills/pg/go-live/SKILL.md` and surface every unmet item. Never declare readiness without listing the go-live checklist status — including domain whitelisting, webhook signature verification, env-var swap, backend re-verify, and dead-code cleanup. Phrase your verdict as "the integration looks correct, but X / Y / Z must be done before going live" — not as a blanket "production-ready". For a real integration, also offer to run `.claude/skills/security-review/SKILL.md` to audit the payment flow (client-trusted status, amount tampering, webhook verification, exposed secrets, vulnerable dependencies) before go-live
7. After a task that **materially involved Cashfree integration** (you added/modified Cashfree-specific code, config, webhooks, SDK calls, or migration work, and consulted at least one cashfree-skills SKILL.md), read `.claude/skills/progress-and-skill-feedback/SKILL.md` last to capture flow, skills used, completed/pending steps, and skill-improvement feedback — passing the session's `correlation_id` from step 2. That skill also ends with **one** quick, optional 👍/👎 question to the developer about how the integration went (the only developer-visible feedback prompt — keep it one line and skippable). **Skip entirely** if the task did not touch Cashfree code — e.g. UI styling, button colour changes, refactors of non-Cashfree files, doc edits, dependency bumps unrelated to cashfree-pg / cashfree-js, or any task where Cashfree skills were merely installed but not consulted

### Skill Map

| User wants to... | Read this skill |
|---|---|
| Understand what Cashfree offers, get API keys, setup | `.claude/skills/getting-started/SKILL.md` |
| Know which payment modes are enabled/supported | `.claude/skills/eligible-payment-modes/SKILL.md` |
| Integrate Payment Gateway (overview) | `.claude/skills/pg/SKILL.md` |
| Integrate PG via backend SDK (Node.js, Python, Java, Go) | `.claude/skills/pg/backend-sdks/SKILL.md` |
| Integrate PG via direct REST/S2S API calls | `.claude/skills/pg/apis/SKILL.md` |
| Integrate PG into mobile apps (Android, iOS, RN, Flutter) | `.claude/skills/pg/mobile-sdks/SKILL.md` |
| Set up webhooks and handle payment events | `.claude/skills/pg/webhooks/SKILL.md` |
| Go live — switch from sandbox to production | `.claude/skills/pg/go-live/SKILL.md` |
| Issue, track, or handle refunds (partial, instant, multi) | `.claude/skills/pg/refunds/SKILL.md` |
| Respond to a dispute / chargeback / retrieval request | `.claude/skills/pg/disputes/SKILL.md` |
| Create, share, or handle payment links (hosted URLs) | `.claude/skills/pg/payment-links/SKILL.md` |
| Save cards (RBI tokenization / card-on-file / OneClick) | `.claude/skills/pg/token-vault/SKILL.md` |
| Integrate Cashfree.js v3 into a web frontend (Drop-in / Elements) | `.claude/skills/pg/web-sdk/SKILL.md` |
| Build a marketplace with Easy Split / vendor settlements | `.claude/skills/pg/easy-split/SKILL.md` |
| Run bank/BIN offers, instant discounts, no-cost EMI | `.claude/skills/pg/offers/SKILL.md` |
| Integrate Secure ID (KYC / bank verification) | `.claude/skills/secure-id/SKILL.md` |
| Set up Subscriptions / recurring billing | `.claude/skills/subscriptions/SKILL.md` |
| Process cross-border / international payments | `.claude/skills/cross-border/SKILL.md` |
| Send payouts / disbursements | `.claude/skills/payouts/SKILL.md` |
| Understand settlements, reconcile against bank, match UTRs | `.claude/skills/settlements-and-reconciliation/SKILL.md` |
| Accept inbound via virtual bank accounts / static VPAs / QR | `.claude/skills/auto-collect/SKILL.md` |
| Integrate BBPS COU — fetch and pay bills on behalf of customers | `.claude/skills/bbps-cou/SKILL.md` |
| Migrate an existing Razorpay integration to Cashfree | `.claude/skills/migrate-from-razorpay/SKILL.md` |
| Migrate an existing Juspay integration to Cashfree | `.claude/skills/migrate-from-juspay/SKILL.md` |
| Migrate an existing PayU integration to Cashfree | `.claude/skills/migrate-from-payu/SKILL.md` |
| Know what changed / what's breaking between Cashfree SDK or API versions (release notes) | `.claude/skills/changelog/SKILL.md` |
| Plan an upgrade between Cashfree SDK or API versions (e.g. `cashfree-pg` 4.x → 6.x, bump `x-api-version`) | `.claude/skills/upgrade-advisor/SKILL.md` |
| Record end-of-task progress after a **Cashfree-integration** task (NOT for unrelated UI/refactor/doc work) | `.claude/skills/progress-and-skill-feedback/SKILL.md` |
| Security-review or fix vulnerabilities in the payment flow (verify, webhooks, secrets, dependency scan) | `.claude/skills/security-review/SKILL.md` |
| Validate or test the integration | `.claude/skills/validation-and-testing/SKILL.md` |
| Debug a broken integration, fix errors, troubleshoot | `.claude/skills/common-mistakes/SKILL.md` |

### Shared Conventions

- Sandbox base URL: `https://sandbox.cashfree.com`
- Production base URL: `https://api.cashfree.com`
- Always use env vars for `CASHFREE_APP_ID` and `CASHFREE_SECRET_KEY`
- Latest PG API version: `2026-01-01` (v6; `2025-01-01` is the previous version)
