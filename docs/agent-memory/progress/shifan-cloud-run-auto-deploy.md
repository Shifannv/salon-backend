# Progress: shifan-cloud-run-auto-deploy

## Goal
Prepare owner-main-push automatic Cloud Run releases after green CI with candidate verification and rollback.

## Status
ready for PR

## Done
- Isolated branch from reviewed main e068101; original user changes preserved.
- Added automatic main-push workflow reusing full CI with pinned actions and existing production environment/concurrency.
- Existing manual candidate approval mode remains separate; automatic mode rejects bootstrap, migrations, stale main and contract differences.
- Automatic baseline comes from currently served immutable Git-labelled image; no guessed legacy SHA.
- Traffic-only v2 patch uses etag and preserves tags; reads only the named service, requiring no broader regional role.
- Public health fails fast and triggers rollback; concurrent external edits are not overwritten.
- Prepared exact additional WIF push/workflow pair with unchanged numeric IDs, actor, main ref, environment and scoped grants.
- Full suite:2002 passed,36 skipped; focused guards81 passed. Independent follow-up review found no outstanding blockers. Docker build/non-root/custom-port8099 health, actionlint, shell syntax, Compose and pip check passed.

## In progress
- Commit/PR delivery and GitHub CI observation.

## Next steps
1. Review/merge this branch with green CI; see backend/docs/CLOUD_RUN_AUTO_DEPLOY.md.
2. Obtain approval for exact backend/deployments/github-auto-condition.cel before updating existing WIF provider.
3. Resolve separately approved initial Git-proven release, schema and client contract compatibility; no automatic bootstrap bypass.
4. Enable AUTO_DEPLOY_ENABLED only after prerequisites; eligible owner main pushes then authorize automatic promotion.

## Decisions
- 2026-10-29: New owner request supersedes per-release manual traffic confirmation for the separately activated automatic workflow, not database migration approval.
- 2026-10-29: Keep automation disabled pending trust approval and current release prerequisites; no new IAM roles, infrastructure or runtime changes.

## Files touched
- .github/workflows/cloud-run-auto.yml and backend.yml; .gitignore.
- backend/scripts/cloud_run_auto.py and cloud_run_candidate.py; tests/unit/test_cloud_run_auto.py.
- backend/deployments/github-auto-condition.cel; backend/docs/CLOUD_RUN_AUTO_DEPLOY.md and related release documentation.
- This branch progress record and SESSIONS.md.

## Blockers and open questions
- Existing WIF allows manual dispatch/exact manual workflow only; an additional paired push/auto-workflow trust condition needs approval under the user's earlier IAM rule.
- Current serving hybrid provenance, migration and contract gates remain; no production or database changes performed.
- Automation cannot guarantee rollback if the runner/API is unavailable; retained receipt includes exact operator rollback command.

## Review findings
- [fixed] Generated receipt dirtied promotion checkout; narrow root ignore plus real-Git regression added.
- [fixed] Service-scoped IAM may not cover location operation polling; poll only approved named service instead.
- [fixed] Sequential failed health probes delayed rollback; stop at first failure.

## Session log
- 2026-10-29: implemented and validated automatic release preparation; IAM/activation/production remain unchanged pending prerequisites.
