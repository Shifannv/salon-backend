# Isolated Restore Evidence Template

> **⚠ UNVERIFIED — The reconciliation harness has not yet been run against a real restored PostgreSQL database.**
> This template is a blank form. No evidence has been collected. Skipped or unrun integration tests
> are NOT evidence and cannot be presented as verification. Fill every section only after running
> the harness against an actual restore of the production backup.

**Purpose:** Record the evidence from an isolated PostgreSQL restore test.  
Fill this out for each restore test run before preparing a stamp or migration approval manifest.

---

## Phase 3 — Docker prerequisites (complete before filling evidence below)

Before running the harness, the following must be completed. This is a Phase 3 gate.

### 1. Download a fresh Supabase backup

```bash
# In Supabase dashboard → Mumbai project → Database → Backups
# Download the latest backup (pg_dump format).
# Encrypt the file before storing:
gpg --symmetric --cipher-algo AES256 supabase_backup_<date>.dump
# Store only the encrypted file; delete the plaintext immediately.
```

### 2. Start a local Docker PostgreSQL

```bash
docker run -d --name salon_restore_test \
  -e POSTGRES_PASSWORD=localtest \
  -e POSTGRES_DB=salon_restore \
  -p 5432:5432 \
  postgres:15
```

### 3. Restore the backup into Docker

```bash
# Decrypt and restore:
gpg --decrypt supabase_backup_<date>.dump.gpg | \
  pg_restore -h 127.0.0.1 -U postgres -d salon_restore --no-privileges --no-owner
```

### 4. Set harness environment variables

```bash
export RESTORE_DB_URL="postgresql+asyncpg://postgres:localtest@127.0.0.1:5432/salon_restore"
export MUMBAI_PROJECT_CONFIRM="wqjlgpnbiapcrlkxumcp"
```

### 5. Run harness phases in sequence

```bash
cd backend/
python -m scripts.migrations.reconciliation_harness --phase preflight
python -m scripts.migrations.reconciliation_harness --phase 0049-equivalence
# (stamp 0040, upgrade 0041-0048, stamp 0049, upgrade 0050 on the Docker DB)
python -m scripts.migrations.reconciliation_harness --phase post-0041-0048
python -m scripts.migrations.reconciliation_harness --phase schema-check
python -m scripts.migrations.reconciliation_harness --phase post-0050
python -m scripts.migrations.reconciliation_harness --phase post-gate-b
python -m scripts.migrations.reconciliation_harness --phase report
```

### Prerequisites checklist

- [ ] Docker is running and `postgres:15` container is up
- [ ] Supabase backup downloaded, encrypted, and plaintext deleted
- [ ] Restore completed without fatal errors
- [ ] `alembic_version` table exists and is empty (confirmed by preflight PASS)
- [ ] No production credentials in any env variable or shell history

---

## Run metadata

| Field | Value |
|-------|-------|
| Date | |
| Runner | |
| Restore database URL (host:port/db only, no credentials) | |
| Source backup ref | |
| MUMBAI_PROJECT_CONFIRM | wqjlgpnbiapcrlkxumcp |
| Harness version (git commit) | |

---

## Safety checks (must all be confirmed before running harness)

- [ ] RESTORE_DB_URL does NOT contain `db.wqjlgpnbiapcrlkxumcp.supabase.co`
- [ ] RESTORE_DB_URL does NOT contain `.pooler.supabase.com`
- [ ] Database was created fresh from a backup (not a live production copy)
- [ ] `_validate_not_production()` passed without error (shown in harness output)
- [ ] `MUMBAI_PROJECT_CONFIRM=wqjlgpnbiapcrlkxumcp` was set as an environment variable (not just typed here)

---

## Phase: preflight

> Status before this section is filled in: **NOT RUN**

Run: `python -m scripts.migrations.reconciliation_harness --phase preflight`

| Check | Status | Notes |
|-------|--------|-------|
| empty_alembic_version | | |
| baseline_0040_tables | | |
| fastapi_only_acl | | |

Evidence JSON file: `RECONCILIATION_EVIDENCE_PREFLIGHT_<timestamp>.json`  
SHA256 of evidence file:  
_(paste sha256sum output here)_

---

## Phase: 0049-equivalence

> Status before this section is filled in: **NOT RUN**

Run: `python -m scripts.migrations.reconciliation_harness --phase 0049-equivalence`

| Check | Status | Notes |
|-------|--------|-------|
| 0049_table_structure | | |
| 0049_primary_key | | |
| 0049_subscription_plan_prices | | |

Evidence JSON file: `RECONCILIATION_EVIDENCE_0049-EQUIVALENCE_<timestamp>.json`  
SHA256 of evidence file:

### salon_plan_prices columns found

```
(paste harness output here — do not fill in from memory or the migration file)
```

### subscription_plans prices found

| Code | Expected | Found | Match |
|------|----------|-------|-------|
| growth_1m | 499.00 | | |
| growth_6m | 2000.00 | | |
| growth_12m | 2999.00 | | |
| premium_6m | 2875.00 | | |
| premium_12m | 5032.00 | | |

---

## Phase: post-0041-0048 (optional mid-sequence check)

> Status before this section is filled in: **NOT RUN**

Run: `python -m scripts.migrations.reconciliation_harness --phase post-0041-0048`

| Check | Status | Notes |
|-------|--------|-------|
| baseline_0040_tables | | |
| fastapi_only_acl | | |
| 0041_destructive_ddl | | Verifies description cols dropped; t_salon_image_limits trigger created |
| 0042_destructive_ddl | | Verifies salons.category col dropped |

---

## Phase: schema-check (post 0041-0048)

> Status before this section is filled in: **NOT RUN**

Run: `python -m scripts.migrations.reconciliation_harness --phase schema-check`

| Check | Status | Notes |
|-------|--------|-------|
| baseline_0040_tables | | |
| fastapi_only_acl | | |
| 0041_destructive_ddl | | Verifies description cols dropped; t_salon_image_limits trigger created |
| 0042_destructive_ddl | | Verifies salons.category col dropped |
| 0049_table_structure | | |
| 0049_primary_key | | |
| 0049_subscription_plan_prices | | |

---

## Phase: post-0050

> Status before this section is filled in: **NOT RUN**

Run: `python -m scripts.migrations.reconciliation_harness --phase post-0050`

| Check | Status | Notes |
|-------|--------|-------|
| 0050_valid_until_column | | |

---

## Phase: post-0051 (Gate C only — not part of Gate B)

> Status before this section is filled in: **NOT RUN**

Run: `python -m scripts.migrations.reconciliation_harness --phase post-0051`

| Check | Status | Notes |
|-------|--------|-------|
| 0051_finance_schema | | |

Finance tables found:
- [ ] salon_expenses
- [ ] salon_cash_adjustments
- [ ] salon_day_close
- [ ] salon_expense_rules

---

## Phase: post-0052 (Gate C only — not part of Gate B)

> Status before this section is filled in: **NOT RUN**

Run: `python -m scripts.migrations.reconciliation_harness --phase post-0052`

| Check | Status | Notes |
|-------|--------|-------|
| 0052_booking_window_function | | |

get_available_slots function: exists / 30-day guard present?

---

## Stamp manifest inputs

> **Do not fill in hashes manually.** Run the harness and paste its output verbatim.
> Hashes computed without running the harness are NOT valid evidence.

Run: `python -m scripts.migrations.reconciliation_harness --phase stamp-inputs --stamp-target <target>`

### For 0040_fastapi_only_access

```
(paste harness output here)
migration_policy.py  : <hash>
<0040-revision>.py   : <hash>
0040_fastapi_only_access.sql : <hash>
```

### For 0049_trial_salon_plan_prices (if applicable)

```
(paste harness output here)
migration_policy.py  : <hash>
<0049-revision>.py   : <hash>
0049_trial_salon_plan_prices.sql : <hash>
```

---

## alembic current after each migration step

> Fill this in from actual `alembic current` output during the restore test — not from memory.

| Step | Expected revision | Actual | Match |
|------|-------------------|--------|-------|
| After 0040 stamp | 0040_fastapi_only_access | | |
| After 0041 | 0041_salon_photo_limits | | |
| After 0042 | 0042_remove_business_category | | |
| After 0043 | 0043_no_show_attendance_guards | | |
| After 0044 | 0044_versioned_checkout_policy | | |
| After 0045 | 0045_customer_booking_changes | | |
| After 0046 | 0046_u08_financial_outcomes | | |
| After 0047 | 0047_booking_audit_erasure | | |
| After 0048 | 0048_support_billing_erasure | | |
| After 0049 stamp | 0049_trial_salon_plan_prices | | |
| After 0050 | 0050_plan_price_valid_until | | |

---

## Rollback test

- [ ] Backup restored to a fresh database
- [ ] `alembic current` shows expected state after restore
- [ ] Core API tables accessible (salons, bookings, services, profiles)
- [ ] Restore took __ minutes

---

## Destructive DDL reminder

Before signing off, confirm awareness of permanent changes in this bundle:

| Rev | Irreversible action |
|-----|---------------------|
| 0041 | `DROP COLUMN salons.description`, `DROP COLUMN services.description` |
| 0042 | `DROP COLUMN salons.category` |
| 0049 | Price updates in subscription_plans (guarded but permanent if guards fired) |
| 0052 | get_available_slots replaced — behavioral change, no schema rollback |

- [ ] Confirmed: production `salons.description` and `services.description` columns are not used by any client after the client app updates ship.
- [ ] Confirmed: production `salons.category` column is not used by any client.
- [ ] Confirmed: maintenance window or write-freeze approach is chosen.

---

## Reviewer sign-off

> This section is only valid after ALL harness phases above are filled in with actual output.
> A blank or partially filled template cannot be signed off.

| Field | Value |
|-------|-------|
| Reviewer | |
| Date reviewed | |
| All harness phases completed | YES / NO |
| Decision | APPROVED / REJECTED |
| Notes | |
