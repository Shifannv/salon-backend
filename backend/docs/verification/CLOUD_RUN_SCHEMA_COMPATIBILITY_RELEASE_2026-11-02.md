# Supervised schema compatibility release — 2 November 2026

Production SQL 0053–0055 is applied and verified. The serving API is still
6fefff4, so the ordinary migration-source guard correctly refused newer main.
The reviewed receipt `backend/deployments/schema-0053-0055-20261101.json`
connects the completed schema execution to this first API compatibility release.

The receipt admits exactly six files (three SQL sidecars and their Alembic
wrappers), whose hashes must match immutable reviewed source 4208c76 and the
selected commit. The serving baseline must remain the exact 6fefff4 revision,
image and repository. Target project/service/database and hashed Gate A/production
execution evidence are checked. Any other migration, changed SQL, changed wrapper,
changed evidence, or different baseline fails closed. No database access or
migration runs in GitHub Actions. No migration history is rewritten.

This compatibility path can only create and verify a zero-traffic candidate.
The deployment records `requires_supervised_promotion=true`; automatic promotion
explicitly rejects it. The run stops with PASS_AWAITING_EXPLICIT_TRAFFIC_APPROVAL.
The owner must separately approve that tested candidate before traffic changes.

After that candidate is promoted, its proven Git SHA becomes the serving baseline.
Future ordinary owner PR merges to main, with successful CI and no migration
differences, follow the existing automatic candidate/health/promotion/rollback path.
Future migrations still require their own approval; this receipt cannot authorize
0056 or edits to any reviewed migration. Direct main pushes, other actors, feature
branches, PR events, stale main, failed CI and false/missing AUTO_DEPLOY_ENABLED
remain blocked by the existing admission guards.

The sole activation switch remains the production environment variable
AUTO_DEPLOY_ENABLED, exactly true. Its existing value is not changed by this
implementation. No IAM/WIF, service-account, repository setting, runtime secret,
DNS, scaling, billing, worker or legacy-hostname changes are introduced.
GitHub Free private branch protection is not enforced; owner PR review is required.

Both CI image source and registry image identity remain SHA/digest-bound. Existing
non-cancelling production concurrency, latest-main checks, image-only deployment,
readiness/version/OpenAPI checks, runtime preservation and rollback remain intact.
No image is rebuilt during rollout. The candidate is built and tested by the same
workflow run that deploys it through existing OIDC federation.

## Free-tier artifact storage correction

CI initially failed after tests because GitHub refused artifact creation at its
storage quota. Inventory found 195 backend artifacts totaling about 20.48 GB,
including 57 CI image archives totaling about 20.35 GB. The owner approved
preserving the latest tested main image locally before deleting these GitHub
image copies, while retaining the 138 other artifacts and all cloud rollback
images/backups. Actual cleanup results must be recorded separately.

Only the automatic main release now requests an image/provenance archive from
reusable CI. PR/feature/standalone CI still builds and smoke-tests the image,
but does not publish unused deployment bundles. Deployment bundles have one-day
retention and compression; the exact consumed artifact ID, source and digest
are still mandatory. Failure to upload that image still blocks deployment.

Diagnostic JUnit/candidate receipt uploads are best-effort: failing tests or
health checks still fail, while an evidence-upload quota error does not change
their result. Job logs/summaries remain available.

The owner separately approved the cleanup job's contents:read/actions:write
permissions. It has no OIDC or cloud credentials. After a successful release,
it verifies artifact ID, image name, run ID and source SHA before deleting only
that run's consumed image archive. The GitHub token has repository Actions-write
authority; the code and job conditions restrict its use, not the platform token
scope itself. Failure reports a warning; no broader cleanup is attempted.
Production deployment retains its existing read/OIDC permissions. GitHub storage
accounting may take 6–12 hours to reflect deletion; no billing upgrade is used.
