# Cloud Run automatic-release gate fix — 1 November 2026

Status: correction verified locally; ready for a reviewed pull request. Production
environment variable `AUTO_DEPLOY_ENABLED` was read through the GitHub API and is
exactly `true`. This work did not change that variable or any secret.

## Proven skipped-release root cause

Automatic run `41277297736` attempt 2 was an owner push to `main` for commit
`6fefff404b148af4798105228418d96f03ad8e4c`. Both CI jobs and the gate job passed,
but `release` was skipped. The gate job log records:

```text
Skip output 'enabled' since it may contain secret.
```

The deployed workflow injected both `vars.AUTO_DEPLOY_ENABLED` and
`secrets.PRODUCTION_AUTO_DEPLOY_ENABLED` at job scope. GitHub registered the secret
for masking, then suppressed the gate's `enabled` output as potentially secret.
Consequently `needs.gate.outputs.enabled == 'true'` could not pass. This was an
output-propagation defect, not a CI, Cloud Run, actor-ID, WIF or application-health
failure. GitHub's blank secret-edit field does not reveal the stored secret value.

## Correction

`AUTO_DEPLOY_ENABLED` is the only deployment switch. It is read as
`${{ vars.AUTO_DEPLOY_ENABLED }}` only in the production-environment Python steps and
accepts exactly lowercase `true`. Missing, empty, inaccessible or nonexact values
fail closed. The obsolete `PRODUCTION_AUTO_DEPLOY_ENABLED` secret and similarly named
repository variable are neither read nor modified.

Removing the secret reference also prevents GitHub from classifying the nonsecret
gate output as derived from that secret. The release job still requires the exact
`enabled == 'true'` output plus successful CI, `push`, `refs/heads/main` and owner
actor ID `172572480`.

The Python admission guard additionally verifies:

- exact repository `Shifannv/salon-backend` and production environment;
- current SHA is still the latest remote `main` SHA;
- checked-out clean source and supplied commit are identical;
- the commit is the exact result of a merged PR into this repository's `main`;
- a rerun uses the original approved actor;
- target project, region, service and Artifact Registry repository are exact;
- the tested CI image artifact belongs to the same SHA/run/attempt;
- migration sources have no unreviewed difference from the proven serving baseline.

Feature-branch pushes and pull-request events never start this workflow. Direct
pushes to `main` fail merged-PR admission. Workflow-level concurrency
`production-cloud-run` uses `cancel-in-progress: false`; a stale queued SHA is refused
before cloud authentication, while an active rollout completes verification or
rollback.

## Deployment safety retained

The exact CI image is loaded and pushed without rebuilding, then deployed by immutable
digest as a zero-traffic candidate. Runtime settings and Secret Manager references are
preserved. Candidate checks cover Ready, `/health/ready`, exact `/version` commit,
process/database/Redis health, docs and OpenAPI compatibility. Promotion is
traffic-only and etag-protected. Both production hostnames are checked after promotion;
failure restores the recorded previous traffic map. No automatic migration, Alembic
stamp or blind `upgrade head` exists.

The supervised first release completed successfully before this correction was
published. Production serves revision `salon-api-production-ci-6fefff4-20261101` at
100%, with immutable image digest
`sha256:30846cbc3328574281f7c5bf3b9cf714386494ffb9138f994465786d1c58475a`.
Both hostnames passed readiness, version identity, database and Redis checks. Revision
`salon-api-production-subpct-20261028` remains Ready for rollback. See
`CLOUD_RUN_RELEASE_PREFLIGHT_2026-11-01.md`.

## Verification scope

Regression coverage proves false/missing/nonexact activation blocks with an explicit
reason; exact `true` plus an ordinary owner-merged latest-main SHA is eligible; every
value of the obsolete secret leaves the decision unchanged; feature, PR,
workflow-dispatch, wrong-repository and wrong-actor contexts fail; direct or mismatched
PR commits fail; stale releases skip before cloud authentication; and immutable-image,
candidate, post-promotion and rollback guards remain enforced.

The private GitHub Free limitation remains: branch protection and rulesets are visible
but not enforced by the plan. Owner review remains necessary. Keep “Require deployments
to succeed before merging” off because deployment follows merge. No IAM/WIF, GitHub
setting, secret, environment variable, database, DNS or Cloud Run configuration was
changed by this gate correction.
