# Mumbai migration investigation tools

Historical tooling from the 2026-10-15 Mumbai schema reconciliation (revisions 0038-0040).
They are **not application code**, are excluded from the Docker image (`scripts/` is in
`.dockerignore`), and nothing in `app/`, `tests/` or CI imports them.

Run from the repo root, e.g. `backend/.venv/Scripts/python.exe backend/scripts/migrations/mumbai/<script>`.
All scripts keep flat sibling imports, so they must stay together in this folder.
`ROOT` is the repo root (`parents[4]`).

| Script (`migration_mumbai_*_20261015.py`) | Role | Touches DB or network |
| --- | --- | --- |
| `staging` | Shared helpers: Mumbai config guard, verified TLS, API smoke run. Reads `backend/.env` | Yes |
| `reference` | Local disposable Postgres vs Mumbai catalog diff. Library for `sql_preflight`, `completion_audit` | Yes |
| `review_bundle`, `review_validate`, `revision_runtime_review` | Rebuild and validate the review bundle in `backend/migrations/reviews/` | **No** (safe, offline) |
| `sql_preflight` | `BEGIN`/`ROLLBACK` preflight of 0038-0040 via `psql` | Yes, Mumbai only |
| `execution_preflight` | Schema-only `pg_dump` backup into `supabase-schema-backup/` | Yes, Mumbai only |
| `booking`, `completion_business`, `completion_runner`, `runtime`, `completion_audit`, `forward_validation` | Evidence runs that produced the JSON in `backend/migrations/reviews/` | Yes |

Rules:

- The DB-touching scripts need explicit approval (see `backend/docs/verification/mumbai-execution-hold-2026-10-15.md`). Do not run them to "check" something.
- Evidence under `backend/migrations/reviews/` is sealed by SHA-256. Do not edit it; it records the old repo-root script paths on purpose.
- `supabase-schema-backup/` at the repo root is local-only (git-ignored). Restore it from the external copy if missing; `sql_preflight` and `execution_preflight` read and write it.
- Hardcoded `C:/Program Files/PostgreSQL/18/bin` is a Windows dev-machine assumption.
