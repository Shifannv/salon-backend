# Gotchas

- Shell is Git Bash on Windows. Run backend commands from `backend/`. A `cd` persists between calls, so prefer absolute paths.
- Cached `.pyc` files show Python 3.14 locally; CI and the Docker image use 3.12.
- `SET LOCAL request.jwt.claims` must run on the same session as the work (`get_authenticated_session` in `backend/app/api/deps.py`), or audit triggers stamp no actor.
- Cache hits on salon detail, services, staff and QR must revalidate publication in Postgres. A cache entry is never authorization.
- `backend/migrations/versions/` holds Alembic `.py` revisions only. Their SQL sidecars (and the 001 baseline) live in `backend/migrations/sql/`; reports and evidence live in `backend/migrations/reviews/` (excluded from the Docker image). Revision files resolve sidecars via `parents[1] / "sql"`.
- The Mumbai investigation runners live in `backend/scripts/migrations/mumbai/` (see its README; not app code, never run the DB-touching ones without approval). `supabase-schema-backup/` at the repo root is local-only and untracked. Evidence JSON keeps historical pre-restructure paths on purpose; details in `backend/docs/migrations/CLEANUP_PLAN.md`.
- Plain `pytest` can fail at collection with `No module named 'psycopg2'` when the local `.env` has a non-asyncpg `DATABASE_URL`. `psycopg2` is not a dependency; run with `ENVIRONMENT=local DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/salon_platform` as process env (never read `.env`).
- Never `git stash -u` here: `core.autocrlf` rewrites untracked LF files to CRLF on pop and breaks the SHA-256 evidence seals. Compare against `git archive HEAD` extracted to a scratch dir instead.
