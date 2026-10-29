# Progress: shifan-cloud-run-bootstrap

## Goal
Verify the legacy production image without a fabricated Git SHA and keep schema gates intact.

## Status
ready for PR

## Done
- Isolated worktree from canonical main 5903d47; original finance edits untouched.
- Verified registry index/platform relationship, 406 selected image-file hashes,
  and exactly nine base-to-serving overlay changes matching release evidence.
- Added exact revision/digest-bound bootstrap selection and typed confirmation.
- Fixed index/platform digest deployment comparison; kept normal labeled releases.
- Migration SQL/version changes remain blocked; historical review changes also gated.
- Fixed signed webhook fixture LF checkout rules without changing fixture contents.
- Full disposable-PG suite1856passed36skipped;46guard tests; Ruff/pip/actionlint,
  shell/Compose and local backend build/nonroot/custom-port/worker smoke pass.
- Read-only schema checks confirm 0051 finance and several audit/support objects
  missing; category/description columns still exist. No production write/deploy.

## In progress
- Publish focused PR and verify GitHub CI.

## Next steps
1. Review PR and backend/docs/CLOUD_RUN_BOOTSTRAP.md.
2. Follow backend/docs/CLOUD_RUN_SCHEMA_RECONCILIATION.md: separately approve
   backup/credential handling, restored-copy assessment and an exact migration plan.
3. Do not dispatch latest-main release while migration deltas remain unreviewed.
4. Never apply destructive column removal, upgrade head or stamp to bypass history.

## Decisions
- Hybrid image is attested by immutable digests/content, not assigned a fake commit.
- Inspect stopped containers only; no runtime-secret/environment-file extraction.
- No migration allow-list or automatic database execution added.

## Files touched
- .gitattributes, candidate workflow/script/guard tests, bootstrap hash manifest.
- backend/docs/CI_CD.md, CLOUD_RUN_BOOTSTRAP.md, CLOUD_RUN_SCHEMA_RECONCILIATION.md.

## Blockers and open questions
- Source includes 0041–0051 migration deltas; live schema is only partially aligned.
- 0041/0042 remove existing columns, requiring explicit data-retention review.
- Fresh verified shared-database backup and exact migration approval remain required.

## Review findings
- [fixed] Index digest is not the Cloud Run platform digest.
- [fixed] Windows CRLF altered byte-exact signed fixture bodies.
- [fixed] Bootstrap cannot accept a different revision/image or altered file set.
- [open] Deployment remains gated pending separate schema reconciliation.

## Session log
- 2026-10-29: Prepared bootstrap PR; actual image proof and local full suite pass;
  production remains subpct-20261028 at100%, no schema or traffic changes.
