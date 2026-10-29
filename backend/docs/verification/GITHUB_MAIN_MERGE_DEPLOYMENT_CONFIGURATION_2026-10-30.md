# Main-merge Cloud Run configuration — 30 October 2026

**Status: blocked for activation.** Repository implementation/local verification only. No deployment, migration, cloud or GitHub Actions API request, secret access, settings change, commit or push was performed. The sole approved external access was unauthenticated public upload-artifact release/commit metadata. Actual configured flag values are the owner's supplied facts, not newly queried settings.

The two required CI check names remain exactly:

- `Lint and tests`
- `Build and smoke test image`

Do not duplicate branch rules/rulesets. The owner manages GitHub UI settings. Keep **Require deployments to succeed before merging OFF**: deployment follows merge. GitHub Free private-repository protection/rulesets are not enforced on this account; do not claim server-enforced review or recommend making the backend public. Runtime merged-PR admission reduces direct-push risk but cannot protect against someone authorized to rewrite main/workflow code. Owner review remains essential.

**Authoritative switch**

Only environment `production` variable **`AUTO_DEPLOY_ENABLED`**, exactly lowercase string `true`, opens deployment. Current owner-reported value is `false` and was not changed. Repository variable `PRODUCTION_AUTO_DEPLOY_ENABLED=false` is unused/stale; leave it unchanged for separately approved cleanup.

The gate job loads production variables with read-only permissions. If the value is absent/false/nonexact, it performs no external request and outputs enabled=false. Because vars can inherit repository/org values, a candidate true also requires exact production-environment variable readback at runtime. Missing/false/wrong-scope values cannot open the gate; denied readback fails closed. The actual production release job depends on that output and is **skipped**, rather than merely skipping deployment steps. Its future environment-read permission must be validated during the supervised phase; no API access was tested locally.

**Branch behavior**

| Event | Behavior |
| --- | --- |
| Push shifan/any feature | Backend CI only; no production workflow or credentials. |
| Open/update PR | Backend CI only, including existing migration-policy and new workflow/guard regressions; no production credentials. |
| Merge PR to main | Same workflow's reusable CI tests/builds exact resulting SHA. Disabled gate skips release; enabled gate still requires exact merged-PR/main/owner/source/artifact/schema/health evidence. |
| Direct main push | CI may run, but admission requires a merged PR whose merge_commit_sha equals selected main SHA and whose base is this repository/main. |
| New main before queued deployment starts | Workflow-level concurrency (cancel-in-progress:false) ensures the newest push holds the single pending slot; an older commit whose CI finishes later cannot displace a newer pending workflow. The newer commit's guard() re-checks main before mutation; older runs skip. No fallback to an older green commit if the newer tip failed. |
| New main after mutation begins | Active deployment/verification/rollback is not cancelled; next eligible queued main follows. |

Original actor ID172572480, repository, ref, workflow path, production environment, deployment service account and WIF restrictions remain unchanged. A different actor cannot retry the owner's release. Rebase strategies not proven by exact merge_commit_sha fail closed.

**Deployment implementation**

- CI preserves the two check names and current declared dependency/pip/Ruff/shell/full-pytest/PostgreSQL/Compose/Docker checks. New static deployment regressions are part of pytest; this work does not claim a new dependency-vulnerability or third-party security audit was run.
- Docker bakes the reviewed SOURCE_COMMIT into a read-only image file, with OCI source/revision labels. `/version` returns that file-backed commit and API version, with Cache-Control:no-store. A runtime variable cannot override it. Local builds without a release SHA report unknown and cannot pass release identity checks.
- CI smoke-tests the image, then exports image.tar/provenance.json. Reusable outputs identify the exact artifact. Release verifies same repository/SHA/run/attempt, archive digest, config digest and layer identities; loads/retags/pushes that image **without rebuilding**. Registry config/layers/source labels are compared again and Cloud Run receives only an immutable platform digest.
- Artifact authentication is never forwarded to signed storage. Retrying requires **rerun all jobs**: a previous-attempt image is intentionally rejected even if its SHA matches.
- One production-cloud-run **workflow-level** concurrency group, cancel-in-progress:false, serializes the entire workflow from start (not just the release job). This prevents an older commit whose CI finishes later from preempting a newer commit's pending release slot: the ordering is set at workflow-queue time (push order), so a newer main commit is always the one that holds the pending slot. An already-running workflow is never cancelled; newer arrivals queue behind it. Main freshness is re-checked before any mutation; after the registry push begins, source identity is frozen so a newer push cannot interrupt an active rollout/rollback. Timeouts/runner loss can still require operator recovery.
- Candidate checks require Ready/resolved digest, /health/ready body, /version commit/version, process/DB/Redis, docs and strict OpenAPI compatibility. Readiness alone is not schema adoption. The existing migration-difference gate still refuses unapproved schema/code combinations; no migration job, stamp or head upgrade was added.
- The previous revision must have valid source labels and pass readiness/identity/public health before candidate release. Post-promotion checks verify readiness/identity and API/DB/Redis on both api.salones.in and the retained apiv1.mudassirmhd.in. Fail-fast failure triggers etag-protected traffic rollback. Concurrent external changes are not overwritten. Failed rollback reports unknown traffic/operator action; a successful rollback still leaves the workflow failed.
- Receipts include commit, API identity, artifact ID/digest, registry/platform digest, start/endUTC, migration comparison target, smoke results, candidate/previous/rollback revisions and exact rollback command. No secret payload or customer row is uploaded. The target describes unchanged migration source relative to a proven baseline; it is not a fabricated observed Alembic version.
- The old manual candidate workflow is retained as a read-only notice, preventing an alternate production deployment path. Historical scripts remain; initial supervised release/recovery needs its separately approved procedure.

**Node20 warning: scoped action update**

Affected action: upload-artifact at ea165f8d65b6e75b540449e92b4886f43607fa02, whose action.yml declares node20. Selected **actions/upload-artifact v7.0.2**, pinned to **cf430e030ddbb5b0abf93d22962f4752f3646cd9**. The official release links that immutable commit and GitHub shows its verified signature; action.yml at the exact SHA declares node24. No other action's SHA/version was updated. Static pin/input validation passed; the action was not executed through GitHub here.

Evidence: [official release](https://github.com/actions/upload-artifact/releases/tag/v7.0.2), [immutable commit](https://github.com/actions/upload-artifact/commit/cf430e030ddbb5b0abf93d22962f4752f3646cd9), [Node24 action metadata](https://raw.githubusercontent.com/actions/upload-artifact/cf430e030ddbb5b0abf93d22962f4752f3646cd9/action.yml).

**Local verification and limits**

Relevant deployment/image-identity/build-identity unit tests use fake HTTP/commands/archives and injected dependency probes. No Docker image build, database connection, integration suite, cloud command, real artifact exchange, OIDC exchange or live rollout ran. Full Ruff, actionlint for every workflow, YAML parsing/static policy tests, bash syntax and git diff --check are the local verification scope. PyYAML6.0.3 is declared for those YAML tests. Final result: **137 relevant unit tests passed** (3 new queue-ordering regression tests added), including a run with external DNS/network, database ports, cloud/database subprocesses and remote Git operations blocked. Ruff, workflow YAML/static checks, actionlint, shell syntax and git diff --check passed. These are not the earlier2002-test history or live CI results.

Exact changed-file inventory (all local and uncommitted):

```text
.github/workflows/backend.yml
.github/workflows/cloud-run-auto.yml
.github/workflows/cloud-run-candidate.yml
.gitignore
backend/Dockerfile
backend/requirements-dev.txt
backend/app/core/build_info.py
backend/app/api/v1/routes/health.py
backend/app/api/v1/schemas/health.py
backend/scripts/check-container.sh
backend/scripts/cloud_run_auto.py
backend/scripts/cloud_run_candidate.py
backend/scripts/ci_image_bundle.py
backend/tests/unit/test_cloud_run_auto.py
backend/tests/unit/test_release_configuration.py
backend/tests/unit/test_build_identity.py
backend/docs/verification/GITHUB_MAIN_MERGE_DEPLOYMENT_CONFIGURATION_2026-10-30.md
```

**Blockers before enabling**

0051 is not deployed according to the prior saved evidence. Migration-history reconciliation, exact migration scope (including the separate0052 decision), fresh verified backup/restore, old-client compatibility, finance-aware workers/rollback, isolated staging verification and the first supervised Git-proven schema-compatible release remain unapproved/unverified. The legacy hybrid image cannot be assigned a guessed Git SHA. Existing bootstrap/migration/OpenAPI guards deliberately still block it. The Free/private protection limitation, environment-variable readback permissions and real artifact/OIDC handoff also require explicit supervised verification/risk acceptance. Local uncommitted code is not releasable.

**Manual final-enable steps for Shifan — later, not executed**

1. Review this diff/test evidence and separately authorize source commit/push/PR. Use the existing main rule/ruleset, exact two checks above, and PR review. Do not enable deployment merely because this repository work passed local tests.
2. Approve and complete the fresh-backup, exact-schema/history/0051 scope and client compatibility work; decide0052 separately. Complete isolated staging and the first supervised proven-source release with healthy, compatible rollback revision. Do not use auto-deployment to bypass these gates.
3. Review/accept the known Free/private enforcement risk without claiming rules are enforced. Keep deployments-before-merge OFF. Validate owner-only merged-commit admission, production-variable readback and exact CI artifact/OIDC identity through the separately approved supervised process; do not broaden WIF/IAM if a check is denied.
4. Obtain explicit owner authorization to activate. In repository Settings -> Environments -> production -> Environment variables, change **AUTO_DEPLOY_ENABLED only** to `true`. Leave repository PRODUCTION_AUTO_DEPLOY_ENABLED unchanged. No automatic migration policy is implied.
5. Merge a reviewed PR to main; observe both exact CI jobs and the release receipt for that SHA/digest/readiness/identity. Failed CI or a stale queued commit must not deploy. If a retry is needed, rerun all jobs, not only release.
6. To pause future releases, set the same production variable to `false`. Do not cancel an in-flight production mutation/rollback. Inspect retained rollback metadata if health fails. Keep both domains and rollback revision.
