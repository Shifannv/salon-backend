# Progress: shifan-finance-truncate-final

## Goal
Finish the approved encrypted backup/local rehearsal and protect prepared finance money tables from owner-role TRUNCATE before release.

## Status
ready for PR

## Done
- Verified encrypted logical recovery copy and isolated restore of all 84 exported tables, canonical row hashes, owners, effective ACLs and financial totals.
- Rehearsed 0041?0048 and proposed latest 0051 on fresh isolated clones; skipped adopted 0049/0050, never upgraded/stamped history.
- Latest-main regressions reproduced three owner TRUNCATE failures; added statement triggers without changing service-role denial or erasure updates.
- Independent read-only migration/code review found no blockers.
- Full pytest: 1959 passed, 36 skipped; Ruff and pip check passed.
- Docker build and isolated non-root/custom-port8099 health smoke passed; Compose with empty env input, actionlint and shell syntax passed.
- Latest existing main CI passed; production and legacy API health/db/redis returned 200; production remains subpct-20261028.

## In progress
- Source delivery and CI observation.

## Next steps
1. Review this branch and backend/docs/SCHEMA_REHEARSAL_20261029.md; do not apply SQL based on the report alone.
2. Obtain separate target/hash-bound migration approval including photo/category retention effects, with a fresh verified recovery copy.
3. After schema adoption, review compatibility attestation/gate changes; verify zero-traffic latest-main candidate before separate traffic confirmation.

## Decisions
- 2026-10-29: retain existing service_role TRUNCATE revoke; add owner-facing statement guards because the owner cannot revoke its own table privilege.
- 2026-10-29: keep all production migrations, deployments and traffic unchanged during this authorized local-only rehearsal.

## Files touched
- backend/migrations/sql/0051_owner_finance_cashbook.sql
- backend/tests/integration/test_owner_finance_sql.py
- backend/docs/SCHEMA_REHEARSAL_20261029.md
- backend/docs/CLOUD_RUN_SCHEMA_RECONCILIATION.md
- This progress file and SESSIONS.md.

## Blockers and open questions
- Latest source still differs from production schema; existing candidate migration guard intentionally blocks deployment.
- Offline OpenAPI gate also requires review: no paths/operations removed, but existing fields and the generated avatar upload schema differ; details are in the rehearsal report.
- Full plan drops one populated salon category and soft-retires five active photos in the snapshot; production retention approval is required.
- Recovery is local logical backup, not hosted PITR or off-device recovery.

## Review findings
- [fixed] Owner TRUNCATE bypassed row triggers; three statement triggers reject it before NEW/OLD access.
- [open] Shared-schema adoption and digest-bound release compatibility remain separate reviewed steps.

## Session log
- 2026-10-29: resumed approved local rehearsal against latest reviewed main 848ac73; preserved original worktree and all recovery evidence.
