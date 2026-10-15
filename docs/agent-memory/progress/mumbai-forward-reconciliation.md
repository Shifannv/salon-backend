# Progress: thameem/mumbai-forward-reconciliation

## Goal
Implement and verify Mumbai local FastAPI refresh/invalidation for customer and owner before any 0040 application. Keep 0038–0040 unapplied; no commit, grant, stamp, Sydney, production, Cloud Run or DNS change is authorized. Current evidence: [local refresh results](../../../backend/docs/verification/mumbai-local-refresh-results-2026-10-15.md).

## Status
in progress

## Done
- Revisions 0038_cancellation_compatibility, 0039_promotion_search_path, 0040_fastapi_only_access drafted (py plus same-named sql), uncommitted.
- Account-deletion adapter edited to scrub bookings.cancellation_reason_code/text (see backend/docs/migrations/MUMBAI_FORWARD_RECONCILIATION.md).
- Unit test backend/tests/unit/test_mumbai_forward_reconciliation.py added; docs updated.
- 2026-10-15: migrations folder restructured (versions/ .py only, sql/ sidecars, reviews/ evidence); revision IDs, down_revision and heads unchanged (single head 0040). Evidence re-sealed by script; SQL content hashes unchanged. Nothing executed against any database.

## In progress
- Earlier Git-uncommitted entries are historical. The owner updated/committed and cleaned the shared backend checkout during this session; this agent issued no Git write commands. Preserve that history and unrelated edits.
- Local staging is configured through ignored `.env.mumbai-local`, guarded Mumbai-only launchers and isolated loopback Redis. FastAPI polling/invalidation is implemented in both separate app checkouts; final real-app Playwright run passed all 11 checks, including both availability failure/retry flows; zero Realtime sockets opened. Synthetic business/Auth data and isolated Redis were cleaned, and local API/Expo servers were stopped.
- Ordinary suites pass: backend 902 passed / 62 skipped; customer 46; owner 26. Independent committed-connection concurrency remains blocked by the rollback fixture and immutable audit cleanup constraints. The acceptance gate remains held.

## Next steps
0. Keep migration execution held. Real Mumbai/API/Redis and 11 browser checks now pass, but independent-connection concurrency and remaining lifecycle/outage coverage are not established; see [results](../../../backend/docs/verification/mumbai-local-refresh-results-2026-10-15.md). Do not count blocked checks as acceptance.
1. Backend tests/lint and selected customer/owner suites are recorded in the local results report. Retain the stated owner TypeScript and pre-existing customer lint failures.
2. Run migration-reviewer on 0038-0040.
3. Historical investigation tools now live together in `backend/scripts/migrations/mumbai/`; ROOT/sibling imports and all six migration source hashes were checked. Do not replay those historical runners for new staging setup: they read normal `.env`.
4. Keep changes uncommitted under the current instruction. Do not apply 0040 before both apps pass staging refresh. The current user instruction authorizes only isolated synthetic Mumbai staging setup/tests and cleanup; it does not authorize migration execution.

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
- Real Mumbai midnight booking exposed UTC/session-date filtering in booking lists; fixed bounds to each salon's timezone and verified both inclusion on the local day and exclusion on the previous day.
- The first customer status-polling change created a detail refresh loop; successful detail now stays stable during background refresh, with error/visibility guards retained and a regression test added.
- Existing owner TypeScript failures (16 schema-test diagnostics) and customer date/time screen lint (same 16 errors / 4 warnings as HEAD) remain separate from passing targeted checks.

## Session log
- 2026-10-15: implemented API polling, mutation/cross-cache invalidation and slot failure recovery; verified real Mumbai JWT/API/Redis plus local browser flows with rollback-only business fixtures and verified synthetic Auth cleanup. Final expanded UI/cleanup results are recorded in the linked results report; no migration/grant/stamp executed.
- 2026-10-15: revalidated all 16 customer/owner inventory hashes and reread subscription/polling/lifecycle hooks. Updated audit, both safe designs and explicit pending staging gate. No frontend/database/migration changes; staging results remain pending.
- 2026-10-15: session started
- 2026-10-15: migration folder cleanup, evidence re-seal and test baseline comparison; root runners and tracked supabase-schema-backup/ await approval (plans only)
