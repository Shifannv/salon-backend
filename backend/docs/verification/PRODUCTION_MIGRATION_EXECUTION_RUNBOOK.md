# Production Migration Execution Runbook

**Project:** Salones backend — Mumbai (wqjlgpnbiapcrlkxumcp)  
**Status:** Phase 1 local preparation complete. Production execution NOT YET AUTHORIZED.  
**Last updated:** 2026-10-30  
**Harness status:** UNVERIFIED — no isolated restore has been run yet against a real PostgreSQL restore.

---

## Destructive and data-impact table for 0041–0052

Read this before authorizing any gate. The original claim that "0041–0048 are additive" was incorrect.

| Rev | DDL impact | Data impact | Rollback limit |
|-----|-----------|-------------|----------------|
| **0041** | `DROP COLUMN salons.description`; `DROP COLUMN services.description`; new trigger `t_salon_image_limits`; replaces `get_salon_by_qr` (description→NULL) | **DESTRUCTIVE.** Column data permanently lost. Soft-deletes excess/duplicate salon_images (sets `is_active=false`). | No undo. Backup restore only. |
| **0042** | `DROP COLUMN IF EXISTS salons.category RESTRICT` | **DESTRUCTIVE.** Category data permanently lost if column existed. | No undo. Backup restore only. |
| **0043** | New trigger `booking_no_show_attendance_guard` on bookings UPDATE | None. | Trigger can be dropped to revert behavior. |
| **0044** | New function `stamp_checkout_policy` (trigger not yet attached) | None. | Function can be dropped. |
| **0045** | New columns on `bookings` (change_version, committed_reschedules, service_fulfilment_amount); new column `booking_services.is_active`; new table `booking_customer_changes`; new overload of `get_available_slots` | Existing booking rows get `change_version=0`, `committed_reschedules=0`, `is_active=true` via DEFAULT. | New columns can be dropped if no rows written. |
| **0046** | New tables `booking_financial_outcomes`, `booking_finance_commands`, `booking_policy_refund_jobs`, `booking_finance_reconciliations`; AFTER UPDATE trigger on bookings fires for u08-policy bookings only | None for existing customer_processing_v1 bookings. New trigger fires only on u08-2026-10-23-v1 policy bookings. | New tables can be dropped if no rows written. |
| **0047** | New `anonymized_at` columns on `booking_customer_changes` and `booking_finance_commands`; replaces `guard_booking_change_history` to permit erasure | None. | Columns can be dropped if no rows written. |
| **0048** | `support_tickets.customer_id` made nullable; new constraint `support_customer_or_retained`; new `retained_restricted` and erasure columns; new table `support_erasure_events`; new columns on `subscription_billing_records`; replaces `tg_subscription_billing_guard` | None. Constraint validation runs online (VALIDATE CONSTRAINT). | Additive columns can be dropped; nullable change cannot be reversed without a NOT VALID constraint. |
| **0049** | New table `salon_plan_prices` (no IF NOT EXISTS — FAILS if table exists); replaces `start_salon_trial` (60 days/500 bookings); `salon_access.trial_booking_limit` default changed to 500 | **DATA UPDATE** (guarded): updates 4 `subscription_plans` prices only if still at 0031 seed values. | salon_plan_prices can be dropped if empty; price updates are permanent if guards fired. |
| **0050** | `ALTER TABLE salon_plan_prices ADD COLUMN IF NOT EXISTS valid_until timestamptz` | None. Idempotent. | Column can be dropped. |
| **0051** | New tables: `salon_expenses`, `salon_cash_adjustments`, `salon_day_closes`, `salon_expense_rules` | None. Fully additive. | Tables can be dropped if empty. |
| **0052** | Replaces `get_available_slots` with 30-day booking window; new guard inside `create_booking` | Behavioral change: slots >30 days out become invisible to customers. | No schema rollback; function replacement is forward-only. |

### 0041 locking risk

0041 acquires `ACCESS EXCLUSIVE MODE` on `salons`, `services`, and `salon_images` with `lock_timeout = '5s'`. Under production write traffic this will:
- Fail immediately if a long-running query or idle transaction holds a conflicting lock.
- Block all new reads and writes on those tables while the lock is held.

**Requirement:** low-traffic window or explicit write freeze before this migration.

### 0052 client compatibility risk

The 30-day booking window is a **visible behavior change**. The customer app must not show slots it can no longer book. Deploying 0052 before a compatible customer app version causes a visible gap between displayed and bookable slots.

---

## Rollback strategy (corrected)

**Restore-from-backup is not harmless.** After production writes resume post-stamp, a restore loses:
- New bookings, cancellations, and financial records written after the backup point.
- Any owner profile or preference updates.
- Any payment events and webhook callbacks.

Three options — choose one before authorizing production execution:

### Option 1: Maintenance window + write freeze (recommended for first release)

1. Announce a maintenance window (e.g., 02:00–04:00 IST).
2. Cloud Run: set minimum instances to 0 or deploy a "503 maintenance" image.
3. Verify zero active connections to the database.
4. Take backup.
5. Execute migrations.
6. Re-enable Cloud Run.
7. If any migration fails, restore from backup (data loss is bounded to the maintenance window only).

**Requires:** separate Cloud Run maintenance-mode deployment approval (not authorized here).

### Option 2: Point-in-time recovery (PITR)

Use Supabase's PITR to recover to the moment just before a failed step.  
- Supabase PITR retention must be confirmed as active on this project before selecting this option.
- Recovery time: typically 15–30 minutes.
- Data loss: zero for completed transactions.

**Requires:** confirming PITR is enabled (owner to verify in Supabase dashboard).

### Option 3: Forward-only repair only

Accept that rollback is not available. If a migration partially fails, write a corrective migration. This is viable only for the additive migrations (0043–0048, 0050, 0051) but NOT for the destructive ones (0041, 0042, 0049 price updates, 0052 behavior change).

**For this release:** Option 1 (maintenance window) is required because 0041, 0042 are destructive.

---

## Three-gate approval model

Replace per-migration approvals with three explicit gates.

### Gate A — backup + isolated restore test (required before any production step)

**Not authorized yet.** Owner authorizes after all items pass:

- [ ] Production backup created and download verified.
- [ ] Isolated restore harness run against backup copy on local/scratch PostgreSQL.
- [ ] All harness phases (preflight, 0049-equivalence, schema-check) return PASS.
- [ ] JSON evidence reports saved with SHA256 hashes.
- [ ] Rollback test: backup restored to a second local database, core API tables accessible.
- [ ] PITR status confirmed (or maintenance window approach chosen).

**Gate A approval:** owner signs `gate_a_approval.json` (same manifest format as stamp approval, target_revision = "gate_a").

### Gate B — 0040→0050 production sequence

**Not authorized until Gate A is approved.** Owner authorizes one signed manifest covering:

- Exact stop conditions for every revision (see below).
- SHA256 hashes of all revision .py and .sql files to be run.
- Evidence file references from Gate A.
- Maintenance window or write-freeze confirmation.
- Reviewer sign-off.

**Gate B execution (all in one supervised session, NOT authorized yet):**

1. Start maintenance window / write freeze.
2. Take final production backup.
3. Stamp 0040 (alembic_version empty → 0040_fastapi_only_access).
4. Upgrade 0041 through 0048 in order (one alembic upgrade command per step).
5. Verify 0049 equivalence check (harness), then stamp 0049.
6. Upgrade 0050.
7. Verify with `alembic current`, harness schema-check, and API smoke test.
8. End maintenance window / re-enable writes.

**Gate B approval:** owner signs `gate_b_approval.json`.

### Gate C — 0051/0052 + AUTO_DEPLOY_ENABLED

**Not authorized until Gate B is complete and API smoke test passes.** Requires:

- [ ] Finance API endpoints deployed and tested.
- [ ] Owner app on a version that shows the finance tab.
- [ ] Customer app on a version that handles the 30-day booking window.
- [ ] Separate sign-off on 0052 client compatibility.
- [ ] Gate B fully complete with no incidents.
- [ ] Explicit owner approval to set `AUTO_DEPLOY_ENABLED=true`.

---

## Stop conditions for 0040→0050 sequence

Each condition must be checked before the next step.

| After | alembic current must show | Stop if |
|-------|--------------------------|---------|
| 0040 stamp | `0040_fastapi_only_access` | Any other revision shown |
| 0041 upgrade | `0041_salon_photo_limits` | Any error, lock timeout, or unexpected revision |
| 0042 upgrade | `0042_remove_business_category` | Any error, lock timeout, or unexpected revision |
| 0043 upgrade | `0043_no_show_attendance_guards` | Any error |
| 0044 upgrade | `0044_versioned_checkout_policy` | Any error |
| 0045 upgrade | `0045_customer_booking_changes` | Any error |
| 0046 upgrade | `0046_u08_financial_outcomes` | Any error |
| 0047 upgrade | `0047_booking_audit_erasure` | Any error |
| 0048 upgrade | `0048_support_billing_erasure` | Any error; confirm VALIDATE CONSTRAINT passed |
| 0049 equivalence | harness 0049-equivalence PASS | Any FAIL in table structure or prices |
| 0049 stamp | `0049_trial_salon_plan_prices` | Any other revision shown |
| 0050 upgrade | `0050_plan_price_valid_until` | Any error |
| Post-0050 | harness schema-check PASS | Any FAIL |

**Any stop condition triggered → do not continue. Assess whether the maintenance window allows a restore or forward repair. Escalate before any further action.**

---

## Exact production commands (Gate B session, NOT AUTHORIZED YET)

```bash
# These commands require DATABASE_URL set to the production URL, Gate B manifest present,
# and maintenance window active. NOT AUTHORIZED until Gate B is signed.

export DATABASE_URL="postgresql+asyncpg://postgres:<pw>@db.wqjlgpnbiapcrlkxumcp.supabase.co:5432/postgres"

# Step: stamp baseline
python -m alembic \
  -x mumbai_project=wqjlgpnbiapcrlkxumcp \
  -x approval_manifest=manifests/gate_b_stamp_0040.json \
  -x approval_id=<gate-b-id> \
  stamp 0040_fastapi_only_access
python -m alembic current   # must show 0040_fastapi_only_access

# Steps 0041-0048: one per upgrade (same -x options, incrementing target)
for REVISION in \
  0041_salon_photo_limits \
  0042_remove_business_category \
  0043_no_show_attendance_guards \
  0044_versioned_checkout_policy \
  0045_customer_booking_changes \
  0046_u08_financial_outcomes \
  0047_booking_audit_erasure \
  0048_support_billing_erasure ; do

  python -m alembic \
    -x migration_policy=mumbai \
    -x mumbai_project=wqjlgpnbiapcrlkxumcp \
    -x approval_manifest=manifests/gate_b_upgrade_${REVISION}.json \
    -x approval_id=<gate-b-id> \
    upgrade $REVISION
  python -m alembic current
  echo "--- STOP AND VERIFY before continuing ---"
done

# Step: 0049 equivalence check (requires RESTORE_DB_URL pointed at production READ replica or local copy)
# This step connects to a read-only copy, not production write path.
# Command not included here - see ISOLATED_RESTORE_EVIDENCE_TEMPLATE.md

# Step: stamp 0049
python -m alembic \
  -x mumbai_project=wqjlgpnbiapcrlkxumcp \
  -x approval_manifest=manifests/gate_b_stamp_0049.json \
  -x approval_id=<gate-b-id> \
  stamp 0049_trial_salon_plan_prices
python -m alembic current   # must show 0049_trial_salon_plan_prices

# Step: upgrade 0050
python -m alembic \
  -x migration_policy=mumbai \
  -x mumbai_project=wqjlgpnbiapcrlkxumcp \
  -x approval_manifest=manifests/gate_b_upgrade_0050.json \
  -x approval_id=<gate-b-id> \
  upgrade 0050_plan_price_valid_until
python -m alembic current   # must show 0050_plan_price_valid_until
```

---

## Finance endpoint checks (after Gate C: 0051)

```bash
# Smoke-test the finance API after 0051 is applied
curl -H "Authorization: Bearer <OWNER_TOKEN>" \
  https://api.salones.in/v1/owner/salons/<SALON_ID>/finance/statement
# Expected: 200 with empty data (no expenses yet), no 500
```

---

## Client compatibility requirements

| Client | 0041 | 0042 | 0043-0048 | 0049 | 0050 | 0051 | 0052 |
|--------|------|------|-----------|------|------|------|------|
| Customer app | description field removed | category removed | none visible | none visible | none visible | none visible | **BREAKING: 30-day slot window** |
| Owner app | description field removed | category removed | no-show rules | plan prices tab | valid_until field | **finance tab required** | slot window |
| Admin website | description removed | category removed | none | plan prices | valid_until | finance view | none |
| Walk-in QR | description→NULL in get_salon_by_qr (column removed, NULL substituted) | none | none | none | none | none | none |

**0052 gate C prerequisite:** customer app must ship and be deployed before 0052 runs. Running 0052 before the customer app update causes slots beyond 30 days to silently disappear from availability without the app handling it gracefully.

---

## Conditions for setting AUTO_DEPLOY_ENABLED=true (Gate C)

All of the following must be true before Gate C authorization:
1. Gate B complete — alembic current shows 0050_plan_price_valid_until, all checks PASS.
2. Full API smoke test passes on production (core booking, cancellation, payment flows).
3. No open P0/P1 incidents.
4. Customer app deployed on a version that handles 30-day slot window.
5. Owner app deployed on a version that shows the finance tab (for 0051).
6. Admin website on a version compatible with description-less salons/services.
7. Walk-in QR website verified with NULL description.
8. Owner explicitly approves enabling automatic deployment in a separate approval action.
9. PITR confirmed active or latest backup confirmed restorable.

`AUTO_DEPLOY_ENABLED=false` must remain unchanged until every item above is confirmed.
