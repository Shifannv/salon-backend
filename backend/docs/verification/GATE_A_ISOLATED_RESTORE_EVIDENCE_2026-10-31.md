# Gate A — Isolated Restore Evidence
## Phase 3 Schema Rehearsal — 2026-10-31

> **⚠ SCHEMA REHEARSAL ONLY — FULL DATA RESTORE REHEARSAL REQUIRED**
> This document covers a schema-only rehearsal using `supabase db dump --schema public` with
> synthetic subscription prices. It does NOT constitute production-data Gate B evidence.
> A full backup (roles + schema + data) with real production data must be restored and all
> steps repeated before Gate B approval can be requested.

**Status: SCHEMA-ONLY GATE B MIGRATION REHEARSAL PASSED — PRODUCTION-DATA EVIDENCE INCOMPLETE**  
**Runner:** Shifan Nv / Claude Code  
**Date:** 2026-10-31  
**Docker container:** `salon_restore_test` (postgres:15, 127.0.0.1:15432)  

---

## Run metadata

| Field | Value |
|-------|-------|
| Date | 2026-10-31 |
| Runner | Shifan Nv |
| Restore database URL (host:port/db only, no credentials) | 127.0.0.1:15432/salon_restore |
| Source | `supabase db dump --schema public` (Supabase CLI 2.109.1, project wqjlgpnbiapcrlkxumcp) |
| MUMBAI_PROJECT_CONFIRM | wqjlgpnbiapcrlkxumcp |
| Harness version (git commit) | abdc5d2 (branch shifan) |
| Docker image | postgres:15 |
| Schema dump file | prod_schema.sql (4992 lines, scratchpad) |
| Schema dump errors | 0 errors after stubs (auth/extensions/roles) applied |

---

## Safety checks

- [x] RESTORE_DB_URL does NOT contain `db.wqjlgpnbiapcrlkxumcp.supabase.co`
- [x] RESTORE_DB_URL does NOT contain `.pooler.supabase.com`
- [x] Database was created fresh from a schema dump (not a live production copy)
- [x] `_validate_not_production()` passed without error (shown in harness output)
- [x] `MUMBAI_PROJECT_CONFIRM=wqjlgpnbiapcrlkxumcp` was set as an environment variable

---

## Production-equivalent state setup

The Docker DB was built to match production's current state:

1. Fresh `postgres:15` container (`salon_restore_test`, port 15432)
2. Mock stubs created: `auth` schema + `auth.users` table + `auth.uid/role/email/jwt()` functions
3. `extensions` schema created; `pgcrypto` installed in `extensions` schema (for `extensions.gen_random_bytes`)
4. Supabase roles created: `anon`, `authenticated`, `service_role`, `authenticator`
5. Production schema dump applied via `psql` stdin pipe (0 errors)
6. `subscription_plans` seeded with owner-approved production prices:
   - `growth_1m=499, growth_6m=2000, growth_12m=2999, premium_1m=599, premium_6m=2875, premium_12m=5032`
7. `alembic_version` left EMPTY (matches production)

Result: 45 tables, exact production column set, description/category columns present, valid_until present on salon_plan_prices.

---

## Phase: preflight

**Status: PASS**

| Check | Status | Notes |
|-------|--------|-------|
| empty_alembic_version | PASS | alembic_version was empty before Gate B |
| baseline_0040_tables | PASS | salons, profiles, bookings, services all present |
| fastapi_only_acl | PASS | No unexpected grants |

Evidence JSON: `RECONCILIATION_EVIDENCE_PREFLIGHT_20261031_054824.json`  
SHA256: `aaaa408b1473b43f051936051a89b56114a3cc29338a2ab5167c1d038214c45b`

---

## Phase: 0049-equivalence

**Status: PASS**

| Check | Status | Notes |
|-------|--------|-------|
| 0049_table_structure | PASS | salon_plan_prices has 7 columns incl. valid_until |
| 0049_primary_key | PASS | Primary key on (salon_id, plan_id) |
| 0049_subscription_plan_prices | PASS | growth_1m=499, growth_6m=2000, growth_12m=2999 |

Evidence JSON: `RECONCILIATION_EVIDENCE_0049-EQUIVALENCE_20261031_054830.json`  
SHA256: `f59419e41ad03bff69adc436e4bcac5bbe0e95b78f4b27799bae097d092c47fb`

### subscription_plans prices found

| Code | Expected | Found | Match |
|------|----------|-------|-------|
| growth_1m | 499.00 | 499.00 | YES |
| growth_6m | 2000.00 | 2000.00 | YES |
| growth_12m | 2999.00 | 2999.00 | YES |
| premium_6m | 2875.00 | 2875.00 | YES |
| premium_12m | 5032.00 | 5032.00 | YES |

---

## Gate B sequence executed on Docker DB

| Step | Action | Result |
|------|--------|--------|
| 1 | Stamp 0040 in alembic_version (INSERT) | OK |
| 2 | Apply 0041_salon_photo_limits.sql via psql | OK (LOCK TABLE outside transaction warns; DDL applied correctly) |
| 3 | Apply 0042_remove_business_category.sql | OK |
| 4 | Apply 0043_no_show_attendance_guards.sql | OK (functions/triggers only) |
| 5 | Apply 0044_versioned_checkout_policy.sql | OK (functions/triggers only) |
| 6 | Apply 0045_customer_booking_changes.sql | OK |
| 7 | Apply 0046_u08_financial_outcomes.sql | OK |
| 8 | Apply 0047_booking_audit_erasure.sql | OK |
| 9 | Apply 0048_support_billing_erasure.sql | OK |
| 10 | Stamp 0049 in alembic_version (UPDATE) | OK |
| 11 | Apply 0050_plan_price_valid_until.sql | OK (IF NOT EXISTS — idempotent) |
| 12 | Update alembic_version to 0050 | OK |

**Note on 0041 LOCK TABLE:** `SET LOCAL lock_timeout='5s'` and `LOCK TABLE` require a transaction block. When Alembic runs the SQL file (which splits on `-- statement --` and wraps each in a transaction), these work correctly. Verified separately: `LOCK TABLE` + `SET LOCAL` succeed inside `BEGIN/COMMIT` block (lock-timeout test below).

---

## Phase: post-0041-0048

**Status: PASS**

| Check | Status | Notes |
|-------|--------|-------|
| baseline_0040_tables | PASS | Core tables present |
| fastapi_only_acl | PASS | No unexpected grants |
| 0041_destructive_ddl | PASS | salons.description dropped; services.description dropped; t_salon_image_limits trigger created |
| 0042_destructive_ddl | PASS | salons.category dropped |

Evidence JSON: `RECONCILIATION_EVIDENCE_POST-0041-0048_20261031_054937.json`  
SHA256: `498d39ba9c76fe637b626516efea948d754f285e611d3a8284df560e0df0e24e`

---

## Phase: schema-check

**Status: PASS**

| Check | Status | Notes |
|-------|--------|-------|
| baseline_0040_tables | PASS | |
| fastapi_only_acl | PASS | |
| 0041_destructive_ddl | PASS | description cols dropped; trigger created |
| 0042_destructive_ddl | PASS | category col dropped |
| 0049_table_structure | PASS | |
| 0049_primary_key | PASS | |
| 0049_subscription_plan_prices | PASS | 499/2000/2999 confirmed |

Evidence JSON: `RECONCILIATION_EVIDENCE_SCHEMA-CHECK_20261031_054945.json`  
SHA256: `39d001b55f9c8f7e9490f041bc827ffcf0788d8ea33557d5543e694cf4c1b25e`

---

## Phase: post-0050

**Status: PASS**

| Check | Status | Notes |
|-------|--------|-------|
| 0050_valid_until_column | PASS | valid_until timestamptz column exists on salon_plan_prices |

Evidence JSON: `RECONCILIATION_EVIDENCE_POST-0050_20261031_054946.json`  
SHA256: `60deb636aa6904c3aae82abe60a263530d1cdab2dd0bf62466834821ce55a739`

---

## Phase: post-gate-b

**Status: PASS (all 9 checks)**

| Check | Status |
|-------|--------|
| alembic_version_at (0050) | PASS |
| baseline_0040_tables | PASS |
| fastapi_only_acl | PASS |
| 0041_destructive_ddl | PASS |
| 0042_destructive_ddl | PASS |
| 0049_table_structure | PASS |
| 0049_primary_key | PASS |
| 0049_subscription_plan_prices | PASS |
| 0050_valid_until_column | PASS |

Evidence JSON: `RECONCILIATION_EVIDENCE_POST-GATE-B_20261031_054946.json`  
SHA256: `ee79eb931322e33ea50ec9719845cd8a41aa21575a33dd920e68ffd3699f2bd0`

---

## Phase: report

**Status: FAIL (expected — Gate B complete, Gate C not run)**

| Check | Status | Notes |
|-------|--------|-------|
| empty_alembic_version | FAIL | EXPECTED — alembic_version = 0050 after Gate B |
| baseline_0040_tables | PASS | |
| fastapi_only_acl | PASS | |
| 0041_destructive_ddl | PASS | |
| 0042_destructive_ddl | PASS | |
| 0049_table_structure | PASS | |
| 0049_primary_key | PASS | |
| 0049_subscription_plan_prices | PASS | |
| 0050_valid_until_column | PASS | |
| 0051_finance_schema | FAIL | EXPECTED — 0051 not applied (Gate C blocked) |
| 0052_booking_window_function | WARN | EXPECTED — 0052 not applied (Gate C blocked) |

The `report` phase FAIL is expected: it checks state that changes across the full lifecycle.  
Gate B verification is captured by `post-gate-b` (all PASS).

Evidence JSON: `RECONCILIATION_EVIDENCE_REPORT_20261031_054952.json`  
SHA256: `f952db2e8da227e0a2115b884b29152d9e35f2598e73263097aca4a1b3e971b3`

---

## Lock-timeout test (step 10)

Verified that `SET LOCAL lock_timeout='5s'` and `LOCK TABLE ... IN ACCESS EXCLUSIVE MODE` work
correctly inside a transaction block (as Alembic runs them):

```
BEGIN;
SET LOCAL lock_timeout = '5s';
LOCK TABLE public.salons IN ACCESS EXCLUSIVE MODE;
→ LOCK TABLE (acquired successfully)
ROLLBACK;
```

**Result: PASS** — lock-timeout behavior is correct when executed in transaction context.

---

## Backend test suite (step 11)

Run: `python -m pytest -q --tb=no -x` against Docker-based backend  
**Result: 1840 passed, 295 skipped, 1 warning — EXIT 0**

---

## Rollback rehearsal (step 12)

Procedure tested:
1. Create fresh `salon_restore_rollback_test` database
2. Apply Supabase mock stubs (auth, extensions, roles)
3. Apply `prod_schema.sql` via psql stdin pipe
4. Verify: `alembic_version` empty, `salons.description` present, 45 tables

**Result: PASS** — rollback restores DB to pre-Gate-B production state correctly.  
Rollback path: restore from backup → DO NOT use `alembic downgrade` (irreversible DDL).

---

## Gate C assessment (step 13)

### 0051 (owner_finance_cashbook)
- **Type:** Additive — 4 new tables, no existing table/column changes
- **Client dependency:** Owner app must be deployed to USE the new tables
- **Regression risk:** None (new tables don't affect existing queries)
- **Verdict:** CAN be applied before client deployment but no value without it
- **Gate C status:** BLOCKED until owner app deployment confirmed

### 0052 (booking_window_30_days)
- **Type:** Behavioral replacement — `get_available_slots()` replaced with 30-day window guard
- **Client dependency:** Customer app, walk-in QR, owner app — all callers of `get_available_slots()`
- **Regression risk:** HIGH — availability outside 30 days returns empty slots; existing clients would show "no availability" for dates >30 days
- **Verdict:** REQUIRES confirmed client deployment before applying
- **Gate C status:** GATE C BLOCKER — client app update + deployment confirmation required

---

## alembic current after each migration step

| Step | Expected revision | Actual | Match |
|------|-------------------|--------|-------|
| After 0040 stamp | 0040_fastapi_only_access | 0040_fastapi_only_access | YES |
| After 0041 | 0041_salon_photo_limits | 0041_salon_photo_limits | YES |
| After 0042 | 0042_remove_business_category | 0042_remove_business_category | YES |
| After 0043 | 0043_no_show_attendance_guards | 0043_no_show_attendance_guards | YES |
| After 0044 | 0044_versioned_checkout_policy | 0044_versioned_checkout_policy | YES |
| After 0045 | 0045_customer_booking_changes | 0045_customer_booking_changes | YES |
| After 0046 | 0046_u08_financial_outcomes | 0046_u08_financial_outcomes | YES |
| After 0047 | 0047_booking_audit_erasure | 0047_booking_audit_erasure | YES |
| After 0048 | 0048_support_billing_erasure | 0048_support_billing_erasure | YES |
| After 0049 stamp | 0049_trial_salon_plan_prices | 0049_trial_salon_plan_prices | YES |
| After 0050 | 0050_plan_price_valid_until | 0050_plan_price_valid_until | YES |

---

## Destructive DDL confirmation

| Rev | Irreversible action | Verified in Docker |
|-----|---------------------|-------------------|
| 0041 | `DROP COLUMN salons.description`, `DROP COLUMN services.description` | CONFIRMED DROPPED |
| 0042 | `DROP COLUMN salons.category` | CONFIRMED DROPPED |
| 0049 | Price updates in subscription_plans (guarded) | PRICES AT 499/2000/2999 — GUARDS NOT FIRED |
| 0052 | get_available_slots replaced | NOT APPLIED (Gate C) |

- [x] Confirmed: production `salons.description` and `services.description` columns exist pre-0041; DROP is safe once client apps updated
- [x] Confirmed: production `salons.category` column exists pre-0042; DROP is safe once client apps updated
- [ ] **PENDING**: Confirmation that ALL client apps (customer, owner, walk-in QR) have been deployed without reading `description` or `category`
- [x] Confirmed: maintenance window / write-freeze approach documented (PRODUCTION_MIGRATION_EXECUTION_RUNBOOK.md §Option 1)

---

## Summary: SCHEMA REHEARSAL PASSED — FULL DATA RESTORE REHEARSAL REQUIRED

All harness phases passed against a schema-only Docker restore with synthetic subscription prices.
This is NOT sufficient Gate B evidence.

**What is still required before Gate B approval can be requested:**
1. Full backup: roles dump + schema dump + data dump, all encrypted
2. Real production data restored (not synthetic prices — actual subscription_plans rows)
3. Table count reconciliation (45 public restored vs production count)
4. Real row counts, fingerprints, financial totals verified
5. All harness phases repeated against the full-data restore
6. Full backend suite against full-data restore
7. Rollback rehearsal with timing and verification

**Gate B MUST NOT proceed until the full data restore rehearsal passes.**

---

## Reviewer sign-off

| Field | Value |
|-------|-------|
| Reviewer | |
| Date reviewed | |
| All harness phases completed | NO — schema-only rehearsal only |
| Decision | PENDING full data restore rehearsal |
| Notes | See GATE_A_ISOLATED_RESTORE_EVIDENCE_FULL_DATA_2026-10-31.md when complete |
