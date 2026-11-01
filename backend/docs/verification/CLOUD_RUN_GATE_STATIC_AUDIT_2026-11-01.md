# Cloud Run deployment gate audit — 1 November 2026

Status: local correction verified; activation remains blocked. No diagnostic PR was merged, and no GitHub setting, secret, variable, WIF/IAM, production database or Cloud Run configuration was changed. The owner reports the production variable is currently true; this audit did not change or independently read it. Therefore this audit cannot certify the separate request that the live variable remain false. Pause it manually before any later merge under separate settings authority.

## Verified defect

Commit `9fe7f5777b6453286d1791e34317d280accd1d83` added a second exact-true switch: `PRODUCTION_AUTO_DEPLOY_ENABLED`. It was passed from GitHub secrets into both production jobs. The former gate wrote enabled=false when that secret was absent or not exactly true, even when AUTO_DEPLOY_ENABLED was true. The gate command returned successfully in that case, so a successful gate job did not establish enabled=true. The existing secret's blank edit dialog is not evidence of its value.

New regressions reproduced the defect before the correction (14 failures, 1 pass in the selected tests). This proves the source defect, not the value or failing condition in an unidentified live run. The exact live actor and gate log remain unverified until the affected run can be read. The initial API lookup was rejected by approval review; the owner subsequently approved narrow read-only run metadata/log access. GitHub CLI is unavailable in this session, and connected job-log tools require the run ID.

## One authoritative switch

Production environment variable `AUTO_DEPLOY_ENABLED`, referenced as `${{ vars.AUTO_DEPLOY_ENABLED }}`, accepts only the lowercase string `true`. It is resolved in the activation, admission and deployment steps inside production-environment jobs. An unavailable/empty resolved value, false, whitespace or another spelling blocks the gate. No secret and no repository variable named PRODUCTION_AUTO_DEPLOY_ENABLED is read. Existing GitHub settings are left intact.

GitHub vars can inherit repository/organization values. The desired configuration must define AUTO_DEPLOY_ENABLED only in environment production, with no same-name inherited value. The workflow cannot independently prove the variable's storage scope using vars alone. The previous REST readback required a permission unavailable to the current GITHUB_TOKEN; this correction does not reintroduce it, add a PAT, or invent equivalent scope proof from a secret. Scope collisions remain an activation verification item; an inherited true could otherwise resolve true when the environment variable is absent.

Every gate run prints `Deployment gate: enabled=<true|false>; blocked_by=<condition names|none>`. No switch value or secret payload is printed. Disabled values never authenticate to GCP. An empty or missing gate output does not satisfy the release job's exact-true condition.

## Complete conditions and sources

| Condition | Source and enforcement | Audit result |
|---|---|---|
| Push to main | Workflow `on.push.branches: [main]`; gate event_push/ref_main; release job if | PASS statically; feature and PR regressions pass |
| Backend CI success | release needs both ci and gate; default success condition; reusable test then image jobs | PASS statically; required names remain Lint and tests / Build and smoke test image |
| Authoritative switch | production step env from vars.AUTO_DEPLOY_ENABLED, exact true | PASS locally; live value owner-reported true; actual scope/collisions UNKNOWN |
| Legacy secret/repository variable | PRODUCTION_AUTO_DEPLOY_ENABLED no longer appears in workflow/helper reads | PASS; never read or changed existing GitHub secret |
| Repository | GITHUB_REPOSITORY exactly Shifannv/salon-backend | PASS statically and in negative tests |
| Actor | GITHUB_ACTOR_ID exactly 172572480 in gate, release job if, Python identity and WIF CEL | Preserved; ordinary owner merge tested; actual affected event actor UNKNOWN |
| Retry actor | GITHUB_TRIGGERING_ACTOR must equal original GITHUB_ACTOR | Preserved; different retry actor rejected |
| Latest selected SHA | GitHub main API, GITHUB_SHA, REQUESTED_COMMIT, git HEAD and clean tree | Preserved; stale release skips before auth; full-SHA/clean-source checks remain |
| Merged PR | commit-associated PR must have merged_at, merge_commit_sha equal selected SHA, base main and exact base repository | PASS; direct push/wrong SHA/base/repository refused |
| Production environment | both jobs select production; identity checks exactly one main branch deployment policy | PASS in source; actual current UI policy UNKNOWN |
| Target variables | GCP_PROJECT_ID=saloon-505509; GCP_REGION=asia-south1; GCP_CLOUD_RUN_SERVICE=salon-api-production; GCP_ARTIFACT_REGISTRY_REPOSITORY=salon-production | Preserved; live settings not read |
| WIF identifiers | production GCP_WORKLOAD_IDENTITY_PROVIDER / GCP_DEPLOY_SERVICE_ACCOUNT variables; pinned auth action | Preserved; no federation exchange or IAM inspection performed |
| WIF trust | CEL repository_id 1422493480, owner_id 172572480, repository, actor_id, main ref, production subject; paired push/cloud-run-auto.yml or manual/candidate path/event | Source unchanged; actual provider readback not performed |
| Migration gate | automatic bootstrap forbidden; proven deployed source baseline; zero backend/migrations differences | Preserved; database state not queried; no automatic migration |
| Image provenance | CI artifact ID/digest from same successful run and attempt; source/config/layers verified; load/retag/push without rebuild; deploy immutable platform digest | Preserved; offline tests pass; real handoff not exercised |
| Serialization | workflow-level production-cloud-run, cancel-in-progress false; latest-main checks before mutation and frozen source after mutation starts | Preserved; no concurrency change in this correction |
| Baseline and candidate | single healthy previous revision with proven labels; unchanged runtime; candidate Ready/digest; readiness, version SHA, DB/Redis, docs/OpenAPI and compatibility checks | Preserved; no production requests sent |
| Promotion/rollback | verified candidate receipt, unchanged resource version/etag and settled traffic; both hostnames verified; guarded rollback to previous revision on health failure | Preserved; mocked tests pass; no promotion attempted |

The workflow uses no repository-level deployment switch or environment secret after this correction. GitHub token authentication and Google OIDC credentials remain infrastructure authentication, not additional on/off switches. WIF/IAM restrictions were not relaxed.

## Verification and activation

Local results: 148 targeted release/image/identity tests passed; all 1825 unit tests passed (one existing dependency deprecation warning); backend Ruff passed; actionlint and YAML/static workflow tests passed. Final diff checks passed; credential-pattern scans of all six changed files found zero hits. The full disposable-PostgreSQL integration suite and actual CI/cloud exchanges were not run as part of this static audit. WIF CEL SHA-256 remained `82a5f858a216ce77bb0cf008e598dac0f72524500f4ffe1869b74c5b05fb60f5`.

Ready for local review, not final activation based on migration alone. Before activation, separately verify the actual event actor and production environment settings, resolve schema/history and 0051/0052/client-compatibility decisions, establish a Git-proven healthy serving baseline and rollback revision, and complete the supervised artifact/WIF/candidate/rollback checks. Saved historical readiness documents do not prove current database state. No live database check is authorized in this task.

For live diagnosis, inspect Actions → Cloud Run automatic production → affected run → gate → Read only the authoritative production-environment gate. The old helper prints `Gate conditions not met: production_secret` when the second switch blocks, or actor_id/event_push/ref_main/repository/auto_deploy_enabled for the other checks. The corrected helper prints the explicit enabled/blocked_by line. Only after the gate output is true do admission, migration, provenance and health checks run; they cannot explain a release job that was skipped before starting.

The owner must keep the production switch false while release prerequisites remain open. This task grants no settings-write authority: do not merge the diagnostic PR or this correction while an enabled production switch could trigger an unapproved release. No advice to set two switches true is applicable.
