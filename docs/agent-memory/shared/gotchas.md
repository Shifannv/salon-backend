# Gotchas

- Shell is Git Bash on Windows. Run backend commands from `backend/`. A `cd` persists between calls, so prefer absolute paths.
- Cached `.pyc` files show Python 3.14 locally; CI and the Docker image use 3.12.
- `SET LOCAL request.jwt.claims` must run on the same session as the work (`get_authenticated_session` in `backend/app/api/deps.py`), or audit triggers stamp no actor.
- Cache hits on salon detail, services, staff and QR must revalidate publication in Postgres. A cache entry is never authorization.
- Migrations `0035` and `0037` also exist as loose `.sql` files in `backend/migrations/`; the `.py` revisions in `versions/` are the Alembic chain.
- Root-level `migration-*` files are scratch artifacts from a Mumbai migration investigation, not part of the app.
