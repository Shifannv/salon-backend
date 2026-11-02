# CI image transport: existing Artifact Registry

GitHub rejected image-archive uploads even after the approved removal of 57 old
image artifacts (20,350,251,974 bytes). Billing storage accounting can lag deletion.
The latest main run 41397202923 passed lint/tests and Docker smoke checks but could
not deliver its image to the release job. No Cloud Run update occurred in that run.

The automatic workflow now runs tests, reads the production environment's exact
`AUTO_DEPLOY_ENABLED=true` gate, and admits only the owner's exact merged latest
main push. A dedicated image job in this same workflow builds and smoke-tests the
image, then publishes it to the existing `salon-production/api` registry. Its job
output identifies the immutable digest, original tested image config and layers,
repository, commit, workflow run and attempt. The release job verifies these
identities against the registry and deploys that digest without rebuilding it.
It does not upload or download the large GitHub CI image archive.

Both cloud jobs use the existing production environment and approved OIDC/WIF
identity. No trust condition, service-account permission or infrastructure changes
are required. The obsolete consumed-artifact cleanup job is removed from this
workflow, eliminating its Actions write permission. Historical archive tooling is
retained for older/manual workflows. Diagnostic evidence uploads remain best effort;
deployment evidence is also printed and included in the workflow summary.

Standalone Backend CI still runs `Lint and tests` and `Build and smoke test image`
on feature pushes and PRs with no cloud credentials or production deployment.
The automatic workflow reuses the same test job but supplies its own image job,
avoiding a second build inside that workflow. The single production concurrency
group remains non-cancelling; stale main is checked before publishing and again
before creating a revision. Once a revision update begins, verification/rollback
finishes even when main advances. No automatic database migration is introduced.

The first reviewed 0053–0055 schema compatibility release still stops at a verified
zero-traffic candidate and requires separate explicit approval for promotion.
Unreviewed migration differences continue to fail closed. The SQL execution receipt
and its sealed evidence are unchanged.

Local checks: 173 focused release/restore/provenance regressions passed; Ruff,
actionlint, four workflow YAML files, shell syntax, Compose, pip check, credential
pattern scan and whitespace checks passed. The locally built image passed non-root,
custom-port, health, worker-import and packaged-migration checks. A full suite rerun
uses temporary storage outside the repository: restore tests intentionally reject
test archives located inside the repository. GitHub's full PostgreSQL-backed CI and
image jobs must also pass before this release fix is merged.
