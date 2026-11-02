# Production and automatic deployment verified — 2 November 2026

Latest main is serving 100% production traffic. The ordinary automatic merged-main
workflow passed CI, candidate verification, promotion and post-promotion probes.

## Identity

- API: <https://api.salones.in>; legacy <https://apiv1.mudassirmhd.in> remains healthy.
- Commit: `a7641fcbe5925ebe4528f78a144d4d98dc0aea9e`.
- Revision: `salon-api-production-gh-a7641fcb-41408082110-1`.
- Image: `asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:f05e2675e632107716379917a1aa947014275f9b24c8cbc9f6122f58893b585d`.
- Automatic release completed 13:21:21 IST; independent final verification 13:22:57 IST.
- [Successful workflow](https://github.com/Shifannv/salon-backend/actions/runs/41408082110).

## Evidence

Full CI passed **2,449 tests, 42 skipped**, with one dependency deprecation warning.
Ruff, pip check, shell syntax, Compose and workflow validation passed. Docker passed
non-root/custom-port, health, worker-import and packaged-migration checks. Three
modifier regressions reproduced the failure before correction; 111 focused checks
passed afterward. Earlier complete local PostgreSQL-backed tests passed 2,446 tests
before those three additions.

| Check | Result |
| --- | --- |
| Exact merged latest-main source and existing WIF identity | Pass |
| Tested image config/layers/source/run and immutable registry digest | Pass |
| Candidate Ready and resolved digest | Pass |
| Candidate readiness, version, API health, DB, Redis, Swagger and OpenAPI | All seven HTTP 200; health/identity checks pass |
| OpenAPI backward comparison against approved serving contract | Pass; 166 paths |
| Runtime/traffic preservation and automatic promotion | Pass; candidate at 100% |
| Readiness, version, health, DB and Redis on both API domains | All ten pass |
| Independent latest-main, traffic, digest and public probes | Pass |

OpenAPI SHA-256: `89842338011e1897d7266b37a1f8128af473daa8c8f72e8daa538eb5bcfe955f`.
Only safe read-only probes ran. Authenticated customer/booking/payment mutations
were not tested. Workers were not deployed or exercised; import checks establish
only import compatibility.

## Schema and delivered fixes

Approved production SQL **0053–0055 was already applied and verified**. No SQL was
rerun by this automatic release. Alembic history intentionally remains at 0052 under
the approved SQL-only procedure. No stamp or history rewrite occurred. Existing
encrypted recovery-backup retention is unchanged.

The owner accepted the admin trial contract changes and explicitly approved the
first supervised promotion of 0027a9b; see [that report](CLOUD_RUN_CANDIDATE_0027A9B_2026-11-02.md).
This release then used that serving commit as its proven no-migration baseline.

- [PR #47](https://github.com/Shifannv/salon-backend/pull/47): tested image delivered
  through existing Artifact Registry, removing the GitHub image-archive dependency.
- [PR #48](https://github.com/Shifannv/salon-backend/pull/48): required Actions read
  permission restored for environment admission.
- [PR #49](https://github.com/Shifannv/salon-backend/pull/49): output-only lastModifier
  excluded from configuration comparison; actual runtime/etag/rollback guards retained.

`AUTO_DEPLOY_ENABLED` is the sole production-environment gate, exactly true; its
existing value was not changed. The legacy switch remains unused and unchanged.
Feature pushes and PRs run CI only. Eligible owner PR merges to latest main deploy
only after same-run CI/image checks, then promote or roll back after verification.
Stale sources are rejected and active releases are not cancelled. Future migration
differences still require separate approval. GitHub Free private branch rules remain
unenforced; preserve owner review and the existing workflow/WIF restrictions.

Optional report uploads can retain quota annotations until GitHub storage accounting
refreshes. They did not fail this successful run; production image delivery does not
depend on GitHub archives. No application business logic, GitHub settings/variables,
IAM/WIF, roles, DNS, certificates, load balancers, billing, runtime secrets or scaling
were changed in these CI/CD releases.

## Rollback

Previous healthy revision and image remain available. The older 6fefff4 revision is
also retained. No revision was deleted.

```powershell
gcloud run services update-traffic salon-api-production --project=saloon-505509 --region=asia-south1 --to-revisions=salon-api-production-gh-0027a9be-41405234717-1=100
```

Ignored receipts: `backend/.artifacts/candidate-41408082110.json` and
`backend/.artifacts/final-auto-release-verification-20261102.json`.
