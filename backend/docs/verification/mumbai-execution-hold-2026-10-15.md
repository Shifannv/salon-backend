# Mumbai execution preflight and hold

Destination: wqjlgpnbiapcrlkxumcp, Mumbai/ap-south-1. Current instruction: keep 0038, 0039 and 0040 uncommitted and unapplied. No Alembic stamp, production/environment/infra change or frontend source change occurred. Sydney was not accessed.

## Passed

- Verified destination and empty public.alembic_version. Supabase's separate migration history still has four earlier restore/hardening entries; none is 0038–0040.
- Dependency chain: 0037_customer_processing_charge → 0038_cancellation_compatibility → 0039_promotion_search_path → 0040_fastapi_only_access (prepared repository head).
- Created two schema-only backups with pg_dump; verified checksums, 2,502 top-level statements and no data COPY/INSERT statements. Passwords were supplied only in process memory. Native libpq used TLS verify-full.
- Corrected exact 0038–0040 SQL passed a BEGIN/ROLLBACK preflight. Catalog, effective/raw ACL-related metadata, default privileges, memberships, history and selected record counts matched the preflight fingerprint after rollback. See root migration-mumbai-execution-preflight-2026-10-15.json.
- Both cancellation columns remain nullable text without defaults. Client effective SELECT remains denied on audited application tables; this is expected, not a failed RLS test.
- Existing frontend mocked tests: 22 passed across six suites. They establish hook/polling behavior under mocks, not live staging compatibility.

## Backup evidence

| Backup directory under supabase-schema-backup | Schema SHA256 |
| --- | --- |
| mumbai-pre-0038-0040-20261015T130916Z | 61f5ab35537a97cf5aa1cbdcad5779b1a0ea2b6f6b8e8ef15df5667bd4abe0d8 |
| mumbai-pre-0038-0040-20261015T131523Z | 3b814ec1cb652b0ea7f12ec7d8a942ebf661d562eb86e437dd458296d6eb8286 |

Each backup directory includes verification.json and SHA256SUMS. Both normalized schema dumps have SHA256 d74f65e66de0af745fd62d70a456715c8117e8c1649048cd594a93f862492731 after excluding only random pg_dump restrict/unrestrict tokens. This independently verifies no schema drift from the failed preflight. These are schema-only backups, not data recovery snapshots.

## Commands run (secrets omitted)

Local scripts:

```powershell
backend/.venv/Scripts/python.exe -m backend.scripts.migrations.migration_mumbai_execution_preflight_20261015
backend/.venv/Scripts/python.exe -m backend.scripts.migrations.migration_mumbai_sql_preflight_20261015
```

The scripts invoke the following native operations with guarded Mumbai target and process-only credentials:

```text
pg_dump --schema-only --no-password --quote-all-identifiers --lock-wait-timeout=5s --host aws-0-ap-south-1.pooler.supabase.com --port 5432 --username postgres.wqjlgpnbiapcrlkxumcp --dbname postgres --file <verified backup directory>/schema.sql
psql --no-psqlrc --no-password --host aws-0-ap-south-1.pooler.supabase.com --port 5432 --username postgres.wqjlgpnbiapcrlkxumcp --dbname postgres --file <verified backup directory>/rollback-preflight.sql
```

Jest ran in the existing frontend checkouts using node node_modules/jest/bin/jest.js, --runInBand, --no-cache, --runTestsByPath and JSON output to this backend workspace; BABEL_DISABLE_CACHE=1 and EXPO_NO_DOTENV=1. Customer selected realtime.service.test.ts and bookings.test.tsx. Owner logic project selected operational-polling.test.ts, useRealtimeSync.test.ts, useBookings.test.ts, then useQueryLifecycle.test.ts. Full selected paths and outputs are represented in the root test JSON artifacts. No install, build, deployment or production API request was needed.

## Failed, corrected and blocked

First preflights failed in 0040's final PL/pgSQL DO assertion: an unparenthesized CASE within IF caused a syntax error at end of input. Parenthesizing the expression fixed parsing without changing the intended privilege predicate. Exact SQL preflight then passed. Source before/after hashes: migration-mumbai-0040-syntax-fix-2026-10-15.json. Failed sessions rolled back; independent schema comparison also matched. The superseded standalone security draft received the same syntax correction; it is not an additional migration to apply.

No post-application checks can be claimed because no application happened. The earlier rollback runtime exercise recorded 57 passes and two direct-RLS cases not applicable under FastAPI-only access; it covered service/FastAPI booking, availability, collection, audit, fake-provider worker and scoped customer/owner erasure. Those artifacts are historical preflight evidence, not tests of a committed 0040 deployment or of native/browser refresh. Real JWT and deployment binding were outside the injected-actor ASGI exercise.

Frontend staging refresh is blocked: local source has customer fallback gaps and owner availability/cross-cache gaps, and the exact Mumbai customer/owner deployed build/API bindings are unverified. No grants were added to fix this. See the companion audit and designs.

## Schema and Alembic result

Both extra cancellation fields are preserved. Prepared 0038 documents them without dropping values or changing nullability; 0039 pins the existing promotion helper's search_path; 0040 revokes client application rights while asserting retained server rights. Scope excludes Auth/Storage managed privileges and extension functions. No signup trigger replacement is proposed.

Earlier review compared all 37 historical source revisions' final effects against Mumbai and preserved their source hashes; it did not replay historical data backfills. The baseline is 0001_baseline executing 001_supabase_schema.sql. Empty Alembic history reflects a schema restore, not a safe instruction to replay all historical upgrades.

Exact equality to a clean expected 0040 schema/effective ACL reference is not proven. No stamp command is proposed. Safe next action is resolve and stage-test refresh, then reproduce a clean expected head and compare columns, types/defaults/nullability, constraints, indexes, functions/security/search_path, triggers, grants/default ACLs, RLS and extensions with version-normalized differences. Resolve every unexplained difference. Only then review a Mumbai-specific history reconciliation/stamp operation separately; no history writes now.

## Rollback and remaining approval

Rollback-only SQL preflight is complete and verified. There is no committed migration to undo. Do not restore the schema backup over Mumbai or replay grants as cleanup. Prepared downgrades deliberately refuse destructive reversal: preserve columns/security and use reviewed forward repairs. Erased personal values must never be restored. Adapter rollback must retain the new scrub behavior or suspend erasure processing.

Account-erasure classification still has 43 older text/JSON gaps beyond the two newly classified cancellation fields. Their exact names follow below; a passing targeted erasure scenario does not close them. They remain a release risk.

Next approval must select and authorize refresh implementation (recommended FastAPI-only polling/invalidation), followed by isolated Mumbai staging acceptance tests. Migration execution approval remains separate and conditional on that gate. No production deployment, traffic switch or Alembic stamp is included.

## Remaining classification gaps (43)

- `api_rate_limits.bucket_hash`
- `booking_audit_events.event_type`
- `booking_audit_events.new_state`
- `booking_audit_events.old_state`
- `booking_payments.collection_method`
- `booking_payments.commission_base`
- `booking_payments.commission_policy_version`
- `booking_payments.provider_session_id`
- `bookings.checkout_policy_version`
- `email_events.body`
- `email_events.event_key`
- `email_events.event_type`
- `email_events.last_error_code`
- `email_events.provider_message_id`
- `email_events.recipient`
- `email_events.status`
- `email_events.subject`
- `payment_anomalies.detail`
- `payment_anomalies.kind`
- `payment_anomalies.provider`
- `payment_anomalies.provider_ref`
- `payment_provider_account_audit.action`
- `payment_provider_account_audit.detail`
- `payment_provider_account_audit.new_status`
- `payment_provider_account_audit.previous_status`
- `payment_provider_account_audit.provider`
- `payment_provider_account_audit.vendor_ref`
- `payment_refunds.kind`
- `salon_access.trial_ended_reason`
- `subscription_billing_records.benefits`
- `subscription_billing_records.billing_interval`
- `subscription_billing_records.currency`
- `subscription_billing_records.failure_code`
- `subscription_billing_records.plan_code`
- `subscription_billing_records.provider`
- `subscription_billing_records.provider_order_ref`
- `subscription_billing_records.provider_payment_ref`
- `subscription_billing_records.receipt`
- `subscription_billing_records.status`
- `subscription_plans.features`
- `support_messages.body`
- `support_tickets.status`
- `support_tickets.subject`
