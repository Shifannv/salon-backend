---
name: alembic-migration
description: Use when creating or reviewing a database schema change or Alembic revision. Covers the raw-SQL workflow, single head, RLS, indexes, lock safety, downgrade and erase_profile_references().
---

# Alembic migration

Never auto-run. Never run against anything but a local/throwaway DB. Show the command and let the user run it. Migrations are never applied at container startup.

## Workflow

1. Read the current head: newest file in `backend/migrations/versions/` (numbered `00NN_name.py`, currently up to `0037`). Run `alembic heads` and expect exactly one head.
2. Create `00NN_short_name.py` with `down_revision` = the current head. Write raw SQL via `op.execute(...)`, matching sibling revisions. Do not hand-translate the baseline `001_supabase_schema.sql` into ORM operations.
3. Schema is never changed from application code.
4. Add or update a test in `backend/tests/unit/` (migration text/shape) and, where behavior matters, `backend/tests/integration/` (real PostgreSQL via `MIGRATION_TEST_DB`).
5. Tell the user: `cd backend && alembic upgrade head` against a local DB. Do not run it.

## Checklist

- [ ] Single head, correct `down_revision`
- [ ] Idempotent where siblings are (`IF NOT EXISTS`, `CREATE OR REPLACE`)
- [ ] New table: RLS enabled, policies written, grants reviewed (least privilege)
- [ ] Indexes for hot filters; FKs with an explicit `ON DELETE` choice
- [ ] Soft delete column `is_active` for platform data; no hard-delete behavior
- [ ] Audit triggers attached where neighbours have them
- [ ] New FK to `profiles`: update `erase_profile_references()` (see `0021_account_deletion.py`, `0028_account_erasure_hardening.py`) and the account-erasure classification tests
- [ ] New text/JSON columns holding personal data: add to the erasure classification
- [ ] Backfills are lock-safe: batched, no long `ACCESS EXCLUSIVE` locks, `ADD CONSTRAINT ... NOT VALID` then `VALIDATE`, `CREATE INDEX CONCURRENTLY` where needed (outside the transaction)
- [ ] `downgrade()` implemented, or an explicit "irreversible" note with the reason
- [ ] `create_booking()` / `get_available_slots()` untouched, or changed with SQL tests in `tests/integration/`
- [ ] No raw SQL error text surfaced to HTTP because of the new constraint names; map them in the adapter
- [ ] Nothing wired into container startup

Then run the `migration-reviewer` agent on the result.
