# Production SQL 0053–0055 execution result

Status: **PASS — production database schema applied; API rollout not performed.**

Owner authorization: “APPROVE production SQL 0053–0055 under this plan,
including a fresh encrypted backup retained for release recovery.”
Target: Supabase project `wqjlgpnbiapcrlkxumcp`.
Completed receipt timestamp: 1 November 2026 18:28:24 UTC / 23:58:24 IST.

## Recovery evidence

Fresh snapshot: 1 November 2026 18:25:51.258536 UTC / 23:55:51.258536 IST.
Backup identifier: `reconciliation-20261101T182551020282Z`.
Archive: 221,379 bytes; SHA-256
`84c76c228d7185b8aaef22096ad46486725dc8977109c04c6014e0db0cae789a`.
Decryption hashes verified. A network-isolated Supabase PostgreSQL 17.11 restore
matched all 94 exported table fingerprints and original effective privileges.
Recovery verification took 0.841 seconds; the isolated database was removed.

Encrypted archive and encrypted recovery metadata are retained, access restricted,
outside the checkout at:
`C:\Users\Lenovo\AppData\Local\SalonRecovery\reconciliation-20261101T182551020282Z`.
The archive's presence was independently checked after execution. Keep this
recovery copy through API rollout; no deletion or off-device copy occurred.
It does not include object-storage file bytes, cloud configuration or role passwords.

## Exact SQL execution

Source: `4208c76d5dad71a923b8de2991ff5677e391b8e8`; latest fetched main
`7185ec1ede40c94a39ae132808832dcb9755f108` has no migration-source differences.
Ten fresh read-only prerequisite checks passed immediately before execution,
including approved subscription prices and exact 60-day function definitions.
All eight proposed tables and five proposed trigger functions were absent.

Each file was applied once with psql --single-transaction -v ON_ERROR_STOP=1,
retaining its lock/statement timeouts. No retry, timeout extension or bypass ran.

| SQL | SHA-256 | Transaction seconds | Schema verified |
| --- | --- | ---: | --- |
| 0053_salon_payout_requests | 4dbf6c1d2a9e95ceb58516053b4931cd5b99a3053c059363f4b8b40fc6d92d87 | 1.114 | yes |
| 0054_staff_earnings | 0fda5efee0541a981012d015d5ab22850b7e31ff3340f2d0ef350374097817b5 | 2.023 | yes |
| 0055_feature_access | 610b70113ba1e48044e532588d28b51e8f800f87d0e5adf95aeeecef302d1f42 | 1.233 | yes |

After each commit, production columns, defaults, constraints, valid indexes,
trigger definitions, function definitions and RLS flags matched the isolated
result. Anon/authenticated table privileges were denied; service_role lacked
TRUNCATE. Feature seed counts matched: 10 catalog entries, 30 matrix cells,
2 plan-content rows. Production customer/booking/payment mutation requests were
not sent. No claim is made that live table fingerprints stayed static while
normal customer traffic continued; these SQL sources do not rewrite existing rows.

Structural verification hashes by migration:

- 0053: `ba08666120ca65b2b86abf58e08f79fbc2e146e99d9f39dab6afca61a87e8a52`
- 0054: `3f569aa6c8fac2b74b2f8652c4c90ef1f3763216125dc545043e4a9c00a21a87`
- 0055: `34258fb038bc0406db235c98200fc1445406ef87947ff5c4c43bbd5c9fddc589`

Alembic history remains `0052_booking_window_30_days`, as explicitly scoped.
No Alembic stamp, manual history update or upgrade head occurred. Do not rerun
0053–0055 based on that older history value; schema effects are already present.
Any future history adoption needs a separate reviewed procedure.

## API verification and next boundary

Both api.salones.in and apiv1.mudassirmhd.in returned HTTP 200 for health/ready,
health/db, health/redis and version. Health statuses were ok. Both reported
commit `6fefff404b148af4798105228418d96f03ad8e4c`. Cloud Run traffic remained
100% on `salon-api-production-ci-6fefff4-20261101`.

Latest-main Backend CI run 41334283559 succeeded for `7185ec1`. Its image is not
yet deployed. The automatic workflow's migration-source refusal remains intact;
database success alone does not change its source-baseline check. Next is a
separately reviewed compatibility/candidate release from the exact tested image,
then the established approval before traffic promotion. Do not disable guards.

Local execution receipt (contains no credential payloads):
`C:\Users\Lenovo\AppData\Local\SalonRecovery\production-sql-0053-0055-20261101\execution-receipt.json`.

No Cloud Run deployment, traffic/DNS/certificate change, runtime-secret change,
IAM/WIF change, automatic-deployment flag change, worker activation, commit or
push occurred in this SQL execution phase. Prior unrelated local changes remain.
