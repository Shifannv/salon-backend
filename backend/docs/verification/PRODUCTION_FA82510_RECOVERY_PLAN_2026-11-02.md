# Production recovery for fa82510 — approved and executed

The user explicitly approved this operation. Migrations and the supervised API
release completed successfully; see
[execution results](PRODUCTION_0056_0057_EXECUTION_RESULT_2026-11-02.md).
The remainder records the plan and state established before that approval.

## Verified cause

[Automatic run 41436345489](https://github.com/Shifannv/salon-backend/actions/runs/41436345489)
passed CI, admission and image publication. Its release job stopped with:

```text
Migration differences require separate reviewed backup, target and approval; candidate refused
```

Latest remote main and local HEAD are `fa82510e9aed22d9dee48784e089a94f4467c64d`.
Production remains healthy on `a7641fcbe5925ebe4528f78a144d4d98dc0aea9e`, revision
`salon-api-production-gh-a7641fcb-41408082110-1`, with 100% traffic.
No production setting, schema or traffic was changed by this investigation.

Read-only inspection of Mumbai project `wqjlgpnbiapcrlkxumcp` found all six new
tables absent: `platform_payment_settings`, `salon_commission_overrides`,
`payout_proofs`, `salon_payout_payments`, `salon_payout_corrections`, `payout_audit`.
`salon_payout_requests.balance_snapshot` is also absent. There are zero payout
requests. Alembic remains at `0052_booking_window_30_days`; the earlier approved
0053–0055 SQL release did not stamp migration history.

## Exact proposed operation

1. Create and verify a fresh encrypted production database backup. Existing local
   backup listings are dated 27 October or earlier and are not this release's backup.
2. Apply only the reviewed SQL for 0056 then 0057 in a controlled transaction, with
   their existing lock/statement timeouts. Do not replay 0001–0055, run `upgrade head`,
   or stamp/rewrite Alembic history. Verify prerequisites and hashes again first.
3. Verify the six tables, snapshot column, constraints, indexes, functions, triggers,
   RLS and public-role denial against the reviewed SQL. Keep payment providers and
   runtime commission configuration unchanged.
4. Deploy the already CI-tested immutable image to the existing service as a
   zero-traffic candidate, preserving runtime configuration and existing tags:
   `asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:a9f46aa81d62437304e91dc403140d8a09293d44eb1b2cb76c1e7a1a73a271ae`.
   Resolve its platform manifest and confirm source labels before deployment.
5. Verify readiness, exact `/version`, API/DB/Redis health and OpenAPI compatibility,
   including the new routes. Promote only the verified candidate to 100% and verify
   `api.salones.in` and `apiv1.mudassirmhd.in`. Retain the current revision for traffic
   rollback. No automatic database downgrade: both migrations are forward-only.
6. Record actual execution evidence and the narrowly hash-bound schema receipt.
   Once the supervised serving image matches this main source, the existing release
   code derives its proven baseline directly; no compatibility exception is needed.
   Later merges without schema changes use the ordinary automatic release.

0056 creates the payment settings and salon overrides with private access; the
initial commission rate/base remain NULL. 0057 adds the snapshot and four private
financial evidence tables, with append-only guards, and replaces the payout request
guard so marking paid requires recorded proof/payment. Coordinate schema execution
and API replacement because the old payout code lacks this new write contract.

## Reviewed working-file hashes (SHA-256)

| File under backend/migrations/ | SHA-256 |
| --- | --- |
| sql/0056_platform_payment_settings.sql | cd83baf69c33f0e5c69f819758844a774d79d23d1f6641d7487e0b1a68119b3f |
| sql/0057_payout_proof.sql | 4ae99ba10d27297f8cd7a49d1858c5a7a36b16ce99b26bf56a762769da52ac61 |
| versions/0056_platform_payment_settings.py | 711dd6e21b31bcc84c347957c5a3cc550a9b087e7ecc482e3946d54cdffaa6f0 |
| versions/0057_payout_proof.py | c64bb11053fed1e9655efb629db1152cf670d527abfc6e80dcdf175300b61645 |

These are reviewed source hashes, not proof of production execution. Bind Git blob
hashes and executed bytes explicitly when constructing the eventual release receipt.
Earlier local verification ran 2,600 tests successfully with 42 skips; the new local
preflight also passed lint, PostgreSQL tests, Docker build and container smoke checks.
GitHub separately passed its checks for this exact merged commit before publication.

## Authorization resolved

The user requested production API deployment first, then automatic release repair.
The user subsequently explicitly approved the backup and exact 0056–0057 SQL
operation above, followed by deployment of the tested API. Execution is complete.
