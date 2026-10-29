# Canonical repository and Cloud Run CI/CD audit

## Repository and authentication

- Requested D:/salon/salon-backend resolves to C:/D/salon/salon-backend in this session.
- User modification to README.md preserved and excluded from this change.
- origin now https://github.com/Shifannv/salon-backend.git.
- upstream now https://github.com/Thameempp/salon-backend.git.
- Existing shifan tracks origin/shifan; CI/CD branch starts at origin/main.
- Authenticated GitHub user Shifannv has admin/push access to the private canonical
  repository (ID 1422493480, owner ID 172572480). Connected GitHub app returned 404;
  existing Git credential authentication worked. No credential value was printed.
- gh was absent from PATH. Official portable gh v2.103.3 was downloaded to ignored
  scratch storage, SHA-256 verified, and auth status passed using the existing Git
  credential in process memory. Its read:org scope warning does not affect this
  user-owned repository; no new credential or broader login scope requested.
- GCP CLI active account 7alonbooking@gmail.com, active project saloon-505509.

Remote comparison before changes:

| Ref | Previous repository | Canonical repository |
| --- | --- | --- |
| main | 265bb187991b34c8032a04eaace5ed380e7c7978 | 5c6c4ea4b71abf2462e5d38fbfcbb6f4e408c827 |
| shifan | fdadfc47c1ac0ef37bbf31d7e2d851c57e9cb2b5 | same |
| Tags | none advertised | backup-personal-main-848dc1d at 848dc1dd9055a84a8fa4cd0e01dfc7a4fd60fa1f |

The main histories diverge by 8 previous-repository commits and 9 canonical
commits, but have identical tree 53df4c263e2c3d556b7c535e6368fd9595f14494.
Canonical main contains current shifan. No force update or main reconciliation
was needed. Both remotes fetched; canonical tags fetched. Upstream-only hafiz
and thameem branches were not copied as reviewed release branches. Existing
local main is an unrelated ahead/behind worktree branch; it was not reset or used
as release source. Upstream-only merge history remains preserved through upstream.

## Verified GCP baseline

- Project saloon-505509, number 283739091709, region asia-south1.
- Production service salon-api-production serves salon-api-production-subpct-20261028 at 100%.
- Serving image: asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:76ce6bec396732f0ac82957248547eead50f662bbc35fce3a42cbdfdb728a9d7.
- Runtime identity salon-production-runtime@saloon-505509.iam.gserviceaccount.com.
- Concurrency 8; existing service max 1 and revision max 3. These distinct limits
  are preserved, not normalized. Ready confirmed. No env values or Secret Manager
  payloads read/displayed; mounted runtime configuration was not modified.
- Existing Docker repositories salon-production and salon-mumbai-staging.
- No Workload Identity pools. Existing github-deploy account has project-scoped
  artifactregistry.writer and a user-managed key dated 2026-08-18. Account IAM
  contains no federation impersonation bindings; no runtime actAs grant found.
  No new grant/key created; no existing key read or revoked.
- No Cloud Build triggers in asia-south1 or global. Recent listed Mumbai builds
  have no buildTriggerId. Both inspected GitHub backend workflows had only
  manually gated production deployment; no automatic old-repository production
  path found in these inspected scopes. This is not an audit of external systems.
- Notification worker pool salon-prod-notifications and job salon-production-db-check
  exist. No Mumbai Scheduler jobs listed. Other worker coverage/health unverified.
- Registry image downloaded for label inspection: OCI revision and source labels
  absent. Therefore a serving-source baseline and migration delta cannot yet be
  proven. Candidate creation must remain blocked; do not infer a source SHA.

## GitHub configuration audit and changes

Workflow names before change: Backend CI/CD and Approved Mumbai migration
validation (read only). Previous repository also lists Copilot/Copilot cloud agent.
Canonical environments, Actions variables and Actions secrets were empty.
Previous-repository environments: copilot, production. Previous-repository secret
names only: VM_HOST, VM_KNOWN_HOSTS, VM_SSH_KEY, VM_USER. No values inspected.

Configured four canonical repository variable names: GCP_PROJECT_ID, GCP_REGION,
GCP_CLOUD_RUN_SERVICE, GCP_ARTIFACT_REGISTRY_REPOSITORY. No Actions secrets added.
GCP_WORKLOAD_IDENTITY_PROVIDER and GCP_DEPLOY_SERVICE_ACCOUNT remain unset pending
the separate [IAM approval](../CLOUD_RUN_OIDC_IAM_PROPOSAL.md).

Rulesets and main protection API both return 403: upgrade to GitHub Pro or make
the repository public. production environment absent. Private required environment
reviewers additionally require a supported plan; Pro alone is insufficient under
the current [GitHub documentation](https://docs.github.com/en/rest/deployments/environments).
No billing, visibility or protection downgrade performed. See
[CI_CD.md](../CI_CD.md) for the exact settings/check names to configure.

## Implemented behavior

Active backend workflow contains only CI. Legacy VM job/packaging removed from
normal execution; scripts/recovery documentation retained. New protected manual
candidate workflow uses pinned Actions, OIDC and the existing production registry.
It reruns CI, rejects feature branches/stale main/unprotected context/dirty source,
requires a proven baseline with no migration differences, and builds a git archive
of the exact selected commit. Image labels/digest are verified before an image-only
zero-traffic deployment. Existing runtime settings and normal traffic are compared
privately before/after. Only readiness and public read-only HTTP probes execute.
Receipt includes rollback command; no automatic production promotion exists.

Two existing integration fixtures stopped at 0049 while repository SQL reads
0050's valid_until column. The initial full run reproduced 27 undefined-column
failures. Fixtures now apply the already committed 0050 SQL to their disposable
localhost databases; no assertions skipped, app/migration SQL modified, migration
policy relaxed, or remote database touched.

## Local verification

- Full pytest with disposable PostgreSQL 18: **1727 passed, 36 skipped**, one
  dependency deprecation warning, 228.57 seconds. Skips are separately opt-in
  suites, not a claim of full production/schema compatibility.
- Fifteen release guard tests cover wrong repo/ref/event/target, stale main,
  absent protection/reviewers, wildcard environment policies, migration changes,
  unexpected runtime/scaling/traffic changes and permitted image-only changes.
- Ruff and pip check pass; actionlint v1.7.12 validates workflows.
- All backend/scripts/*.sh pass bash -n; Compose config validation passes without
  printing configuration/template contents.
- backend-only Docker build succeeds; nonroot, PORT=8080, /health, packaged
  migrations and worker import smoke pass. This image is local verification only,
  not pushed/deployed. No production image was built from the working tree.
- Diff reviewed and migration files unchanged. README.md remains user-owned.

## Release hold

Source branch/PR may be pushed for review. Do not merge with failing CI. Candidate
cannot be deployed from the feature branch and is held until protected main,
reviewer environment, approved IAM, reviewed/merged workflow and serving-source
provenance are verified. No candidate revision/URL exists for this change, so no
traffic approval is requested. No production deployment/promotion, database
migration, DNS/TLS/LB/scaling/secret/billing change, VM deployment, resource deletion
or worker activation was performed.
