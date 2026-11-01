# Main-merge Cloud Run configuration — 30 October 2026

**Status: ready for a reviewed gate-fix pull request.** The first supervised,
Git-proven Cloud Run release completed successfully on 1 November 2026. The current
production variable and the affected Actions run were then inspected read-only. This
source correction does not itself deploy, migrate or change GitHub settings.

The two required CI check names remain exactly:

- `Lint and tests`
- `Build and smoke test image`

Do not duplicate branch rules/rulesets. The owner manages GitHub UI settings. Keep **Require deployments to succeed before merging OFF**: deployment follows merge. GitHub Free private-repository protection/rulesets are not enforced on this account; do not claim server-enforced review or recommend making the backend public. Runtime merged-PR admission reduces direct-push risk but cannot protect against someone authorized to rewrite main/workflow code. Owner review remains essential.

**Authoritative switch**

Only environment `production` variable **`AUTO_DEPLOY_ENABLED`**, exactly lowercase
string `true`, opens deployment. Its current verified value is `true`; this change did
not modify it. The obsolete `PRODUCTION_AUTO_DEPLOY_ENABLED` repository variable and
environment secret are ignored and left unchanged.

Updated 1 November: the production jobs resolve `vars.AUTO_DEPLOY_ENABLED` in each
executing Python step. Missing/false/nonexact values output enabled=false and skip
release. No secondary secret is used. The prior workflow referenced the obsolete
secret at job scope, causing GitHub to suppress the `enabled` job output as potentially
secret and skip `release`. See [the verified fix](CLOUD_RUN_GATE_FIX_2026-11-01.md).

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
- The old manual candidate workflow is retained as a read-only notice, preventing an
  alternate production deployment path. The initial supervised release is complete;
  historical recovery scripts remain available but are not normal release paths.

**Node20 warning: scoped action update**

Affected action: upload-artifact at ea165f8d65b6e75b540449e92b4886f43607fa02, whose action.yml declares node20. Selected **actions/upload-artifact v7.0.2**, pinned to **cf430e030ddbb5b0abf93d22962f4752f3646cd9**. The official release links that immutable commit and GitHub shows its verified signature; action.yml at the exact SHA declares node24. No other action's SHA/version was updated. Static pin/input validation passed; the action was not executed through GitHub here.

Evidence: [official release](https://github.com/actions/upload-artifact/releases/tag/v7.0.2), [immutable commit](https://github.com/actions/upload-artifact/commit/cf430e030ddbb5b0abf93d22962f4752f3646cd9), [Node24 action metadata](https://raw.githubusercontent.com/actions/upload-artifact/cf430e030ddbb5b0abf93d22962f4752f3646cd9/action.yml).

**Current gate-fix verification and limits**

The focused gate/release suite passed 89 tests. The complete unit suite passed 1,825
tests. The complete local pytest collection passed 1,847 and skipped 301 cases that
require a separately configured disposable database. Full backend Ruff passed;
actionlint inspected all four workflows; all four parsed as YAML; and `git diff
--check` passed. GitHub CI must still run its disposable-PostgreSQL and Docker checks
for the exact PR commit. The affected run and production environment were inspected
read-only to establish the live root cause/value; no workflow was dispatched and no
GitHub setting was changed by this correction.

Exact intended gate-fix/release-evidence inventory:

```text
.github/workflows/cloud-run-auto.yml
backend/docs/CI_CD.md
backend/docs/verification/CLOUD_RUN_GATE_FIX_2026-11-01.md
backend/docs/verification/CLOUD_RUN_RELEASE_PREFLIGHT_2026-11-01.md
backend/docs/verification/GITHUB_MAIN_MERGE_DEPLOYMENT_CONFIGURATION_2026-10-30.md
backend/scripts/cloud_run_auto.py
backend/tests/unit/test_cloud_run_auto.py
backend/tests/unit/test_release_configuration.py
```

**Activation evidence and remaining limits**

The live database read-only catalogue reported migration target
`0052_booking_window_30_days`, the reviewed finance objects/guards and matching selected
function bodies. The first supervised release established a Git-labelled, immutable,
healthy serving image and retained Ready rollback revision. Artifact, registry,
candidate, contract, public-hostname and traffic-promotion paths succeeded. WIF trust
was configured/read back, but the first automatic run must still prove the live OIDC
exchange. A denied exchange fails before any candidate or traffic change. These facts
clear the initial-release blockers for the currently serving source; they do not approve
future schema changes. Any migration-source difference still fails closed and requires
its own backup, review, compatibility evidence and explicit approval.

GitHub Free private-repository rules remain non-enforced. Owner review is therefore a
real operational control, not a server guarantee. Keep deployments-before-merge off.
Workers are outside the Cloud Run API rollout and need their own release coverage.

**Owner operation after this fix is merged**

1. Review this focused diff and require `Lint and tests` plus
   `Build and smoke test image` to pass on the pull request.
2. Merge only through a PR into `main` as the approved owner. The resulting push runs
   the same CI for the exact merge SHA, then the corrected release gate.
3. Observe the automatic release receipt: exact SHA, immutable digest, candidate checks,
   both public hostnames and final traffic. Do not cancel an in-flight rollout.
4. Leave `AUTO_DEPLOY_ENABLED=true` for automatic releases. To pause future releases,
   set only that production environment variable to `false`; the obsolete
   `PRODUCTION_AUTO_DEPLOY_ENABLED` settings have no effect.
5. If a retry is required, rerun all jobs so the CI image and release attempt remain
   identical. Never rerun only the release job or deploy a mutable tag.
