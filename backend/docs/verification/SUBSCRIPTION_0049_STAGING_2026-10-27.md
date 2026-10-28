# Subscription 0049: applied database change and staging release

Status: staging deployed; available smoke checks pass. Owner-authenticated plan
response remains pending. Production code promotion is NOT approved or executed.

## Authorization and recovery

The user approved applying only 0049 to the shared Mumbai database, deploying
staging, then stopping until an explicit “go production”. Supabase reported no
hosted backups and PITR disabled, so no hosted recovery timestamp exists. The user
explicitly accepted verified encrypted local copies as the backup gate.

Copies created **2026-10-27 14:19:28 UTC / 19:49:28 IST**:
`C:\Users\Lenovo\AppData\Local\SalonRecovery\subscription-0049-20261027T141928053859Z`

- `subscription-objects-data.sql.gpg`: pg_dump data-only for public.subscription_plans and public.salon_access.
- `start-salon-trial.sql.gpg`: original public.start_salon_trial(uuid, timestamptz) definition.
- `object-metadata.json.gpg`: original default, function ownership/ACL and counts.
- `backup-manifest.json`: nonsecret checksums and recovery metadata.

Decryption and plaintext hashes verified in memory; files encrypted and locally
access-restricted. These scoped local copies are not a full/off-device backup.

## Database result

Only `backend/migrations/sql/0049_trial_salon_plan_prices.sql` applied, 13 approved
statements, using `psql --single-transaction -v ON_ERROR_STOP=1`. Completed
**2026-10-27 14:31:34 UTC / 20:01:34 IST**. SQL SHA-256:
`6c3f2905c5708c6efb2f2875097b7c56c7f19757f1c28b6187bb676cd470b884`.

Preflight prerequisites passed and salon_plan_prices did not exist. Postflight:

- salon_plan_prices exists; RLS enabled; anon/authenticated SELECT denied.
- service_role SELECT, INSERT, UPDATE and DELETE each granted.
- New trial booking limit default 500; all seven started trials retain 120.
- Growth monthly/6-month/12-month prices: 349 / 1675 / 2932.
- Premium monthly/6-month/12-month prices: 599 / 2875 / 5032.
- Alembic history remains empty and unchanged; no upgrade or stamp executed.

Staging and production share this database: these database changes already affect
production data/defaults, although production serving code remains unchanged.
Do not rerun 0049. Local evidence: `.artifacts/subscription-0049-20261027/migration-result.json`.

## Staging image and runtime

- Source: `28f6e94edbe951b52b07f1b74e9e4e8430542b4c`, branch shifan.
- Image: `asia-south1-docker.pkg.dev/saloon-505509/salon-mumbai-staging/api@sha256:f33de3348cb682e7ea553587aaa8497c5ee68c75e9dd1eb3b2134584e27d4eac`.
- Linux manifest digest: `sha256:9e9242a56906d57ce8ccf919f2fe420db5a631937dc056c6796f144da4547426`.
- Revision: `salon-api-mumbai-staging-sub0049-28f6e94-20261027`, 100% staging traffic.
- URL: https://salon-api-mumbai-staging-jmqpp743pa-el.a.run.app (private IAM).
- Previous staging revision: `salon-api-mumbai-staging-cold10-20261020`.
- Checkout URL: https://salones.in/subscription/checkout.
- CORS includes https://salones.in and https://www.salones.in.

Existing secrets, IAM, resources and service account preserved. Revision max 1
and existing service max 3 preserved; no scaling setting changed. Image includes
the public Supabase CA with a pinned checksum. No startup migration.

## Verification

Ruff passes. Pytest: **1438 passed, 180 skipped**, one dependency deprecation
warning. Skipped integrations are not live integration evidence. Offline image
checks pass: nonroot runtime, no env files, correct CA, checkout URL and OpenAPI.

Live checks at **14:42:03 UTC / 20:12:03 IST**:

| Check | Result |
| --- | --- |
| IAM-authenticated /health, /health/db, /health/redis | Each 200 |
| /v1/subscriptions/config checkout_url | 200, expected URL |
| /openapi.json admin salon plan-prices route | 200, present |
| CORS preflight for both website origins | Each 200, origin matches |
| Anonymous staging /health | 403 |
| Staging IAM public grants | None |
| api.salones.in/health and apiv1.mudassirmhd.in/health | Each 200 |
| Production serving revision | salon-api-production-api-domain-20261027 at 100% |
| Owner GET /v1/subscription-plans | Pending owner session; not claimed passed |

The owner test needs a genuine Supabase owner access token, separate from GCP
login. Request a protected file path or interactive owner login; never paste or
log credentials. Use X-Serverless-Authorization for Cloud Run IAM and Authorization
for the owner session. Verify all four price fields, annual/semiannual prices and
discounts, and null monthly discount before considering production approval.

Local receipts/scripts are in `backend/.artifacts/subscription-0049-20261027/`:
`staging-deployment.json`, `staging-smoke.json`, `apply_0049.py`,
`deploy_staging.py`, `smoke_staging.py`. No production deployment, old hostname
removal, or deletion-worker activation performed. Do not promote production until
the owner check passes and the user explicitly says “go production”.
