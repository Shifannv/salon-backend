# Production migration reconciliation — correction and safe path

**30 October 2026. Read-only design document only.**
No migrations applied, no data changed, no production system mutated.
This document supersedes the erroneous stamp proposal in `PRODUCTION_MIGRATION_RECONCILIATION_2026-10-30.md`.

---

## Part 1 — Why the stamp proposal is UNSAFE

The original report proposed:

```sql
INSERT INTO alembic_version(version_num) VALUES ('0045_customer_booking_changes');
INSERT INTO alembic_version(version_num) VALUES ('0050_plan_price_valid_until');
```

**This is wrong for two independent reasons.**

### Reason 1 — Alembic is not a checklist; it is a chain cursor

`alembic_version` holds the current HEAD revision of the chain. When Alembic reads `0050_plan_price_valid_until` in that table, it concludes that the database schema is at revision 0050 and that every revision from 0001 through 0050 has been applied. It does not track individual revisions independently.

Stamping `0050` while 0041–0048 are absent would cause:
- `alembic upgrade head` to silently skip 0041–0048 and try to run only 0051–0052
- 0051 and 0052 would run on a database that is missing `bookings.change_version`, `bookings.committed_reschedules`, `booking_services.is_active`, `booking_customer_changes`, `booking_financial_outcomes`, `booking_finance_commands`, `support_erasure_events`, and many other objects those migrations depend on or modify

### Reason 2 — 0045 is not applied; the original evidence was wrong

The original report identified `customer_booking_restrictions` as a table created by 0045 and concluded 0045 was applied. **This was a read error.** Reading 0045's actual SQL reveals:

0045 (`customer_booking_changes`) creates:
- `booking_customer_changes` table
- Columns `change_version`, `committed_reschedules`, `service_fulfilment_amount` on `bookings`
- Column `is_active` on `booking_services`
- A 4-argument `get_available_slots(uuid, date, int, uuid)` overload
- Functions `booking_change_quote` and `apply_customer_booking_change`

**None of these objects exist in production** (confirmed by live query, 2026-10-30):
- `booking_customer_changes` is absent from the production table list
- `get_available_slots` has only one overload: `(p_staff_id uuid, p_date date, p_duration_minutes integer)` — the 4-arg version is absent
- `booking_change_quote` and `apply_customer_booking_change` are absent from the routine listing
- 0047 adds `anonymized_at` to `booking_customer_changes` and `booking_finance_commands` — neither table exists, confirming 0047 cannot have run

`customer_booking_restrictions` is a table from the pre-0041 bootstrap baseline (0001–0040), not from 0045.

---

## Part 2 — Corrected production state

**Query timestamp window: 2026-10-30 ~01:35–01:42 IST**
**All queries read-only. No mutation occurred.**

| Migration | Structural verdict | Evidence |
|---|---|---|
| 0041 `salon_photo_limits` | **NOT APPLIED** | `salons.description` exists; `t_salon_image_limits` trigger absent; `guard_salon_photo_limits` absent |
| 0042 `remove_business_category` | **NOT APPLIED** | `salons.category` exists |
| 0043 `no_show_attendance_guards` | **NOT APPLIED** | `booking_no_show_attendance_guard` trigger absent |
| 0044 `versioned_checkout_policy` | **NOT APPLIED** | `bookings.checkout_policy_version` absent; `stamp_checkout_policy` function absent |
| **0045** `customer_booking_changes` | **NOT APPLIED** (CORRECTION — earlier report was wrong) | `booking_customer_changes` absent; 4-arg `get_available_slots` absent; `booking_change_quote`, `apply_customer_booking_change` absent; `bookings.change_version` absent |
| 0046 `u08_financial_outcomes` | **NOT APPLIED** | `booking_financial_outcomes` and 3 related tables absent |
| 0047 `booking_audit_erasure` | **NOT APPLIED** | `anonymized_at` absent from both target tables; `erase_booking_audit_personal_data` absent; target tables (`booking_customer_changes`, `booking_finance_commands`) absent |
| 0048 `support_billing_erasure` | **NOT APPLIED** | `support_erasure_events` absent |
| 0049 `trial_salon_plan_prices` | **PARTIALLY APPLIED — UNCONFIRMED** | `salon_plan_prices` table EXISTS (CREATE TABLE ran); data UPDATEs to `subscription_plans` unverified — see Part 3 |
| 0050 `plan_price_valid_until` | **APPLIED** (outside Alembic, no version stamp) | `salon_plan_prices.valid_until` column exists |
| 0051 `owner_finance_cashbook` | **NOT APPLIED** | All 4 tables absent |
| 0052 `booking_window_30_days` | **NOT APPLIED** | Live `get_available_slots` body has no `v_today` variable or 30-day date range guard |

**Alembic version table: zero rows.** No revision has ever been stamped.

**Summary of the actual gap**: migrations 0041–0048 are entirely absent. 0049's structure ran but its data mutations are unconfirmed. 0050 ran. 0051–0052 are absent. The chain is broken at 0040 with two out-of-band SQL executions (0049 structural, 0050 structural+column).

---

## Part 3 — 0049 cannot be considered applied until data is verified

0049 (`trial_salon_plan_prices`) contains two distinct kinds of work:

1. **Structural** — `CREATE TABLE public.salon_plan_prices (...)` and index/RLS/grants. This is confirmed applied (`salon_plan_prices` table exists).
2. **Data mutations** — four `UPDATE public.subscription_plans SET price_amount = X WHERE code = 'Y' AND price_amount = old_value`. These are idempotent guards (they only run if the old value is still in place), but whether they ran is unknown.

The data verification query (reading `subscription_plans` price values) was blocked in this session by the production read classifier. The price values must be manually verified by a privileged operator before 0049 is classified as fully applied.

**Until verified**, treat 0049 as "structural only, data unknown." When running 0049 on an isolated restore, the data UPDATEs will safely run (they are idempotent). Do not skip them.

---

## Part 4 — Why the current main code cannot be deployed without schema changes

The following objects are missing from production and are referenced directly by the deployed Python code:

| Missing object | Migration | Code location affected |
|---|---|---|
| `bookings.change_version` | 0045 | SQLAlchemy `Booking` model and booking change use case |
| `bookings.committed_reschedules` | 0045 | SQLAlchemy `Booking` model |
| `bookings.service_fulfilment_amount` | 0045 | SQLAlchemy `Booking` model |
| `booking_services.is_active` | 0045 | `BookingService` model and all booking queries that filter by it |
| `booking_customer_changes` | 0045 | `BookingFinanceRepository`, booking change endpoints |
| `get_available_slots(uuid,date,int,uuid)` (4-arg) | 0045 | `booking_change_quote` Postgres function called by booking change use case |
| `bookings.checkout_policy_version` | 0044 | `booking_change_quote` Postgres function (reads this column) |
| `booking_financial_outcomes` | 0046 | `BookingFinanceRepository` — `admin_statement`, `owner_statement` endpoints |
| `booking_finance_commands` | 0046 | `BookingFinanceRepository` — `finance_command` endpoint |
| `salon_expenses`, `salon_cash_adjustments`, `salon_day_closes`, `salon_expense_rules` | 0051 | Finance cashbook endpoints |

An app-only release (code deployed, no schema changes) is **not possible**. At minimum, 0041–0045 must be applied before the current main code is deployed, and 0051 must be applied before finance endpoints can be served without 500 errors.

---

## Part 5 — Comparison of safe reconciliation approaches

### Approach A — New bridge migration (e.g., `0053_production_reconciliation_bridge`)

A new migration file that absorbs the effect of all missing migrations (0041–0048, 0051–0052) using idempotent SQL (`IF NOT EXISTS`, `CREATE OR REPLACE`, `ADD COLUMN IF NOT EXISTS`).

| Property | Assessment |
|---|---|
| Falsely marks missing migrations as applied? | **No** — 0041–0052 remain unstamped; only the new revision is stamped |
| Data-loss risk | Low (idempotent guards) if written correctly |
| Downtime risk | Medium — includes all DDL including DROP COLUMN (0041/0042) which require brief lock |
| Rollback feasibility | Poor — 0041–0052 are forward-only; the bridge inherits that constraint |
| Can support 0051 finance tables? | **Yes** — bridge includes them |
| Requires migration rewrites? | No new rewrites; bridge is a new file |
| Production verification required | Full isolated restore test as defined in Part 7 |

**Problem**: Future developers reading the migration chain will see 0041–0052 as "never ran" and then a bridge. The intent of each change is permanently obscured. `alembic downgrade` from the bridge head would attempt to reverse all of 0041–0052's effect in a single step, which is likely undefined or broken (all those migrations have `downgrade` that raises RuntimeError).

**Use only if:** the project commits to never using `alembic downgrade` and is prepared to document the break permanently.

### Approach B — Idempotent forward repair (RECOMMENDED)

For each migration from 0041 to 0052, make the SQL idempotent at the specific statements that conflict with the current production state, then run each migration in order on an isolated restore. After each migration's SQL runs cleanly on the restore, that revision can be run on production and stamped.

**Specific idempotency changes required**:

| Migration | Current SQL | Required change |
|---|---|---|
| 0041 | `ALTER TABLE public.salons DROP COLUMN description` | `DROP COLUMN IF EXISTS description` |
| 0041 | `ALTER TABLE public.services DROP COLUMN description` | `DROP COLUMN IF EXISTS description` |
| 0041 | `CREATE UNIQUE INDEX uq_salon_active_image_url ON ...` | `CREATE UNIQUE INDEX IF NOT EXISTS uq_salon_active_image_url ON ...` |
| 0041 | `CREATE TRIGGER t_salon_image_limits BEFORE ...` | Wrap with `DROP TRIGGER IF EXISTS; CREATE TRIGGER` |
| 0042 | `ALTER TABLE public.salons DROP COLUMN IF EXISTS category RESTRICT` | Already uses IF EXISTS — safe |
| 0043 | `CREATE TRIGGER booking_no_show_attendance_guard ...` | `DROP TRIGGER IF EXISTS; CREATE TRIGGER` (already has `DROP TRIGGER IF EXISTS` line) — **already idempotent** |
| 0044 | New function + trigger only — no conflicting DDL | Already idempotent (`CREATE OR REPLACE FUNCTION`, `DROP TRIGGER IF EXISTS`) — **already idempotent** |
| 0045 | `ALTER TABLE public.bookings ADD COLUMN change_version ...` | `ADD COLUMN IF NOT EXISTS change_version ...` |
| 0045 | `ALTER TABLE public.bookings ADD COLUMN committed_reschedules ...` | `ADD COLUMN IF NOT EXISTS committed_reschedules ...` |
| 0045 | `ALTER TABLE public.bookings ADD COLUMN service_fulfilment_amount ...` | `ADD COLUMN IF NOT EXISTS service_fulfilment_amount ...` |
| 0045 | `ALTER TABLE public.booking_services ADD COLUMN is_active ...` | `ADD COLUMN IF NOT EXISTS is_active ...` |
| 0045 | `CREATE TABLE public.booking_customer_changes ...` | `CREATE TABLE IF NOT EXISTS` |
| 0046 | All CREATE TABLEs | `CREATE TABLE IF NOT EXISTS` for each |
| 0047 | `ALTER TABLE ... ADD COLUMN anonymized_at ...` | `ADD COLUMN IF NOT EXISTS anonymized_at ...` for both tables |
| 0048 | `ALTER TABLE public.support_tickets ADD COLUMN ...` | `ADD COLUMN IF NOT EXISTS` for each |
| 0048 | `ALTER TABLE public.support_tickets ADD CONSTRAINT ...` | Wrap with `DO $$ BEGIN ... EXCEPTION WHEN duplicate_object THEN NULL; END $$` |
| 0048 | `CREATE TABLE public.support_erasure_events ...` | `CREATE TABLE IF NOT EXISTS` |
| 0049 | `CREATE TABLE public.salon_plan_prices ...` | **`CREATE TABLE IF NOT EXISTS`** (REQUIRED — table already exists) |
| 0050 | `ADD COLUMN IF NOT EXISTS valid_until` | Already uses IF NOT EXISTS — **already idempotent** |
| 0051 | All CREATE TABLEs | `CREATE TABLE IF NOT EXISTS` for each |
| 0052 | All `CREATE OR REPLACE FUNCTION` | Already idempotent — **already idempotent** |

| Property | Assessment |
|---|---|
| Falsely marks missing migrations as applied? | **No** — each revision is stamped only after its SQL has run successfully |
| Data-loss risk | Minimal — idempotent guards prevent re-running already-applied DDL |
| Downtime risk | Same as original migrations; each can be run in a maintenance window |
| Rollback feasibility | Same as original (forward-only; downgrade raises RuntimeError) — no new constraint |
| Can support 0051 finance tables? | **Yes** |
| Requires migration rewrites? | **Yes** — requires editing each migration's SQL file. Each edit must be reviewed and approved separately. This is a new PR. |
| Production verification required | Full isolated restore test per Part 7 |

**This approach gives an accurate Alembic chain**: after all 12 migrations complete, `alembic_version` contains `0052_booking_window_30_days` and the chain is honest — every revision from 0001 to 0052 actually ran.

**Why it does not falsely mark missing migrations**: Each revision is only stamped after its SQL has executed successfully on the target database. The stamp follows execution; it does not precede it.

### Approach C — Compatibility release (hide endpoints until schema is ready)

Add startup guards that return HTTP 503 for finance and booking-change endpoints when their required tables are absent. Deploy this guarded code first, apply migrations separately, then remove the guards.

| Property | Assessment |
|---|---|
| Falsely marks missing migrations as applied? | N/A — this is a code-layer mitigation, not a schema tool |
| Data-loss risk | None — no schema changes |
| Downtime risk | None — app still serves all non-guarded endpoints |
| Rollback feasibility | Good — remove guards and redeploy |
| Can support 0051 finance tables? | No by itself — prevents 500s but does not create the tables |
| Requires migration rewrites? | No |
| Production verification required | Code review of the guards; integration test that endpoints return 503 not 500 |

**This approach is complementary, not standalone.** It reduces the urgency of schema migration by preventing production 500 errors for finance endpoints. It does not solve the schema gap and is not a substitute for Approach B.

**The critical remaining problem with Approach C alone**: `bookings.change_version`, `bookings.committed_reschedules`, and `booking_services.is_active` (all from 0045) are referenced by SQLAlchemy models. If the ORM models declare these columns and production doesn't have them, any query touching the `bookings` or `booking_services` tables will fail — not just the booking-change endpoints. Guards cannot prevent model-layer failures. This means 0041–0045 must run before any app code deployment regardless.

### Approach D — Verified direct SQL with sequential Alembic stamps

Run each migration's SQL statements directly (using `psql` or `alembic upgrade --sql` output), verify each step manually, then stamp the revision with `alembic stamp <revision>` — NOT `alembic stamp head`.

This is functionally equivalent to Approach B but does not require modifying the migration files. The risk is that `alembic stamp <individual_revision>` is NOT how Alembic is designed to work: `alembic stamp <rev>` sets the HEAD to that revision, implying all ancestors are applied. Running `alembic stamp 0041` while 0001–0040 are from the bootstrap (never Alembic-stamped) would be interpreted by Alembic as "schema is at 0041."

**This approach cannot achieve an accurate chain without running each migration in order and stamping each in order.** Attempting to stamp a mid-chain revision while skipping earlier ones creates the same false-history problem.

---

## Part 6 — How production gets a single trustworthy Alembic revision

The ONLY honest way to have `alembic_version` reflect the true schema state, without lying about missing migrations, is:

1. **Run every migration from 0041 through 0052 in order, making each one idempotent (Approach B).**
2. After each migration's SQL executes successfully, `alembic upgrade <next_revision>` advances `alembic_version` to that revision.
3. After 0052 completes, `alembic_version` contains `0052_booking_window_30_days`, which is true: the database now has all 0001–0052 objects.

There is no shortcut that results in a trustworthy chain. "Stamping" a later revision while earlier ones are missing is lying to Alembic; it will cause incorrect `upgrade` and `downgrade` commands in the future.

For 0049 and 0050 specifically:
- When running 0049 on production, the `CREATE TABLE IF NOT EXISTS salon_plan_prices` will skip silently because the table already exists. The data UPDATEs will run safely (idempotent guards). The result after 0049: schema unchanged, data may or may not change (idempotent). Stamp 0049.
- 0050: `ADD COLUMN IF NOT EXISTS valid_until` will skip silently. Stamp 0050.

This means 0049 and 0050 are "run again but do nothing" — which is correct and honest. The chain is complete.

---

## Part 7 — Required isolated restore test stages

The following stages must all complete before any production migration command is authorized.

### Stage 1 — Isolated restore environment

- Create a new, empty Postgres instance completely separate from `wqjlgpnbiapcrlkxumcp`
- Take a production dump (coordinated with owner as a separate approved action)
- Restore dump to the isolated instance
- Confirm: 44 tables present, `alembic_version` has zero rows, key row counts match

### Stage 2 — Apply idempotent migration patch

- In a separate PR (not in production, not on `main`): apply all idempotency changes from the table in Part 5, Approach B
- This PR is reviewed and approved before any isolated restore test
- The only changes are `IF NOT EXISTS` / `IF EXISTS` guards and `DROP TRIGGER IF EXISTS` before creates

### Stage 3 — Sequential migration run on isolated restore

Run in strict order, verifying each step:

```
0041 → verify salons.description absent, t_salon_image_limits trigger present
0042 → verify salons.category absent
0043 → verify booking_no_show_attendance_guard trigger present
0044 → verify bookings.checkout_policy_version present, stamp_checkout_policy_tg trigger present
0045 → verify booking_customer_changes table present, bookings.change_version present,
        get_available_slots(uuid,date,int,uuid) 4-arg overload present
0046 → verify booking_financial_outcomes present
0047 → verify booking_customer_changes.anonymized_at present, booking_finance_commands.anonymized_at present
0048 → verify support_erasure_events table present, support_tickets.retained_restricted present
0049 → verify idempotent skip on CREATE TABLE; verify subscription_plans price values (confirm data state)
0050 → verify idempotent skip on ADD COLUMN
0051 → verify salon_expenses, salon_cash_adjustments, salon_day_closes, salon_expense_rules all present
0052 → verify get_available_slots body includes v_today 30-day range check; verify create_booking window guard
```

After each step: confirm Alembic version table has the correct single entry.

### Stage 4 — Data integrity check on isolated restore

```sql
SELECT count(*) FROM bookings;              -- unchanged from pre-migration count
SELECT count(*) FROM salon_subscriptions;   -- unchanged
SELECT count(*) FROM profiles;              -- unchanged
SELECT count(*) FROM booking_payments;      -- unchanged
-- New tables: all empty (no data existed before these tables)
SELECT count(*) FROM booking_customer_changes;  -- 0
SELECT count(*) FROM booking_financial_outcomes; -- 0
SELECT count(*) FROM salon_expenses;            -- 0
-- Verify 0041 image retirement did not accidentally deactivate images in use
SELECT count(*) FROM salon_images WHERE is_active;  -- should be > 0 for salons with images
-- Verify 0042 category drop didn't leave orphan references
-- (no query needed; category was a text column with no FK)
-- Verify checkout_policy_version default on new bookings (from 0044)
-- INSERT a test booking, confirm checkout_policy_version = 'customer_processing_v1'
```

### Stage 5 — Full test suite on isolated restore

```bash
DATABASE_URL=<isolated_restore_url> pytest backend/tests/ -q
# Must match or exceed current unit test pass count
# Key suites: booking tests, finance tests, test_cloud_run_auto, test_release_configuration
```

### Stage 6 — Record and owner-approve restore evidence

Document backup timestamp, each migration's output, each verification query result, test suite pass count. Owner reviews and explicitly approves before production migration is authorized.

---

## Part 8 — Release boundaries

### Boundary 0: App-only release — NOT POSSIBLE

Deploying current main code without schema changes will cause:
- ORM failures on any `bookings` or `booking_services` query (missing `change_version`, `committed_reschedules`, `service_fulfilment_amount`, `is_active`)
- 500 on all booking-change endpoints (missing `booking_customer_changes`, 4-arg slot function)
- 500 on all finance endpoints (missing `booking_financial_outcomes`, `salon_expenses`, etc.)

A compatibility guard (Approach C) could prevent finance 500s but cannot prevent ORM model column failures from 0045. **0041–0045 must run before any code deployment.**

### Boundary 1: Minimum schema release for core booking (0041–0045)

Deploys: migrations 0041, 0042, 0043, 0044, 0045 in order.

After this boundary:
- Core booking endpoints work
- Booking change endpoints work
- Finance endpoints still 500 (0046, 0051 absent)
- No-show enforcement active (0043)
- Photo limits enforced (0041)
- `salons.category` and `salons.description` dropped (0042, 0041) — old client apps that rely on these fields receive null/absent fields
- 30-day booking window not yet enforced (0052 absent)

Client compatibility risk: old owner app versions that send or read `salons.category` will see it dropped. Must verify app behavior before this step.

### Boundary 2: Schema compatibility release for erasure workers (add 0046, 0047, 0048)

Deploys: migrations 0046, 0047, 0048 (can run in one maintenance window after Boundary 1).

After this boundary:
- U08 financial outcome tracking active (0046, requires 0044's `checkout_policy_version` column)
- Booking audit erasure works correctly (0047)
- Support ticket erasure works (0048)
- Finance cashbook endpoints still 500 (0051 absent)

### Boundary 3: Finance cashbook release (add 0049 idempotent, 0050 idempotent, 0051)

Deploys: 0049 (idempotent re-run, no structural change), 0050 (idempotent re-run), 0051.

**0049 data verification must complete before this boundary**: confirm subscription_plans price values are at expected 0049 levels before deciding whether the data UPDATEs need to run.

After this boundary:
- All finance cashbook endpoints work (`/ledger`, `/expenses`, `/day-close`, etc.)
- Expense rules work
- 30-day booking window not yet enforced

**This is the earliest point at which 0051 can safely be deployed**:
- 0041–0048 must have already run (in Boundaries 1 and 2 above)
- 0049 data state must be verified and stamped
- Isolated restore test (Part 7) must have passed for the full 0051 scope
- Owner must approve in writing

### Boundary 4: Booking window release (add 0052) — requires client coordination

0052 replaces `get_available_slots` and `create_booking` to enforce a 30-day future booking limit. Old customer app versions that query availability for dates beyond today+30 will receive empty results. Old apps that attempt to create a booking more than 30 days out will receive `booking_window_exceeded`.

This boundary must be coordinated with a customer app release. Apply 0052 on the same day (or after) the customer app update that communicates the 30-day limit is live for all users.

---

## Part 9 — Required manual approvals before production migration

1. **Owner review of each migration's idempotency patch** — the PR that adds IF NOT EXISTS guards is a code change to the migration chain. It requires review against the key rules before merge.
2. **0049 data verification** — a privileged operator must query `subscription_plans` and confirm price values. Owner must see and approve the result before 0049 is stamped.
3. **Isolated restore evidence document** — all Stage 1–6 results from Part 7 must be reviewed and explicitly approved by the owner.
4. **Old-client compatibility sign-off for 0041/0042** — the owner must confirm that old owner app versions tolerate the dropped `category` and `description` fields before 0041/0042 run.
5. **Client coordination for 0052** — owner must confirm the customer app update window before 0052 runs.
6. **Each production migration execution** — each migration run on the production database is a separate authorized action. The discovery and planning in this document do not authorize any production execution.

---

## Confirmation

No production state changed while producing this document. The Supabase project `wqjlgpnbiapcrlkxumcp` was queried read-only during the earlier discovery session (2026-10-30 ~01:35–01:42 IST). No queries, schema changes, migrations, stamps, data writes, deploys, secrets reads, backups, restores, or GitHub variable changes were performed in this session or while writing this document.

`AUTO_DEPLOY_ENABLED` remains `false`. The production Cloud Run service is unchanged.
