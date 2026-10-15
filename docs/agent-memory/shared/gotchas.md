# Gotchas

- Shell is Git Bash on Windows. Run backend commands from `backend/`. A `cd` persists between calls, so prefer absolute paths.
- Cached `.pyc` files show Python 3.14 locally; CI and the Docker image use 3.12.
- `SET LOCAL request.jwt.claims` must run on the same session as the work (`get_authenticated_session` in `backend/app/api/deps.py`), or audit triggers stamp no actor.
- Cache hits on salon detail, services, staff and QR must revalidate publication in Postgres. A cache entry is never authorization.
- `backend/migrations/versions/` holds Alembic `.py` revisions only. Their SQL sidecars (and the 001 baseline) live in `backend/migrations/sql/`; reports and evidence live in `backend/migrations/reviews/` (excluded from the Docker image). Revision files resolve sidecars via `parents[1] / "sql"`.
- Root-level `migration_mumbai_*.py` runners and `supabase-schema-backup/` are scratch from the Mumbai investigation, not part of the app. Evidence JSON keeps historical pre-restructure paths on purpose.
