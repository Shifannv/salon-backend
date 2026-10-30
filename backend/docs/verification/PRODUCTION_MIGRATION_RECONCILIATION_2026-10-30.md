# Production migration reconciliation and backup/restore plan

**30 October 2026 — read-only discovery. No migrations applied, no data changed.**
Query timestamp window: 2026-10-30 ~01:35–01:42 IST.
Supabase project queried: `wqjlgpnbiapcrlkxumcp` (shared staging/production — see B2 note below).

---

## 1. Alembic version table

```sql
SELECT version_num FROM alembic_version;
-- Result: [] — zero rows
```

No migration has ever been stamped through Alembic. All applied migrations were executed directly as SQL, outside the Alembic chain. The Alembic table itself exists (confirmed) but is empty.

---

## 2. Production table inventory (baseline vs. post-0040)

Tables present at query time (all public BASE TABLEs):

```
account_deletion_challenges    booking_audit_events         booking_payments
account_deletion_requests      booking_services             bookings
alembic_version                blocked_slots                customer_booking_restrictions
api_rate_limits                booking_action_requests      device_tokens
email_events                   notification_deliveries      notification_outbox
languages                      notifications                payment_anomalies
payment_idempotency_keys       payment_provider_account_audit  payment_provider_accounts
payment_refunds                payment_webhook_events       profiles
salon_access                   salon_holidays               salon_images
salon_payout_account_history   salon_payout_accounts        salon_plan_prices
salon_reports                  salon_subscriptions          salons
service_categories             service_subcategories        services
staff                          staff_service_languages      staff_services
subscription_billing_records   subscription_events          subscription_plans
subscription_provider_accounts support_messages             support_tickets
```

**Tables absent** (expected from migrations 0041–0052):

| Expected table | Migration | Status |
|---|---|---|
| `booking_financial_outcomes` | 0046 | ABSENT |
| `booking_finance_commands` | 0046 | ABSENT |
| `booking_policy_refund_jobs` | 0046 | ABSENT |
| `booking_finance_reconciliations` | 0046 | ABSENT |
| `support_erasure_events` | 0048 | ABSENT |
| `salon_expenses` | 0051 | ABSENT |
| `salon_cash_adjustments` | 0051 | ABSENT |
| `salon_day_closes` | 0051 | ABSENT |
| `salon_expense_rules` | 0051 | ABSENT |

---

## 3. Per-migration reconciliation: 0041–0052

### 0041 `salon_photo_limits` — **NOT APPLIED**

Key indicators:
- `salons.description` column **EXISTS** — the migration's `ALTER TABLE public.salons DROP COLUMN description` was not executed.
- `services.description` column — not checked explicitly but expected to still exist.
- Trigger `t_salon_image_limits` on `salon_images` — **absent** (trigger query returned no row for this name).
- `guard_salon_photo_limits()` function — absent (not in routine listing).
- Unique index `uq_salon_active_image_url` — not verified but expected absent.

The SQL also replaces `get_salon_by_qr` to return `NULL::text` for description and retires excess salon images. Neither change has been applied.

### 0042 `remove_business_category` — **NOT APPLIED**

Key indicators:
- `salons.category` column **EXISTS** (confirmed by column query: `data_type=text, is_nullable=YES`).
- This migration's only DDL is `ALTER TABLE public.salons DROP COLUMN IF EXISTS category RESTRICT`.

**Important**: 0042 depends on 0041. Neither can run until 0041 runs first. Additionally, deploying the current main code before 0042 is applied means `salons.category` is still visible to the API. Old owner clients that send `category` in their payloads will not break, but the code no longer reads or writes it.

### 0043 `no_show_attendance_guards` — **NOT APPLIED**

Key indicators:
- Trigger `booking_no_show_attendance_guard` on `bookings` — **absent** (not found in trigger query).
- Function `guard_no_show_attendance()` — absent from routine listing.

This migration only creates a trigger function and trigger; no column additions. However it must run in chain order (after 0042).

### 0044 `versioned_checkout_policy` — **NOT APPLIED**

Key indicators:
- Column `bookings.checkout_policy_version` — **absent** (searched as `checkout_policy`; trigger query returned nothing for `stamp_checkout_policy_tg`).
- Trigger `stamp_checkout_policy_tg` — absent.
- Function `stamp_checkout_policy()` — absent from routine listing.

The migration's DDL adds `checkout_policy_version` to `bookings` with a default and the trigger. Without this column, the U08 financial policy (0046) cannot be used.

### 0045 `customer_booking_changes` — **APPLIED** (outside Alembic, no version stamp)

Key indicators — table exists with all expected columns:
```
customer_booking_restrictions
  customer_id              uuid      NOT NULL
  no_show_count            integer
  pay_at_salon_blocked_until  timestamptz
```

Table is present and column types match the migration's intended schema. This was applied directly as SQL; Alembic was never stamped.

**Risk**: 0045 was applied without 0041–0044 having run. The migration chain is broken. Alembic cannot run 0045 again (it would fail on the already-existing table) and cannot safely run 0041–0044 after 0045 without careful conflict checking.

### 0046 `u08_financial_outcomes` — **NOT APPLIED**

Four tables entirely absent: `booking_financial_outcomes`, `booking_finance_commands`, `booking_policy_refund_jobs`, `booking_finance_reconciliations`. Functions `snapshot_terminal_booking_finance`, `reconcile_terminal_booking_funds`, `manage_booking_finance`, `guard_financial_outcome_snapshot` — all absent from routine listing.

### 0047 `booking_audit_erasure` — **NOT APPLIED** (table was created earlier; erasure columns absent)

Key indicators:
- `booking_audit_events` table **EXISTS** (was created by a pre-0041 migration).
- Columns `erased_at` and `erasure_actor` queried on `booking_audit_events` — **both absent**.
- 0047 adds these erasure columns to the existing table. They are not present.

### 0048 `support_billing_erasure` — **NOT APPLIED**

`support_erasure_events` table is **absent**.

### 0049 `trial_salon_plan_prices` — **LIKELY APPLIED** (data change; no structural indicator)

This migration inserts or updates rows in `salon_plan_prices` for trial plan pricing. No new columns or tables to detect structurally. Previously noted as "separately applied." The `salon_plan_prices` table exists. Exact data verification requires a targeted data query against the plan price rows — not performed here to avoid reading potentially sensitive pricing configuration.

### 0050 `plan_price_valid_until` — **APPLIED** (outside Alembic, no version stamp)

Key indicator: `salon_plan_prices.valid_until` column **EXISTS** (`data_type=timestamp with time zone`, confirmed by column query).

### 0051 `owner_finance_cashbook` — **NOT APPLIED**

All four tables absent: `salon_expenses`, `salon_cash_adjustments`, `salon_day_closes`, `salon_expense_rules`. All associated functions and triggers absent.

**Consequence**: Finance API routes are registered unconditionally in the main code. Any request to `/v1/salons/me/ledger/...` or `/v1/salons/me/expenses/...` on a deployed main revision will fail with a Postgres `UndefinedTable` error that surfaces as HTTP 500.

### 0052 `booking_window_30_days` — **NOT APPLIED**

Live `get_available_slots` body (queried verbatim):

```sql
-- Production (current, 0052 NOT applied):
if v_tz is null then return; end if;
-- goes directly to holiday check — NO date-range guard
if exists (select 1 from salon_holidays ...
```

Expected body after 0052:
```sql
if v_tz is null then return; end if;
v_today := (now() at time zone v_tz)::date;
if p_date < v_today or p_date > v_today + 30 then  -- <-- this line absent
  return;
end if;
if exists (select 1 from salon_holidays ...
```

`create_booking` similarly lacks the `if p_source = 'app' and v_booking_date > v_today + 30 then raise exception 'booking_window_exceeded'` guard.

**Consequence of current state**: Customers can book slots more than 30 days from today. Applying 0052 without a client app update that communicates the new limit will cause `get_available_slots` to return empty for any date beyond today+30, which old app versions will show as "no availability."

---

## 4. Exact reconciliation table (migration scope decision matrix)

| Migration | Structural state | Safe to run on isolated restore | Prerequisite state |
|---|---|---|---|
| **0041** | NOT APPLIED | Yes — additive trigger + index + DROP on description (no data at risk if description is blank/null for all salons) | None (first in gap chain) |
| **0042** | NOT APPLIED | Yes — single column DROP | Must run 0041 first |
| **0043** | NOT APPLIED | Yes — trigger only, no column | Must run 0042 first |
| **0044** | NOT APPLIED | Yes — column addition + trigger | Must run 0043 first |
| **0045** | ALREADY APPLIED | **DO NOT RUN** — table exists; `CREATE TABLE` will fail | n/a |
| **0046** | NOT APPLIED | Requires 0044 (checkout_policy_version column referenced in trigger) | Must run 0044 first; 0046 is a finance release gate — separate approval |
| **0047** | NOT APPLIED | Yes — column additions on existing table | Must confirm 0046 scope |
| **0048** | NOT APPLIED | Yes — new table | Can run independently |
| **0049** | LIKELY APPLIED | **DO NOT RUN** — re-running will create duplicate rows or conflict on unique constraint | Verify rows first |
| **0050** | APPLIED | **DO NOT RUN** — column exists; `ADD COLUMN valid_until` will fail | n/a |
| **0051** | NOT APPLIED | Yes — all new tables | Can run; no dependencies on 0041–0048 objects |
| **0052** | NOT APPLIED | Yes — `CREATE OR REPLACE FUNCTION` (safe to run multiple times) | No prerequisite DDL; requires client coordination (see above) |

**Critical chain constraint**: 0041 → 0042 → 0043 → 0044 must run in order before 0046. 0045 was already applied and must be skipped. 0049 and 0050 were applied and must be skipped.

**Minimum schema-safe release scope** (without 0046 U08 finance policy):
Run 0041, 0042, 0043, 0044; skip 0045, 0049, 0050; defer 0046; run 0047, 0048 (safe independently); defer 0051 and 0052 until coordinated client rollout.

**Minimum scope to unblock finance endpoints** (prevents HTTP 500):
Run 0051 additionally.

**Minimum scope to enforce 30-day booking window**:
Run 0052 additionally, only after customer app update is deployed or confirmed backward-compatible.

---

## 5. Identified conflicts requiring manual resolution before ANY migration run

### C1 — 0041 drops `salons.description` but 0045 is already applied

0045 `customer_booking_restrictions` has no dependency on `salons.description`. Dropping `description` after 0045 is already present is safe from a dependency perspective. However, any active API code that reads `salons.description` will receive a null/missing field after 0041. Verify all callers (owner app, customer app, admin API) tolerate a missing `description` field before running 0041.

### C2 — 0045 breaks the Alembic chain

`alembic_version` is empty. Running `alembic upgrade head` would attempt to run 0001 through 0052 in order, including 0045 which will fail on `CREATE TABLE customer_booking_restrictions` because it already exists. The correct approach is:

1. Stamp the existing applied migrations into `alembic_version` manually before using Alembic to run anything:
   ```sql
   INSERT INTO alembic_version(version_num) VALUES ('0045_customer_booking_changes');
   INSERT INTO alembic_version(version_num) VALUES ('0050_plan_price_valid_until');
   -- Add 0049 if confirmed applied
   ```
2. Then use `alembic upgrade head` or targeted `alembic upgrade <revision>` — it will skip already-stamped revisions.
3. Alternatively, run each unapplied migration's SQL directly and stamp each revision after confirming success.

**Do not use `alembic stamp head` without running the migrations** — that would mark all revisions as applied without executing any SQL.

### C3 — 0046 requires `checkout_policy_version` column (from 0044)

The `snapshot_terminal_booking_finance` trigger function in 0046 reads `NEW.checkout_policy_version`. If 0046 is run without 0044, the trigger will fail at runtime on any booking status change, not at migration time. Run 0044 before 0046.

### C4 — Finance 500 risk before 0051

Deploying main code before 0051 means finance API routes will 500 on any access. This is a silent runtime failure that will appear in production logs. Options:
1. Apply 0051 before the first code deployment. **Recommended.**
2. Add a startup guard or feature flag that returns HTTP 503 for finance routes when the tables are absent. This requires code change and a separate PR.

---

## 6. Required backup and restore execution plan

**Scope**: Before running any migration in production, the following steps must be completed in full. Each step must be documented with timestamp and confirmation.

### Step 1 — Production backup

```
Action:  Create a point-in-time snapshot via Supabase dashboard or:
         supabase db dump --db-url "$PRODUCTION_DB_URL" > prod_backup_$(date +%Y%m%d_%H%M%S).sql
         OR: pg_dump -Fc -h <host> -U postgres -d postgres > prod_backup_YYYYMMDD.dump

Record:  - Exact timestamp of backup start
         - Exact size of dump file (bytes)
         - SHA-256 of dump file
         - Store in a location separate from the production host
```

**Note on shared DB**: The current Supabase project `wqjlgpnbiapcrlkxumcp` is shared between staging and production. Any backup taken is a backup of the shared state. This does not substitute for an isolated staging database (blocker B2 from `FIRST_PRODUCTION_AUTO_RELEASE_PLAN_2026-10-30.md`). The backup is for production protection only, not for staging rehearsal.

### Step 2 — Provision isolated restore target

```
Action:  Create a new, empty database instance completely separate from the
         shared Supabase project. Options:
         (a) Create a NEW Supabase project (different project ID, different DB host)
         (b) Create a separate RDS/Cloud SQL instance for rehearsal only
         
This database must:
         - Have no shared connection pool, storage, auth or DNS with production
         - Be reachable only from the developer's machine or a controlled runner
         - Be deleted after the rehearsal run is confirmed

Record:  - New project/instance hostname
         - Confirmation that it shares nothing with production
```

### Step 3 — Restore backup to isolated target

```
Action:  psql -h <isolated_host> -U postgres -d postgres < prod_backup_YYYYMMDD.sql
         OR: pg_restore -Fc -h <isolated_host> -U postgres -d postgres prod_backup_YYYYMMDD.dump

Verify:  SELECT count(*) FROM information_schema.tables WHERE table_schema='public';
         -- must match production table count (44 tables as of this query)
         SELECT version_num FROM alembic_version;
         -- must show 0 rows (matching production)
         SELECT count(*) FROM bookings;
         -- must be a non-negative integer; record it for before/after comparison
         SELECT count(*) FROM salon_subscriptions;
         -- record for before/after comparison
```

### Step 4 — Stamp Alembic version on isolated restore

```sql
-- Stamp already-applied migrations to prevent Alembic from re-running them
INSERT INTO alembic_version(version_num) VALUES
  ('0045_customer_booking_changes'),
  ('0050_plan_price_valid_until');
-- Also stamp 0049 if confirmed applied (run targeted data verification first):
-- SELECT count(*) FROM salon_plan_prices WHERE valid_until IS NOT NULL;
-- If > 0, 0050 is applied. For 0049: check trial plan price rows exist.
```

### Step 5 — Run target migration scope on isolated restore

The recommended minimum scope for the first release is 0041–0044, 0047, 0048, 0051. Run in strict order:

```bash
# From backend/ directory, with DATABASE_URL pointing to the ISOLATED restore:
alembic upgrade 0041_salon_photo_limits
alembic upgrade 0042_remove_business_category
alembic upgrade 0043_no_show_attendance_guards
alembic upgrade 0044_versioned_checkout_policy
# 0045 already stamped — skip
# 0046 deferred — skip
alembic upgrade 0047_booking_audit_erasure
alembic upgrade 0048_support_billing_erasure
# 0049 already stamped — skip
# 0050 already stamped — skip
alembic upgrade 0051_owner_finance_cashbook
# 0052 deferred until client coordination — skip
```

After each upgrade, confirm the key indicator objects exist:

| Migration | Verification query |
|---|---|
| 0041 | `SELECT column_name FROM information_schema.columns WHERE table_name='salons' AND column_name='description';` — expect 0 rows |
| 0042 | `SELECT column_name FROM information_schema.columns WHERE table_name='salons' AND column_name='category';` — expect 0 rows |
| 0043 | `SELECT tgname FROM pg_trigger WHERE tgname='booking_no_show_attendance_guard';` — expect 1 row |
| 0044 | `SELECT column_name FROM information_schema.columns WHERE table_name='bookings' AND column_name='checkout_policy_version';` — expect 1 row |
| 0047 | `SELECT column_name FROM information_schema.columns WHERE table_name='booking_audit_events' AND column_name='erased_at';` — expect 1 row |
| 0048 | `SELECT table_name FROM information_schema.tables WHERE table_name='support_erasure_events';` — expect 1 row |
| 0051 | `SELECT table_name FROM information_schema.tables WHERE table_name IN ('salon_expenses','salon_cash_adjustments','salon_day_closes','salon_expense_rules') ORDER BY 1;` — expect 4 rows |

### Step 6 — Verify data integrity on isolated restore

```sql
-- Row counts must match pre-migration values
SELECT count(*) FROM bookings;          -- unchanged
SELECT count(*) FROM salon_subscriptions; -- unchanged
SELECT count(*) FROM profiles;          -- unchanged
SELECT count(*) FROM booking_payments;  -- unchanged

-- No orphaned rows introduced
SELECT count(*) FROM booking_audit_events WHERE erased_at IS NOT NULL; -- expect 0 (new column, NULL default)
SELECT count(*) FROM salon_expenses;    -- expect 0 (new table)

-- get_salon_by_qr returns expected shape (description field is NULL, not error)
SELECT id, name, description FROM public.get_salon_by_qr('<any valid qr_token>');
-- description column should be present but NULL (0041 replaces function to return NULL::text)
```

### Step 7 — Run full test suite against isolated restore

```bash
# Set DATABASE_URL to the isolated restore
pytest backend/tests/ -q
# Must pass at same level as current main (77 unit tests, integration tests if configured)
# Key suites: test_cloud_run_auto.py, test_release_configuration.py, booking tests
```

### Step 8 — Record rehearsal evidence

Document in a new evidence file:
- Backup timestamp and SHA-256
- Isolated restore host (can be redacted to project-ID hash)
- Alembic stamp commands run
- Each `alembic upgrade` command and its exit code
- Each verification query result
- `pytest` pass/skip/fail count
- Any errors encountered and resolution
- Total elapsed time

This evidence file is a prerequisite for owner approval of the production migration run.

### Step 9 — Production migration (authorized separately)

Only after all of the above steps are documented and owner-approved:

```bash
# Confirm production backup is fresh (< 1 hour old)
# Confirm AUTO_DEPLOY_ENABLED is still false
# Run migrations in the exact same order as Step 5 above, against PRODUCTION_DB_URL
# Verify each step with the same queries from Step 5
# Record alembic_version table state after all migrations
```

---

## 7. Discovery limitations and outstanding items

1. **0049 exact state unverified**: Whether 0049 `trial_salon_plan_prices` data rows exist with the expected values was not queried in this session (avoided reading pricing configuration). Before stamping 0049 as applied, run a targeted data query on `salon_plan_prices` to confirm the trial plan rows exist.

2. **`services.description` not directly checked**: The column query checked `salons.description` and `salons.category`. The presence of `services.description` was not directly verified. Since 0041 drops both `salons.description` and `services.description`, and `salons.description` still exists, `services.description` is almost certainly also still present. This should be confirmed before planning 0041 execution.

3. **0046 intentionally deferred**: The U08 financial policy tables are not included in the minimum release scope. 0046 requires a separate finance release approval, client compatibility review for the new `checkout_policy_version` column, and a review of the `snapshot_terminal_booking_finance` trigger behavior on existing bookings.

4. **0052 client coordination required**: The 30-day booking window change will cause `get_available_slots` to return empty results for dates beyond today+30. Old app versions that fetch availability for dates far in the future will silently show no availability. This must be coordinated with a customer app release before 0052 is applied.

5. **Alembic chain repair (C2 above) must be reviewed**: The proposed stamp insertions (`INSERT INTO alembic_version`) must be reviewed by the owner before execution to confirm the exact set of applied migrations is accurately reflected. Incorrect stamping leads to either skipped necessary migrations or re-running already-applied ones.
