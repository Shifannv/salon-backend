# Final Cloud Run deployment policy — proposed design and dry-run plan

29 October 2026. **Design only. No workflow/helper/application code was changed, no tests or production requests were run, and nothing was committed, pushed, enabled, migrated or deployed.** Automatic deployment remains disabled. Read with the [0051 readiness report](FINANCE_0051_RELEASE_READINESS_2026-10-29.md).

Frozen source: cached main `d05566ce6f464c8b796d9d03a21e2c10f16859ff`. This design supersedes the earlier ordinary-main-push authorization model. It is not a claim that the merged workflow already satisfies the final policy.

**1. Exact trigger and authorization policy**

| Event | CI | Production behavior |
| --- | --- | --- |
| Any feature push, including shifan | All required checks/build | Never authenticate to GCP or deploy. |
| Any PR, including forks | Lint/tests/security/migration policy/build; no production credentials | Never deploy; no pull_request_target privilege path. |
| Direct main push | CI runs, even if someone bypasses repository controls | Deployment admission rejects it. Workflow-side rejection does not replace server protection. |
| PR merged to protected main | CI runs for the exact resulting main SHA | Eligible only after every required job for that SHA succeeds, protection/merge proof passes and activation/prerequisites are satisfied. |
| Failed/skipped/cancelled/timed-out required job | Preserve evidence | Not eligible. Green unrelated or head-branch CI is insufficient. |
| Older queued eligible commit | CI results retained | Skip before production mutation if a newer main tip exists. |

Keep exact repository/IDs, actor172572480, refs/heads/main, environmentproduction, existing push/auto-workflow pairing, deployment service account and four scoped grants. No Owner/Editor, project-wide Run, Secret Manager, JSON key, new bot actor or new WIF event/path. The OIDC-authenticated job stays in cloud-run-auto.yml on a push event; do not switch it to workflow_run/schedule and silently widen trust.

**Enforced main protection is a hard prerequisite.** Earlier GitHub Free/private evidence said required branch review/rulesets were not enforced. No new server inspection is allowed in this phase. Do not claim main is protected, treat the environment branch filter as protection, or emulate enforcement with a green script. Require an active server-side policy: PR-only changes, required exact CI checks, up-to-date merge validation, blocked force pushes/deletion/direct push, and no administrator/app bypass. Billing/visibility changes are not authorized or requested. If this requirement cannot be enforced under the chosen account configuration, activation remains blocked until the owner resolves the policy constraint.

Merge admission must read branch protection/enforcement and the main head through the GitHub API, then prove a merged PR with base main and merge_commit_sha equal to the selected SHA. Reject merely associated, closed-unmerged or different-commit PRs. Prefer reviewed merge/squash strategies; rebase merges need their own exact-final-commit proof tests. Preserve owner-only actor restrictions, including an owner check on whoever initiates a retry; do not silently trust a bot rerun as the owner.

**2. Required changes versus existing source**

| Area | Current implementation | Proposed change |
| --- | --- | --- |
| Main trigger | Auto workflow accepts eligible owner main push | Add enforced-protection/merged-PR admission, no direct-push bypass. |
| CI/security | Existing test/image jobs include Ruff/pytest/pip check/shell/Compose/migration-policy guard | Add explicit required security job: dependency audit, Python security analysis and secret scan, with pinned/declared tooling and no continue-on-error. Tool versions/configuration need implementation review; no scan was run now. |
| Tested image | CI builds/smokes, release helper independently builds again | Export the CI-tested image/provenance; load/publish it without rebuilding. |
| Readiness | /health/ready exists in source; release smoke omits it | Make it mandatory; validate body and required dependencies/schema manifest, not just process200. Its current SELECT1/conditional Redis check alone is not schema readiness. |
| API identity | OCI commit/source labels; no verified commit-identity endpoint found | Add reviewed baked identity contract, proposed GET /version returning semantic API version and commit_sha. Compare HTTP identity, OCI labels and selected CI SHA. OpenAPI's static version alone is insufficient. |
| Concurrency | Shared workflow-level group | Put the one production lock around release/admission/rollout/rollback, after CI; never cancel an active deployment. All other mutation paths must use that same group or be disabled. |
| Schema | Migration differences fail closed; history not reconciled | Keep refusal. First approved reconciliation/compatibility release must establish a hash-bound adopted-schema manifest; no bypass/head/stamp. |
| Manual candidate workflow | Can create zero-traffic production candidates by dispatch | Under final normal-release policy, make it validation-only or restrict it through an explicitly approved initial/recovery procedure. It must not remain an alternate normal deployment bypass. Preserve WIF restrictions; no trust change is needed for this design. |

Proposed implementation files, **not changed now**:

- `.github/workflows/backend.yml`: required jobs/security, reusable outputs and exact tested-image artifact.
- `.github/workflows/cloud-run-auto.yml`: main-push CI dependency, admission, single release lock, immutable-artifact rollout and complete metadata.
- `.github/workflows/cloud-run-candidate.yml`: remove normal deployment bypass; retain controlled preparation/recovery material.
- `backend/scripts/cloud_run_auto.py`, `cloud_run_candidate.py`, `docker_image_ids.py` as needed: stage separation, artifact/source proof, schema evidence, readiness/identity, stale handling, rollback and receipts; no extra IAM.
- `backend/Dockerfile` and reviewed build-metadata/version route/schema/tests: bake identity once at CI build. Never obtain a claimed SHA from an overridable production secret/env value.
- Relevant unit/integration/security test/config/declared CI-tool requirements and release docs. Any finance readiness/capability control is separate reviewed application work, not an already-existing env toggle.

Workflow files changed in **this** task: **none**. Files created: this design and the companion readiness report only.

**3. Same-commit CI and immutable-image handoff**

The reusable backend workflow must finish all of these named requirements for the selected merged SHA: lint/dependency check; complete PostgreSQL tests; security; migration policy; Docker build/nonroot/custom-port/readiness/identity/Compose smoke. Exact future GitHub required-check display names must be read back after implementation; do not guess a prefixed check name when configuring protection.

Exact proposed reusable job graph:

| Job ID / proposed display name | Dependencies | Required result |
| --- | --- | --- |
| lint / Backend lint | None | Declared dependency installation, pip check, full Ruff including release helpers, shell syntax. |
| test / Backend tests | None | Complete pytest with disposable PostgreSQL18, explicit synthetic URL and JUnit; required integration skips refused. |
| security / Backend security | None | Locked dependency audit, Python security analysis and secret/source scan; fail on findings under reviewed policy, no silent suppression or production credentials. |
| migration_policy / Migration policy | None | Existing migration-policy regressions plus exact source/schema-manifest classification and no head/stamp/startup execution path. This validates policy, never applies production SQL. |
| image / Build and smoke test image | lint,test,security,migration_policy all successful | Build exact archived SHA once, bake identity, smoke nonroot/custom port/readiness/version, validate Compose and export tested-image/provenance artifact. |

The reusable workflow exposes outputs from image's immutable artifact-upload result and verified provenance metadata. Normal push/PR triggers use this same graph with contents:read only; no CI job receives id-token:write or runtime secrets. Proposed security-tool helper/configuration and locked CI-only dependencies must be part of the reviewed implementation diff, not an assumed capability of current Ruff/pytest.

It must publish immutable artifact outputs:

| Output | Binding/verification |
| --- | --- |
| image_artifact_id | Artifact ID from the image job in this same workflow run/attempt; not a name search across successful runs. |
| image_artifact_digest | GitHub artifact/checksum identity, verified on download. |
| tested_image_config_digest | Image configuration digest from the image actually smoked. |
| tested_image_layer_ids | Ordered content identities; retain tested classic/containerd equivalence proof using the existing image-ID helper. |
| image_source_sha | Exact selected merged SHA and repository; image build labels and baked version identity must match. |
| migration_manifest_sha256 | Reviewed schema/compatibility target, not a guessed database head. |

CI builds from a clean archived exact commit using backend/Dockerfile with backend context. Controlled baked metadata is generated in the temporary build context and included in provenance; ignored/untracked developer files and credentials cannot enter it. Tests use disposable PostgreSQL and synthetic integrations, not production secrets.

Release downloads only that artifact ID from that run/attempt, verifies archive checksum/source metadata, loads the image and verifies the tested configuration/layers. It may retag and push to the existing Artifact Registry; it must never run docker build or otherwise rebuild it. Resolve the remote Linux platform digest and prove its configuration/filesystem identities match the tested artifact; serialization/index digest differences must be explained by verified content identity, not assumed. Deploy only the resulting `.../api@sha256:...` reference. A mutable latest tag is never an input or deployment target.

This avoids requiring private-repository paid attestation services or adding GCP credentials to CI. Artifact download/provenance helper must reject another run/repository/attempt/SHA, changed content, missing evidence or a manual replacement artifact.

**4. Proposed automatic workflow shape**

This is the exact intended job/control structure. The reusable outputs and helper subcommands below are **interfaces to implement and test**, not currently executable commands. It is not an applied workflow. Existing immutable action SHAs are retained; no unverified new action hash is invented.

```yaml
name: Cloud Run automatic production
on:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  ci:
    uses: ./.github/workflows/backend.yml
    permissions:
      contents: read
  release:
    needs: ci
    if: github.repository == 'Shifannv/salon-backend' && github.event_name == 'push' && github.ref == 'refs/heads/main' && github.actor_id == '172572480' && needs.ci.result == 'success'
    runs-on: ubuntu-24.04
    timeout-minutes: 50
    concurrency:
      group: production-cloud-run
      cancel-in-progress: false
    environment:
      name: production
      url: https://api.salones.in
    permissions:
      contents: read
      actions: read
      pull-requests: read
      id-token: write
    env:
      AUTO_DEPLOY_ENABLED: ${{ vars.AUTO_DEPLOY_ENABLED }}
      GH_TOKEN: ${{ github.token }}
      GCP_PROJECT_ID: ${{ vars.GCP_PROJECT_ID }}
      GCP_REGION: ${{ vars.GCP_REGION }}
      GCP_CLOUD_RUN_SERVICE: ${{ vars.GCP_CLOUD_RUN_SERVICE }}
      GCP_ARTIFACT_REGISTRY_REPOSITORY: ${{ vars.GCP_ARTIFACT_REGISTRY_REPOSITORY }}
      REQUESTED_COMMIT: ${{ github.sha }}
      CI_IMAGE_ARTIFACT_ID: ${{ needs.ci.outputs.image_artifact_id }}
      CI_IMAGE_ARTIFACT_DIGEST: ${{ needs.ci.outputs.image_artifact_digest }}
      CI_TESTED_CONFIG_DIGEST: ${{ needs.ci.outputs.tested_image_config_digest }}
      CI_IMAGE_SOURCE_SHA: ${{ needs.ci.outputs.image_source_sha }}
      MIGRATION_MANIFEST_SHA256: ${{ needs.ci.outputs.migration_manifest_sha256 }}
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803
        with:
          ref: ${{ github.sha }}
          fetch-depth: 0
          persist-credentials: false
      - name: Admit exact merged protected-main release, or record disabled/stale
        id: admit
        run: python3 backend/scripts/cloud_run_auto.py admit
      - uses: google-github-actions/auth@7c6bc770dae815cd3e89ee6cdf493a5fab2cc093
        if: steps.admit.outputs.eligible == 'true'
        with:
          project_id: ${{ vars.GCP_PROJECT_ID }}
          workload_identity_provider: ${{ vars.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ vars.GCP_DEPLOY_SERVICE_ACCOUNT }}
          create_credentials_file: true
      - uses: google-github-actions/setup-gcloud@aa5489c8933f4cc7a4f7d45035b3b1440c9c10db
        if: steps.admit.outputs.eligible == 'true'
      - name: Restore tested image, verify schema, deploy candidate and promote safely
        if: steps.admit.outputs.eligible == 'true'
        run: python3 backend/scripts/cloud_run_auto.py deploy-tested-image
      - uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        if: always()
        with:
          name: release-result-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}
          path: release-result.json
          if-no-files-found: error
```

Admission writes a receipt even when disabled/superseded/rejected. Disabled mode produces eligible=false before GCP auth. Invalid protection/merge/evidence is a refusal, not a successful deployment. The upload step/summary must preserve failure status; no continue-on-error can turn a failed release green. Pin runner/tool dependencies during implementation and validate this proposed structure with actionlint after reusable outputs exist.

**5. Release state machine, freshness and concurrency**

`CI_COMPLETE -> DISABLED | REJECTED | SKIPPED_SUPERSEDED | ADMITTED -> IMAGE_VERIFIED -> SCHEMA_VERIFIED -> CANDIDATE_READY -> CANDIDATE_VERIFIED -> PROMOTION_REQUESTED -> PROMOTED_HEALTHY | FAILED_ROLLED_BACK | FAILED_OPERATOR_ACTION_REQUIRED`.

One production job owns production-cloud-run from admission through final verification/rollback. CI may run in parallel; its cancellation never cancels an active release. Never use --to-latest or assign traffic from a different run's receipt. Existing service resource version/etag and digest/readiness checks guard external edits; patch only traffic and preserve tags/runtime/secret refs. Keep previous revision.

Immediately after acquiring the lock, verify current main SHA and merged PR. Recheck immediately before the first production mutation if artifact/preflight work took time. An older queued SHA is skipped without cloud mutation when a newer main exists. Once admitted and production mutation starts, do not force-cancel on a newer push: finish bounded verification/promotion-or-rollback, then allow the newest queued eligible release. Never interrupt rollback because main advanced. Future refactoring must distinguish admission freshness from immutable source identity; the current helper's repeated latest-main assertions are not a complete state-machine implementation.

GitHub concurrency is not a FIFO guarantee; replaced pending jobs can be skipped, but the newest eligible main run must retain a path to release. Test out-of-order CI completion, a newer run replacing pending work, and a new main arriving during rollout. Transient operations get bounded idempotent retries/inspection; reserve recovery time before the50-minute runner deadline. Runner loss/timeouts or persistent API failure can still require an operator; do not promise guaranteed rollback/liveness through an outage.

**Important policy edge case:** strict “skip an older commit whenever any newer main exists” conflicts with “eventually deploy the newest successful historical main commit” if a newer tip fails CI. This design follows the stricter tip-only rule: keep the previous healthy revision, wait for a successful corrected latest main, and do not silently deploy a non-tip green ancestor. If historical-green fallback is intended instead, the owner must explicitly revise the stale rule. Likewise a green but unhealthy/schema-incompatible commit must never be forced into production to satisfy liveness. Eventual deployment is conditional on the latest eligible tip passing all CI/schema/compatibility/health gates and infrastructure availability.

**6. Readiness, identity, smoke and rollback contract**

- CI/local/staging/candidate/production must all test /health/ready. Validate its agreed JSON body and dependencies, not merely HTTP200. Current readiness proves SELECT1 and configured Redis, not finance tables or0051 adoption: the separate schema/capability manifest must also be verified.
- Proposed /version must return baked commit_sha and semantic API version. Compare with selected commit, CI artifact and OCI source/revision labels. Also verify Cloud Run Ready and resolved platform image digest. Never assert identity by reading an overridable runtime env value.
- Candidate read-only smoke: readiness, process/DB/Redis, docs/OpenAPI and approved finance contracts/capabilities. Runtime authentication tests use separate approved test identities. No production booking/payment/expense/close/refund/deletion writes or SMS sends. Mutations are isolated-staging tests.
- Promote only the in-process verified candidate at its fixed digest, without rebuilding. Post-promotion verify readiness, identity and required read-only smoke on api.salones.in and apiv1.mudassirmhd.in. Fail fast on the first unhealthy result and retain the failed evidence.
- On failed verification, mark release failed even if rollback succeeds. Restore previous healthy traffic using etag/unchanged-state checks; verify rollback identity/readiness on both hosts. A conflicting external edit is not overwritten. Retain revisions/data and a specific operator rollback command if automatic repair fails.
- First legacy-to-Git release needs separately reviewed baseline provenance and rollback evidence: the current hybrid cannot be assigned a fabricated commit SHA. Explicitly approve how its fixed digest/inventory establishes old-image identity and prove old API/erasure workers tolerate new schema/data. Normal later releases require real baked Git identity.

**7. Migration policy: disabled now, no automatic migration job yet**

AUTO_DEPLOY_ENABLED staysfalse.0051 production execution, history reconciliation and finance API compatibility are not approved;0052 scope is unresolved. Workflow/schema compatibility checks must refuse release rather than trying to repair the DB. No Alembic stamp, manual guessed version-table adoption, baseline replay or blind upgrade head.

After the first reviewed schema-compatible release, make a **separate policy decision** about future migrations. Default remains explicit operator-approved execution plus a read-only schema gate. If automatic backward-compatible migration is later approved, require a dedicated pre-rollout job with exact target/files/hashes/preconditions, fresh recoverable backup evidence, privilege/lock/data-preservation review, tested forward repair and explicit approved compatibility classification. Destructive/backfill/history-reconciliation changes do not become automatic just because a PR merged. Any migration credentials/permissions need separate minimal-scope approval; the current deploy SA must not gain Secret Manager/database access implicitly.

No executable migration command is part of this design. No migration job is silently activated by the new application workflow.

**8. Required deployment metadata**

Every run records: status/admission reason; commit SHA/repository/actor/merged PR; exact CI run/attempt and required-job results; CI artifact ID/digest/tested config/layer identity; registry index and deployed platform digest; API version/commit identity; deployment start/endUTC; migration target plus approved schema-manifest/file hashes (including0052 only if approved); previous healthy/rollback and candidate/serving revisions; every readiness/smoke result; promotion/rollback state and exact rollback command. Do not label a guessed Alembic head as observed migration state. No secret/environment payload, token, raw SQL error or customer/financial row is uploaded.

DISABLED and SKIPPED_SUPERSEDED are visibly distinct from deployed-success. FAILED_ROLLED_BACK remains a failed deployment. Unknown traffic after a failed rollback must be reported as unknown/operator action, never false success.

**9. Dry-run/test plan — no production access**

No tests below were executed now. Implement tests first after design/source-work approval. Mock GitHub/GCP/registry/HTTP for guard/state tests; disposable DB/image tests use explicit local targets and synthetic integrations. A dry-run must not obtain OIDC credentials or call production even with GET.

| Scenario | Expected result |
| --- | --- |
| Push shifan/feature, PR/fork/closed-unmerged PR/tag/dispatch | CI as applicable; zero production auth/build-publish/deploy/traffic calls. |
| Direct main push, protection unenforced, admin bypass, associated-but-not-merged PR | Refuse admission before GCP auth. |
| Owner main merge, every exact-SHA job successful | Eligible only when activation/prerequisites are satisfied. |
| Any required job failed/skipped/cancelled, stale prior green or different SHA | No release. Security and migration-policy failures cannot be waived by aggregate green. |
| AUTO_DEPLOY_ENABLED absent/false | Disabled receipt; no GCP auth or deployment. |
| Wrong actor/repo/environment/ref/workflow/triggering actor | Refuse; existing WIF restrictions remain. |
| Different artifact run/attempt/SHA/config/layers/checksum or mutable latest tag | Refuse without build/deploy. |
| Correct saved image loaded/retagged/pushed | Same tested configuration/layers; remote platform digest/labels verified; assert no docker build in release. |
| Newer main before lock/start; CI finishes out of order | Old release skipped; newest eligible main remains runnable. |
| Newer main during admitted rollout/rollback | Active job not cancelled; finish safely, then latest queued admission. |
| Newer main fails CI | Preserve previous healthy revision under tip-only rule; document owner decision if different fallback wanted. |
| Missing/partial0051, history drift,0052 unapproved, schema incompatibility | Stop; no SQL mutation or app rollout. |
| Readyfalse, readiness503/malformed body, wrong API commit/version despite200 | No promotion; if already promoted, failed status plus rollback. |
| Digest changes after smoke, resource-version/etag conflict | Refuse stale mutation; inspect state and avoid overwriting external edits. |
| Lost PATCH reply after server acceptance | Inspect desired/resolved service state; roll back if needed, no blind duplicate mutation. |
| First public health fails | Start rollback without waiting for remaining slow probes. |
| Rollback succeeds | Verify previous revision and both hosts; keep deployment failed. |
| Rollback denied/API outage/runner lost | Retain operator-action receipt/command; do not drop revisions or restore DB blindly. |
| Schema guard destructive probe and app writes | Disposable PostgreSQL/staging only; zero production requests and provider sends. |
| Old owner/customer parsers, unavailable Finance, expiry/outbox, QR/avatar,0052 boundaries | Explicit compatibility acceptance; no fabricated totals or unintended writes. |

Static implementation validation: workflow YAML/actionlint; pinned action/tool inventory; permissions/event/needs/concurrency audit; shell syntax; secret/source-artifact allowlist; all backend lint/security/migration-policy/tests; full disposable-PG coverage; Docker nonroot/custom-port/readiness/baked-identity checks; Compose with synthetic input. Record required skips as failures/blockers. Offline test doubles verify every failed path makes zero unauthorized mutations.

Only after those pass and separate approval: isolated staging full acceptance, then initial reviewed production schema/compatibility release and bounded read-only candidate/public smoke. None is authorized by the current report request.

**10. Approval gates and stop point**

1. Owner reviews this design, including tip-only failure semantics, branch-protection feasibility and removal of direct/manual normal deployment bypasses.
2. Separate approval to implement source/workflow/identity/security changes; then review the exact diff and tests. No commit/push is authorized in this task.
3. Demonstrate enforced main protection and merge-only provenance with no broad IAM change. If unavailable, remain disabled; do not relax the requirement.
4. Separately approve fresh recovery evidence and exact production0051/history/remaining-schema plan, old-client behavior,0052 decision, erasure workers and rollback safety.
5. Complete and explicitly approve the initial proven-source schema-compatible candidate/promotion and post-release evidence.
6. Explicitly approve AUTO_DEPLOY_ENABLED=true only after all gates. Future eligible protected-main merges then authorize ordinary automatic releases; no per-release chat approval is needed.
7. Decide future automatic-migration policy separately; do not imply approval from application auto-deployment.

**Stop here.** Current workflow/helper files and production remain unchanged in this phase. No runtime checks were rerun; historical2002passed/36skipped and81 guards do not validate this new unimplemented policy. These two report files are the only deliverables.
