# Approved migration 0058 and PR #52 production release

The user explicitly approved migration 0058 and PR #52 production deployment,
including the new permanent admin salon-erasure capability. The SQL was installed
on 2 November 2026. Tool approval-service quota stopped the API deployment command
before it ran. The user resumed work on 3 November; the previously approved tested
image was deployed and promoted successfully after renewed state verification.

## Production identity

- Source: PR #52, `253a591cea7ee81c5cc3a5cda5e354ada14eb5be`, verified latest main.
- Supervised revision: `salon-api-production-approved-253a591-0058-20261102`.
- Tested image:
  `asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:63799e3a86e588f5efe4a1118fca6701a0d4a14d7d512628373b492da9551311`.
- Both `https://api.salones.in` and `https://apiv1.mudassirmhd.in` passed readiness,
  exact source identity, API/database/Redis health, Swagger and OpenAPI checks.
- OpenAPI is backward compatible, with 176 paths and SHA-256
  `c19a9e9df1fcd192588d159c15e547fc3ff8aaab1bf9a514e9c3c0e738559610`.
- Previous healthy revision `salon-api-production-gh-fa82510e-41436345489-2` is retained.

The image was built and smoke-tested successfully by GitHub for this exact main
commit. It was not rebuilt for the supervised rollout. Runtime configuration and
existing tags were preserved. No worker deployment or production erasure/refund
operation was part of verification. Authenticated destructive flows were not run.

## Schema and backup

A fresh encrypted backup preceded SQL execution. Checksum, complete GPG decryption
and archive listing passed (108 table-data entries). No plaintext dump was written;
this particular archive has not undergone a new full restore rehearsal.

Only the reviewed 0058 SQL ran, in one transaction with bounded locks/statements.
Its bytes exactly matched the selected Git blob. The tombstone table has RLS;
`anon` and `authenticated` cannot access it or execute `erase_salon(uuid)`.
The backend execute grant and exact function body were verified. Existing trigger
modes, salon counts and Alembic history were unchanged. No erasure job was created.
Live metadata on 3 November reconfirmed installation, RLS and public-role denial.

Alembic remains `0052_booking_window_30_days` under the previously approved SQL-only
release procedure; no stamp, history rewrite or baseline replay ran. The SQL installs
an admin capability that can delete financial history when later explicitly invoked.
This release authorization does not authorize deletion of any actual salon.

Exact identities and hashes are in
[the execution receipt](../../deployments/schema-0058-20261103.json).
Ignored operational receipt:
`backend/.artifacts/approved-0058-pr52-recovery.json`.

## Automatic release

PR #51 and PR #52 CI/image checks passed, but release refused the unreviewed migration
source delta relative to the serving fa82510 image. Applying SQL alone does not
establish a new serving-image baseline. The approved supervised 253a591 release now
provides that proven baseline, without changing or weakening the migration guard.

The entire [PR #52 workflow](https://github.com/Shifannv/salon-backend/actions/runs/41450888389)
was rerun after promotion to verify automatic CI, image publication, candidate checks
and production promotion. Attempt 2 completed successfully, recording
`PASS_PRODUCTION_PROMOTED` at 06:10:16 UTC / 11:40:16 IST on 3 November 2026.
Later schema-changing releases still require their own approval and compatibility
rollout; green CI alone does not establish production schema readiness.

## Final automatic release verification

[Successful attempt 2](https://github.com/Shifannv/salon-backend/actions/runs/41450888389/attempts/2)
passed **2,620 tests with 42 skipped** and one dependency deprecation warning.
Admission, the dedicated Docker build/smoke/publication job and release all passed.
The reusable image job is intentionally skipped because the dedicated production
image job performs those checks.

Independent verification confirmed 100% traffic on
`salon-api-production-gh-253a591c-41450888389-2`, Ready with immutable image
`asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:5a9d1fe6dc7f94d8de87422079fcc53c066e05532c6050885d3d212c67f30b5c`.
Both public domains independently returned the exact PR #52 commit and healthy
readiness/process/database/Redis responses after automatic promotion. The supervised
253a591 revision and prior fa82510 revision remain retained as rollback choices.

No workflow guard was weakened. The missing reviewed schema and compatibility
rollout were completed, establishing the correct baseline for normal automation.
The new execution receipt and documentation are local changes, not yet committed
or pushed.
