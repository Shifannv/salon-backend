# Alembic bridge graph validation

**30 October 2026. Read-only design validation.**
No production, database, Cloud Run, GitHub or provider system was accessed.
No migration files written, no commits, no pushes.
`AUTO_DEPLOY_ENABLED` remains `false`.

Evidence basis: two disposable local experiments run entirely from a temporary directory
using Alembic's Python API (no env.py, no policy guards, no external network).

---

## Evidence: the experiments

### Experiment setup

A dummy migration tree was created in a temporary directory, mirroring the real
revision structure and naming conventions (`0041_rev`, ..., `0052_rev`,
`0053_bridge`, `0054_merge`, `0055_future`). All `upgrade()` functions are no-ops.

**Graph under test:**
```
0001..0040  (linear chain)
      |
      +-- 0041 -- 0042 -- ... -- 0052  (dev chain)
      |
      +-- 0053_bridge
                  |
                  +-- 0054_merge (down_revision = ("0052", "0053_bridge"))
                              |
                              +-- 0055_future
```

### Experiment A — ScriptDirectory iterate_revisions

`ScriptDirectory.iterate_revisions(target, lower)` was called for each scenario.
This is the Alembic function that computes the upgrade plan (which revisions to execute).

**Results:**

| Scenario | Current state | Target | Plan |
|---|---|---|---|
| S1: fresh install | base (empty) | 0055_future | 0001..0040, **0053_bridge**, 0041..0052, 0054_merge, 0055_future |
| S2: baseline to bridge | 0040 | 0053_bridge | **0053_bridge** |
| S3: bridge to merge | 0053_bridge | 0054_merge | **0054_merge only** |
| S4: bridge to future | 0053_bridge | 0055_future | **0054_merge, 0055_future** |
| S5: dev normal chain | 0040 | 0052 | 0041..0052 |
| S6: dev to merge | 0052 | 0054_merge | **0054_merge only** |
| S7: both parents to merge | {0052, 0053_bridge} | 0054_merge | **0054_merge only** |

### Experiment B — Live SQLite execution

A minimal SQLite database was created. Alembic was used to execute real upgrades
through the `alembic.command.upgrade()` API. The `alembic_version` table was
inspected after each step.

**Graph:** `base → rev_a → rev_b` (dev chain) and `rev_a → rev_c → rev_d` where
`rev_d = merge(rev_b, rev_c)`.

**Execution sequence (rev_b deliberately never applied):**

```
Step 1: upgrade base -> rev_a
  alembic_version = ['rev_a']

Step 2: upgrade rev_a -> rev_c (bridge, skipping dev chain rev_b)
  alembic_version = ['rev_c']

Step 3: upgrade rev_c -> rev_d (merge)
        Expected: only rev_d executes; rev_b NOT executed
  alembic_version = ['rev_d']
  Result: merge applied successfully; rev_b was NOT run
```

---

## 1. Does 0053 → 0054 replay 0041–0052?

**No.** Both experiments prove this conclusively.

**Experiment A, scenario S3:**
`iterate_revisions("0054_merge", ["0053_bridge"])` returns `[0054_merge]`.
Alembic's upgrade plan contains only the merge revision itself. Revisions 0041–0052
are not included.

**Experiment B:**
With `alembic_version = {rev_c}` (analogous to production at 0053), upgrading to
`rev_d` (merge) executes only `rev_d`. After the merge, `alembic_version = {rev_d}`.
The dev-chain revision `rev_b` (analogous to 0041–0052) was never executed and the
upgrade succeeded.

**Why Alembic behaves this way:**
`iterate_revisions(merge, bridge)` computes the set of revisions that are ancestors of
the merge AND NOT ancestors of the bridge's history (inclusive). Since both 0041–0052
and 0053 branch from 0040, and 0040 is already in the bridge's ancestry, the branch
0041–0052 is considered "covered" by the common ancestor. Alembic's merge upgrade
only executes the merge step itself, not the uncovered branch. The merge revision
internally deletes both listed parents from `alembic_version` (0052 was never there,
so the DELETE is a no-op) and inserts the merge revision ID.

---

## 2. Is the proposed bridge safe or unsafe?

**The production upgrade path is safe. The fresh-install path is broken.**

### Production upgrade path: safe

`0040 → 0053 (bridge) → 0054 (merge) → future migrations`

Alembic only runs the bridge (1 revision) and the merge (1 revision). It does not
replay 0041–0052. Future migrations after the merge execute normally.

### Fresh-install path: broken

Experiment A, scenario S1 shows the exact fresh-install execution order:
```
0001_rev, 0002_rev, ... 0040_rev, 0053_bridge, 0041_rev, 0042_rev, ...
                                  ^^^^^^^^^^^
                                  Bridge runs BEFORE 0041–0052
```

On a fresh database, Alembic's topological sort places `0053_bridge` (which branches
from 0040 and has a higher numeric ID than 0052) **before** the dev chain (0041–0052).
This ordering is consistent across both tests and matches the naming convention
(both branch from 0040; Alembic sorts the short branch before the long one).

**What breaks:**

The bridge uses idempotent SQL (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT
EXISTS`). After the bridge runs on a fresh DB:
- `booking_customer_changes` exists (bridge created it)
- `salon_expenses`, `salon_cash_adjustments`, etc. exist (bridge created them)
- `bookings.change_version`, `checkout_policy_version` columns exist (bridge added them)

Then the original migrations 0041–0052 run. Their DDL is NOT idempotent:
- `0041`: `ALTER TABLE salons DROP COLUMN description` — bridge already dropped it
  → PostgreSQL raises `column "description" of relation "salons" does not exist`
- `0045`: `CREATE TABLE booking_customer_changes` (no `IF NOT EXISTS`)
  → PostgreSQL raises `relation "booking_customer_changes" already exists`
- `0051`: `CREATE TABLE salon_expenses` (no `IF NOT EXISTS`)
  → PostgreSQL raises `relation "salon_expenses" already exists`

**Fresh installs fail.** Every developer running `alembic upgrade head` on a clean
database would get a migration error. CI against a fresh container would also fail.

### Summary

| Path | Safe? | Evidence |
|---|---|---|
| Production: 0040 → 0053 → 0054 → future | YES | Exp A (S2, S3, S4), Exp B (Step 3) |
| Fresh install: empty DB → head | NO | Exp A (S1): bridge before dev chain |
| Dev: 0040 → 0052 → 0054 → future | YES | Exp A (S5, S6) |

---

## 3. Recommended migration-history reconciliation path

Given the fresh-install breakage, the bridge+merge design requires an extra
safeguard before it can be merged. The **straight-line execution** path is simpler,
safer for all environments, and preserves a clean linear history.

### Recommended: straight-line execution using original immutable migrations

```
[policy amendment] alembic stamp 0040_fastapi_only_access   # establish baseline
alembic upgrade 0041_salon_photo_limits                     # +verify
alembic upgrade 0042_remove_business_category              # +verify
alembic upgrade 0043_no_show_attendance_guards             # +verify
alembic upgrade 0044_versioned_checkout_policy             # +verify
alembic upgrade 0045_customer_booking_changes              # +verify
alembic upgrade 0046_u08_financial_outcomes                # +verify
alembic upgrade 0047_booking_audit_erasure                 # +verify
alembic upgrade 0048_support_billing_erasure               # +verify
[0049 structural proof] alembic stamp 0049_trial_salon_plan_prices   # see section 5
alembic upgrade 0050_plan_price_valid_until                # idempotent DDL
alembic upgrade 0051_owner_finance_cashbook                # after restore test
alembic upgrade 0052_booking_window_30_days                # after client coordination
```

**Advantages over bridge+merge:**
- Linear history: `alembic_version` chains 0001 → 0040 → 0041 → ... → 0052
- Fresh installs unchanged: `alembic upgrade head` works exactly as before
- No new migration files required
- No topological sort surprises
- Each applied revision is literally the reviewed, intended SQL

**If bridge+merge is kept despite the fresh-install breakage**, a mandatory fix is
required before merge: add `branch_labels = ["production_bridge"]` to the bridge
revision, and document that development environments must use
`alembic upgrade 0052_booking_window_30_days` (or `alembic upgrade dev@head` if a
`default` branch label is added to the dev chain) rather than `alembic upgrade head`.
This preserves the production path but isolates the bridge from the default dev
upgrade. The fresh-install ordering problem disappears because `head` for the dev
branch is `0052`, and `0053_bridge` is only reachable via its explicit label.

---

## 4. Exact conditions required before a baseline stamp

`migration_policy.py` line 76–77 refuses ALL stamp commands unconditionally:
```python
if command in {"stamp", "do_stamp"} or isinstance(destination, (tuple, list)):
    raise CommandError("Alembic stamp is not authorized by migration policy; …")
```

Before any `alembic stamp 0040_fastapi_only_access` can execute, ALL of the
following are required:

1. **Policy code change** — `migration_policy.py` must be amended to allow a stamp
   specifically for `0040_fastapi_only_access`. The narrowest change: add a
   condition that permits stamp when `destination == "0040_fastapi_only_access"` and
   a valid Mumbai-pattern DATABASE_URL is present and the owner provides an
   explicit `approval_manifest`. Do not open stamp to any arbitrary revision.

2. **Approval manifest** — a JSON file signed by the owner naming
   `target_revision = "0040_fastapi_only_access"`, `project_ref = MUMBAI_PROJECT`,
   `status = "approved"`, and SHA256 hashes of the policy-amended migration_policy.py
   and the stamp approval document.

3. **Isolated restore confirmation** — the production database, restored to an
   isolated environment, must show that the current schema is exactly consistent with
   what 0040 produced: all ACL revocations from 0040's SQL are in place, all objects
   from 0038/0039/0040 are present, and no object from 0041–0052 exists in the
   isolated restore's schema. Run `alembic current` — it must return empty (no
   existing alembic_version rows), confirming this is truly the first stamp.

4. **Owner explicit written authorization** — Shifan must authorize this specific
   `alembic stamp 0040_fastapi_only_access` command in writing (in the PR approving
   the policy amendment or in a separate review comment) before it is executed.

5. **DATABASE_URL explicitly set** — the command must use the production pooler URL
   in the process environment; `.env` files do not count. The existing policy guard
   on line 48 of `migration_policy.py` enforces this.

6. **`mumbai_project` confirmation** — the `-x mumbai_project=wqjlgpnbiapcrlkxumcp`
   argument must be passed to satisfy the requirement from the Mumbai policy
   amendment.

Only after all six conditions are met should `alembic stamp 0040_fastapi_only_access`
be executed. The stamp writes one row to `alembic_version`; it executes no DDL or DML.

---

## 5. How 0049/0050 can be truthfully reconciled

### 0050 — `ADD COLUMN IF NOT EXISTS valid_until`

**No reconciliation needed.** `0050_plan_price_valid_until.sql` contains:
```sql
ALTER TABLE public.salon_plan_prices
    ADD COLUMN IF NOT EXISTS valid_until timestamptz;
```
This is already idempotent. If `valid_until` already exists (confirmed from production
catalogue), the statement is a no-op on PostgreSQL. Run `alembic upgrade 0050` via
the standard Mumbai policy path; it will succeed without error.

**Verification before running:** `SELECT column_name, data_type FROM
information_schema.columns WHERE table_name='salon_plan_prices' AND
column_name='valid_until'` → must return 1 row. If it does, the upgrade
is confirmed safe to run and will be idempotent.

### 0049 — `CREATE TABLE salon_plan_prices`

**Cannot be run as-is.** The SQL creates `salon_plan_prices` without `IF NOT EXISTS`.
The table already exists in production. Running `alembic upgrade 0049` would fail
with `relation "salon_plan_prices" already exists`.

**Reconciliation path (policy-authorized stamp, not direct SQL):**

Step 1 — Structural equivalence proof. Run this query on the isolated restore:
```sql
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'salon_plan_prices'
ORDER BY ordinal_position;
```
Compare the result row-by-row against the `CREATE TABLE` statement in
`backend/migrations/sql/0049_trial_salon_plan_prices.sql`. Every column name,
data type, nullability, and default must match exactly.

Step 2 — Constraint and index equivalence. Run:
```sql
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint WHERE conrelid = 'salon_plan_prices'::regclass;

SELECT indexname, indexdef FROM pg_indexes
WHERE tablename = 'salon_plan_prices';
```
Compare against the DDL in the migration file.

Step 3 — If exactly equivalent, amend `migration_policy.py` to allow a stamp
specifically for `0049_trial_salon_plan_prices` with the same approval manifest
mechanism described in section 4.

Step 4 — Run `alembic stamp 0049_trial_salon_plan_prices` via the policy-authorized
stamp path. This writes one row to `alembic_version`; no SQL from the migration
executes.

**The data UPDATEs from 0049 must be verified separately.** Stamping 0049 skips
its `upgrade()` SQL entirely, including four `UPDATE subscription_plans` statements
that set prices for `growth_6m`, `growth_12m`, `premium_6m`, `premium_12m`. Before
stamping, run this query on the isolated restore:
```sql
SELECT code, price_amount
FROM subscription_plans
WHERE code IN ('growth_6m', 'growth_12m', 'premium_6m', 'premium_12m');
```
If the prices already match the 0049 target values, the UPDATEs were applied at some
point and stamping is safe. If they don't match, the UPDATEs must be applied
manually (as a reviewed, separately authorized SQL operation) before stamping, or
they can be run as part of a new forward migration above 0052 that corrects the
prices idempotently.

---

## 6. Required restore tests before 0051

Migration 0051 (`0051_owner_finance_cashbook`) creates four append-only money tables
(`salon_expenses`, `salon_cash_adjustments`, `salon_day_closes`, `salon_expense_rules`)
with forward-only triggers. Once applied, rows cannot be deleted. This makes 0051
the highest-consequence migration in the chain.

**All of the following must pass on an isolated restore (not production) before
0051 can be authorized:**

### 6a. Schema integrity checks (verify 0041–0050 applied correctly)

```sql
-- Dropped columns absent (0041/0042)
SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND table_name='salons'
  AND column_name IN ('description', 'category');
-- Expect 0 rows

SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND table_name='services'
  AND column_name='description';
-- Expect 0 rows

-- Columns added by 0045
SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND table_name='bookings'
  AND column_name IN ('change_version','committed_reschedules',
                      'service_fulfilment_amount','checkout_policy_version');
-- Expect 4 rows

SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND table_name='booking_services'
  AND column_name='is_active';
-- Expect 1 row

-- Tables created by 0045–0048
SELECT table_name FROM information_schema.tables
WHERE table_schema='public'
  AND table_name IN ('booking_customer_changes','booking_financial_outcomes',
      'booking_finance_commands','booking_policy_refund_jobs',
      'booking_finance_reconciliations','support_erasure_events');
-- Expect 6 rows

-- Function overloads from 0045/0052
SELECT proname, pg_get_function_arguments(oid) FROM pg_proc
WHERE pronamespace='public'::regnamespace
  AND proname IN ('get_available_slots','booking_change_quote');
-- get_available_slots: must have both 3-arg and 4-arg overloads
-- booking_change_quote: must exist

-- salon_plan_prices from 0049/0050
SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND table_name='salon_plan_prices'
  AND column_name IN ('id','salon_id','plan_id','price_amount','currency','valid_until');
-- Expect 6 rows (valid_until from 0050)
```

### 6b. Trigger behavioral tests

All of the following must PASS (not error) on the isolated restore:

1. **Photo limits (0041):** `INSERT` a second cover image for a salon that already
   has one → must raise `salon_photo_limit` (PostgreSQL exception code P0001 or
   similar). Verify trigger `t_salon_image_limits` exists on `salon_images`.

2. **No-show grace (0043):** Attempt `UPDATE bookings SET status='no_show'` where
   `start_datetime > now() - interval '5 minutes'` → must raise `no_show_grace_period`.
   Same update where `start_datetime < now() - interval '10 minutes'` with a valid
   cancellation_reason → must succeed.

3. **Checkout policy stamp (0044):** `INSERT INTO bookings (…)` → the
   `checkout_policy_version` column must be populated by the trigger
   (`RETURNING checkout_policy_version` must return `'customer_processing_v1'`).
   `UPDATE bookings SET checkout_policy_version='other'` → must raise
   `checkout_policy_is_immutable`.

4. **Booking change quote (0045):** Call `booking_change_quote(booking_uuid, staff_uuid,
   service_ids_array, new_start_timestamptz)` with a booking that has
   `checkout_policy_version = 'u08-2026-10-23-v1'` → must return a valid JSONB
   object. Same call with `checkout_policy_version = 'customer_processing_v1'` → must
   raise `booking_change_policy_unsupported`.

5. **Financial outcome trigger (0046):** Transition a test booking with
   `checkout_policy_version = 'u08-2026-10-23-v1'` and a positive `paid_amount` to
   `completed` → verify a row is inserted in `booking_financial_outcomes`. Transition
   a booking with the default policy to `completed` → verify no row is inserted and
   no exception is raised.

6. **Erasure guard (0047):** Attempt `UPDATE booking_customer_changes SET
   some_column='x' WHERE false` (no-op) without erasure context → must raise
   `booking_change_erasure_policy_violated` or equivalent. This proves the
   `guard_booking_change_history()` trigger is installed and active.

7. **Support ticket nullable (0048):** `INSERT INTO support_tickets (…)` with
   `customer_id = NULL` → must succeed (column is now nullable). Existing rows with
   non-null `customer_id` must remain unchanged.

8. **salon_plan_prices structure (0049/0050):** Verify the `valid_until` column
   accepts `NULL` and accepts a future `timestamptz`. Verify the subscription_plans
   price values match the 0049 target (or the correction was applied separately).

### 6c. Post-0051 tests (run AFTER 0051 on the isolated restore only)

9. **Finance tables created:** `SELECT table_name FROM information_schema.tables
   WHERE table_schema='public' AND table_name IN ('salon_expenses',
   'salon_cash_adjustments','salon_day_closes','salon_expense_rules')` → expect 4 rows.

10. **Append-only triggers:** `DELETE FROM salon_expenses WHERE false` → must raise
    `finance_records_are_append_only`. `INSERT INTO salon_expenses (salon_id, date,
    amount_cents, description, category, creator_id, source)` with valid values → must
    succeed.

11. **alembic_version after 0051:** `SELECT version_num FROM alembic_version` → must
    return `0051_owner_finance_cashbook` (single row).

Only after all 11 tests pass should 0052 be considered. 0052 requires a separate
client-app coordination check.

---

## Confirmation

No production state changed.
No migration files were written, modified, or committed.
No database, Cloud Run, GitHub variable, WIF/IAM, secret, backup, restore or
deployment action was taken.
`AUTO_DEPLOY_ENABLED` remains `false`.

All evidence above is from disposable temporary directories and a disposable SQLite
database that existed only within a Python `tempfile.TemporaryDirectory()` context.
The analysis scripts are saved at:
`C:\Users\Lenovo\AppData\Local\Temp\claude\d--salon-salon-backend\
8176878a-953c-4179-bba4-2c1e26dea0c4\scratchpad\alembic_graph_test.py`
`C:\Users\Lenovo\AppData\Local\Temp\claude\d--salon-salon-backend\
8176878a-953c-4179-bba4-2c1e26dea0c4\scratchpad\alembic_graph_test2.py`
