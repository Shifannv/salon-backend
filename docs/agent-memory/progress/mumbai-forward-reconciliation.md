# Progress: thameem/mumbai-forward-reconciliation

## Goal
Verify compatible customer and owner API refresh behavior before any 0040 application. Audit Realtime subscriptions, SELECT/RLS requirements, invalidation hooks and event-failure fallback; prepare minimal secure Realtime and FastAPI refresh designs. Keep migrations held; no commit, application or stamp is authorized.

## Status
in progress

## Done
- Revisions 0038_cancellation_compatibility, 0039_promotion_search_path, 0040_fastapi_only_access drafted (py plus same-named sql), uncommitted.
- Account-deletion adapter edited to scrub bookings.cancellation_reason_code/text (see backend/docs/migrations/MUMBAI_FORWARD_RECONCILIATION.md).
- Unit test backend/tests/unit/test_mumbai_forward_reconciliation.py added; docs updated.
- 2026-10-15: migrations folder restructured (versions/ .py only, sql/ sidecars, reviews/ evidence); revision IDs, down_revision and heads unchanged (single head 0040). Evidence re-sealed by script; SQL content hashes unchanged. Nothing executed against any database.

## In progress
- Everything is uncommitted on this branch (modified docs/tests/repo plus new migrations).

## Next steps
0. Complete the customer/owner staging refresh gate in [the designs](../../../backend/docs/verification/mumbai-refresh-designs-2026-10-15.md) before proposing migration execution. Existing mocked tests do not pass this gate.
1. Run lint and tests from backend/ (`/check`) on the uncommitted work and record results.
2. Run migration-reviewer on 0038-0040.
3. Decide what to do with root-level migration-mumbai-* scratch files and migration_mumbai_*.py (commit, move under docs, or leave untracked).
4. Keep changes uncommitted under the current instruction. Do not apply 0040 before both apps pass staging refresh. Nothing may be executed against Mumbai without explicit authorization.

## Decisions
- 2026-10-15 revalidation: compatible API refresh verification takes priority. Recommend FastAPI polling/invalidation; private Broadcast with strict per-user authorization is the secure Realtime alternative. Raw business-row grants conflict with unchanged 0040 and do not fix customer availability safely.
- Current checkout starts clean on `shifan`; six 0038-0040 Python/SQL files are already tracked in HEAD. Earlier Git-uncommitted entries below describe historical state. Do not rewrite history to manufacture uncommitted migrations; no commits or migration edits made in this audit. Database non-application remains recorded evidence, not a fresh live query.
- 2026-10-15: no migration, stamp or grant execution against Mumbai, because the reconciliation doc says it is prepared only.

## Files touched
- backend/migrations/sql/0038-0040 (.sql) and backend/migrations/versions/0038-0040 (.py)
- backend/app/infrastructure/db/repositories/account_deletion_repository.py
- backend/docs/migrations/MUMBAI_FORWARD_RECONCILIATION.md, backend/docs/migrations/README.md, backend/docs/ACCOUNT_DELETION.md, docs/database-plan.md, README.md
- backend/migrations/reviews/ (evidence, moved from repo root), backend/scripts/migrations/reseal_layout_evidence.py (new)
- backend/tests/unit/test_mumbai_forward_reconciliation.py, test_payment_flows.py, integration/test_account_deletion_sql.py

## Blockers and open questions
- Mumbai readiness report says head reconciliation, Auth delivery, TLS and deployed verification are still open.
- Wider erasure classification guard misses newer tables (separate release risk).

## Review findings
- none yet

## Session log
- 2026-10-15: revalidated all 16 customer/owner inventory hashes and reread subscription/polling/lifecycle hooks. Updated audit, both safe designs and explicit pending staging gate. No frontend/database/migration changes; staging results remain pending.
- 2026-10-15: session started
- 2026-10-15: migration folder cleanup, evidence re-seal and test baseline comparison; root runners and tracked supabase-schema-backup/ await approval (plans only)
