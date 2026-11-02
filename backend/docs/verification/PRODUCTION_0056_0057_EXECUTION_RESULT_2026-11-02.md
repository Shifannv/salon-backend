# Approved 0056–0057 production recovery

The owner explicitly approved migrations 0056 and 0057 and deployment of the tested
API. Both SQL files committed in one transaction on Mumbai production project
`wqjlgpnbiapcrlkxumcp`. The tested `fa82510` image was then deployed and promoted
successfully to `salon-api-production-approved-fa82510-20261102`.

Both `https://api.salones.in` and `https://apiv1.mudassirmhd.in` passed readiness,
exact `/version` commit identity, process/database/Redis health, Swagger and OpenAPI
checks. Both domains serve `fa82510e9aed22d9dee48784e089a94f4467c64d`.
OpenAPI has 174 paths and SHA-256
`4dab33441e51a8fb980d59c49f9d3a09aefc9ba21a326a01f8aaa8188e3b8894`.

The image was reused from successful CI in
[run 41436345489](https://github.com/Shifannv/salon-backend/actions/runs/41436345489),
without rebuilding for the supervised release:
`asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:a9f46aa81d62437304e91dc403140d8a09293d44eb1b2cb76c1e7a1a73a271ae`.
Source labels and resolved digest were verified. All runtime settings and earlier
review tags were preserved. The previous healthy `a7641fc` revision is retained.

## Database verification

All six tables exist with RLS enabled and no table access for `anon` or
`authenticated`. The payout snapshot is JSONB. The three required guard functions
and expected constraints and triggers are installed. Payment settings have one
singleton row; commission rate and base remain unset. No provider or application
runtime setting was changed. No customer/booking/payment mutation was exercised.

Alembic history remains `0052_booking_window_30_days`, consistent with the approved
SQL-only execution process used for 0053–0055. No stamp, baseline replay or migration
history rewrite ran. Both new migrations are forward-only. API rollback does not
undo them and must account for the payout-proof write contract.

Before execution a fresh encrypted database archive was created and verified by
checksum, complete GPG decryption and `pg_restore --list` (102 table-data entries).
No plaintext archive was written. This archive has not undergone a new full restore
rehearsal. Exact hashes, backup identity and verification are recorded in
[the execution receipt](../../deployments/schema-0056-0057-20261102.json).
The ignored operational receipt is
`backend/.artifacts/approved-0056-0057-recovery.json`.

## Frontend contract

Eight admin paths are added. No existing path or operation is removed.
`POST /v1/admin/wallet/payout-requests/{request_id}/mark-paid` now accepts multipart
form data containing the payment details and proof, replacing the reference-only
JSON body. The obsolete `PayoutMarkPaidRequest` component is removed. Existing
response fields are preserved; wallet responses add optional payment metadata.
This exact 0057 contract delta was reviewed during the explicitly approved release.
The admin frontend must use the multipart form; old reference-only calls fail
validation instead of marking payouts paid without evidence.

## Automatic release recovery

The original release correctly refused migration differences while its tests and
image jobs passed. The missing production schema and serving baseline have now been
reconciled through the approved supervised operation. A new compatibility bypass in
the release code is unnecessary: the serving image now proves `fa82510` as its Git
baseline, so unchanged migration sources compare equal for the next automatic run.
The full workflow was rerun as attempt 2 to validate CI, same-attempt image provenance,
candidate checks, promotion and rollback safeguards. The original migration guard
remains intact; future schema changes still need approval before their API release.

## Successful automatic run and final verification

[Attempt 2](https://github.com/Shifannv/salon-backend/actions/runs/41436345489/attempts/2)
completed successfully. CI passed **2,600 tests, 42 skipped**, with one dependency
deprecation warning. Admission, image build/smoke/publication and the production
release all succeeded. The reusable image job is intentionally skipped because
the dedicated production image job builds and verifies the image instead.

The release recorded `PASS_PRODUCTION_PROMOTED` at 11:56:20 UTC / 17:26:20 IST.
Independent final inspection confirmed:

- 100% traffic on `salon-api-production-gh-fa82510e-41436345489-2`.
- Immutable image
  `asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:b4098be95fc82868d819edf6e7a9822eb82147682dd19089515de687280dc1b9`.
- Exact `fa82510e9aed22d9dee48784e089a94f4467c64d` commit identity on both API hosts.
- Readiness, process, database and Redis health all returned `ok` on both hosts.
- The supervised fa82510 revision remains retained as the immediate rollback target;
  the older a7641fc revision is also retained. No revision was deleted.

No workflow source change was needed: completing the approved production schema and
supervised compatibility release resolved the cause, and the unchanged automatic
workflow now passed end to end. The execution evidence and deployment-guide updates
are local documentation changes, not yet committed or pushed.
