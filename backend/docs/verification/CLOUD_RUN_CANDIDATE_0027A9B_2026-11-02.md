# Latest main candidate — 2 November 2026

Status: the owner explicitly accepted the listed admin contract changes and approved
`PROMOTE CLOUD RUN CANDIDATE`. This existing revision was promoted to 100% production
traffic at 13:04 IST. Independent canonical and legacy readiness, commit, API health,
database and Redis checks all passed at 13:06 IST. No rebuild or migration ran.

## Immutable release identity

- Main commit: `0027a9be0f0340688c19cb018202c6600cd628ac`.
- Image: `asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:e6bcb42dbd9f240a48adf536bf946d88b595a85b72bbc9ba22307a023c2815e3`.
- Candidate: `salon-api-production-gh-0027a9be-41405234717-1`.
- Candidate URL: <https://gh-41405234717-1---salon-api-production-jmqpp743pa-el.a.run.app>.
- Ready time: 2 November 2026, 12:54:57 IST.
- Previous rollback revision: `salon-api-production-ci-6fefff4-20261101`.
- Current 100% revision: `salon-api-production-gh-0027a9be-41405234717-1`.
- Serving commit: `0027a9be0f0340688c19cb018202c6600cd628ac`.
- [Workflow evidence](https://github.com/Shifannv/salon-backend/actions/runs/41405234717).
- [Registry transport PR #47](https://github.com/Shifannv/salon-backend/pull/47)
  and [read-permission correction PR #48](https://github.com/Shifannv/salon-backend/pull/48) are merged.

The same workflow passed full CI, admitted the exact latest merged main, verified
the existing WIF claims, built and smoke-tested the image, published it to the
existing registry, checked its config/layer/source/run identities, and deployed
its immutable digest without rebuilding. Cloud Run's resolved digest matches.
The image-only update passed the workflow's runtime/traffic preservation check.
Independent metadata checks confirmed Ready and, after approval, this revision at 100%.
The original workflow remains failed on its contract guard; owner acceptance and
supervised promotion are recorded separately, without relabeling that CI result.

The traffic API update succeeded, but the existing wrapper falsely included
server-owned `lastModifier` in its runtime comparison after the operator changed.
Its recovery guard refused an additional write. Independent checks established the
successful, healthy production state; no rollback traffic write occurred. A focused
follow-up fixes that comparison while retaining runtime and concurrency guards.

## Read-only verification

| Probe | Result |
| --- | --- |
| `/health/ready` | HTTP 200, status ok |
| `/version` | HTTP 200, exact candidate commit |
| `/health` | HTTP 200, status ok |
| `/health/db` | HTTP 200, status ok |
| `/health/redis` | HTTP 200, status ok |
| `/docs` | HTTP 200 |
| `/openapi.json` | HTTP 200, valid stable document; compatibility exception pending |

OpenAPI SHA-256: `89842338011e1897d7266b37a1f8128af473daa8c8f72e8daa538eb5bcfe955f`.
Independent probes also verified the serving commit and health endpoints on both
`api.salones.in` and `apiv1.mudassirmhd.in`. No authenticated business mutation,
checkout, payment, booking, customer write or account deletion was performed.

## Exact compatibility blocker

No existing paths or HTTP operations were removed. Comparing existing component
schemas found these changes:

| Schema/field | Serving contract | Candidate contract |
| --- | --- | --- |
| `AdminApproveSalonRequest.trial_booking_limit` | Optional, default 500 | Required integer; same 1–1,000,000 bounds |
| `SalonTrialResponse.trial_days` | Default 60; bounds 1–3650 | Required integer; old default/bounds absent |
| `SalonTrialResponse.trial_booking_limit` | Integer, default 500; bounds 1–1,000,000 | Integer or null; old default/bounds absent |

Affected operations:

- `POST /v1/admin/salons/{salon_id}/approve`.
- `GET /v1/admin/salons/{salon_id}/trial`.
- `PUT /v1/admin/salons/{salon_id}/trial`.

Older admin approval requests omitting the limit can receive 422. Admin trial
clients must tolerate a null booking limit. These are real compatibility changes;
the generic contract guard has not been weakened or silently bypassed. Promotion
requires explicit acceptance for this exact image, or a separately tested fix
restoring compatibility. The workflow status remains failed for that guard.

## Database, workers and remaining gate

Approved production SQL 0053–0055 was already applied and verified in the preceding
release phase, with its retained encrypted recovery backup. No SQL was rerun here.
The candidate admitted only the exact six reviewed SQL/wrapper files through the
hashed execution receipt. It packages `0055_feature_access`; production Alembic
history was intentionally left at 0052 under the approved SQL-only procedure.
No stamp or automatic migration was introduced.

This deploy covers the API image only. Notification, payment, email, media cleanup
and account deletion workers were not deployed or exercised against production.
Their imports passed container smoke tests; that is not worker-runtime coverage.

`AUTO_DEPLOY_ENABLED` remains the sole production-environment switch. The repaired
pipeline now reaches real candidate creation without a GitHub image archive.
After the first compatibility candidate is explicitly accepted and promoted,
future successful latest owner main merges with no migration/contract regression
can use the normal automatic promotion/rollback path. Future migrations remain
separately gated. GitHub Free private branch protection remains unenforced.

No DNS, certificate, IAM/WIF, role, billing, scaling, runtime-secret or GitHub
variable change was made during this candidate release.

## Promotion and rollback

Completed owner decision: accept the admin contract changes above and approve
`PROMOTE CLOUD RUN CANDIDATE`. The existing revision was promoted without rebuilding.
Verify readiness, exact commit and health on both API domains. If verification
fails, return traffic to the recorded healthy revision; retain both revisions.

```powershell
gcloud run services update-traffic salon-api-production --project=saloon-505509 --region=asia-south1 --to-revisions=salon-api-production-ci-6fefff4-20261101=100
```

Local operational evidence (ignored, no secret payloads):
`backend/.artifacts/candidate-41405234717.json`,
`backend/.artifacts/candidate-contract-differences-41405234717.json`, and
`backend/.artifacts/candidate-verification-41405234717.json`.
