# Production Alembic baseline/bridge strategy — architecture review

**30 October 2026. Read-only architecture review. No production state changed.**
No migrations applied, no files modified, no database, Cloud Run, GitHub or provider system accessed.
`AUTO_DEPLOY_ENABLED` remains `false`.

---

## Critical finding: the migration policy framework

Before addressing the bridge design, a structural constraint discovered by reading
`backend/app/core/migration_policy.py` must be understood. It controls every
`alembic` command at the code level — not only at the shell level.

**`validate_migration_target()` refuses `alembic stamp` unconditionally:**
```python
if command in {"stamp", "do_stamp"} or isinstance(destination, (tuple, list)):
    raise CommandError("Alembic stamp is not authorized by migration policy; …")
```
Any plan that includes `alembic stamp 0040_fastapi_only_access` will be refused by
this guard before any SQL is emitted. The stamp step requires a policy code change first.

**Mumbai upgrades are restricted to `PREPARED_REVISIONS`:**
```python
PREPARED_REVISIONS = (
    "0038_cancellation_compatibility",
    "0039_promotion_search_path",
    "0040_fastapi_only_access",
)
...
if destination not in PREPARED_REVISIONS:
    raise CommandError("Mumbai execution must name a prepared revision explicitly …")
```
Only revisions 0038, 0039, and 0040 are currently authorized as upgrade targets
against the production database. No revision above 0040 — including any bridge
revision — can run until `PREPARED_REVISIONS` is updated and `validate_evidence()`
receives an approved manifest for that revision.

**Every revision from 0041 onward carries a docstring that confirms this:**
```python
# 0041_salon_photo_limits.py
"""Remove salon/service descriptions; keep one cover and two independent slides.

Prepared for review only. Existing Mumbai history must be reconciled separately;
the current migration policy intentionally does not authorize this revision.
"""
```
This is not an oversight — it is a deliberate gate. The policy framework means the
bridge strategy is not purely a migration-file design problem; it requires a policy
code change plus a reviewed approval manifest before any execution.

**Portable CI boundary:**
```python
PORTABLE_CI_REVISION = "0037_customer_processing_charge"
```
Portable CI (disposable loopback Postgres) covers only 0001–0037. Any bridge
isolation test must use a separate mechanism (isolated restore + manual policy
override with a test manifest), not the standard portable CI path.

---

## 1. Can Alembic safely begin at 0041 with no trustworthy baseline revision?

No. Three independent reasons:

**Reason 1 — `alembic_version` has zero rows.**
Alembic requires a starting revision in `alembic_version` to calculate the
migration delta. With zero rows, `alembic upgrade <any-revision>` begins from the
start of the chain (revision 0001). Revision 0001 contains `CREATE TABLE`
statements for the bootstrap schema that already exist in production (packaged into
`salon-api-production-subpct-20261028`). The first statement would fail with
`DuplicateTableError` or equivalent.

**Reason 2 — 0049/0050 were applied outside Alembic.**
`salon_plan_prices` (0049) and its `valid_until` column (0050) exist in production
applied directly as SQL, not through Alembic. Running the 0049 migration file again
without idempotency guards would fail with `relation "salon_plan_prices" already exists`.
Running 0050 would fail with `column "valid_until" of relation "salon_plan_prices"
already exists` (without `IF NOT EXISTS`).

**Reason 3 — Migration policy refuses execution above 0040.**
Even if the `alembic_version` table could be seeded, `validate_migration_target()`
refuses any upgrade target that is not in `PREPARED_REVISIONS`. Revision 0041 is not
in that set. The guard fires before any SQL is emitted.

**Conclusion:** Before any `alembic upgrade` can run against production, three
preconditions must be met: (a) a known, stable Alembic HEAD must be established,
(b) the migration policy must be amended to authorize the new target revision, and
(c) a reviewed approval manifest with exact SHA256 hashes must be prepared.

---

## 2. Is changing historical migration files safe?

**No. Historical migration files must not be modified.** Four reasons:

**Fresh databases.**
Adding `IF NOT EXISTS` guards changes the semantics of a clean install. If a
developer drops and recreates their local database or CI runs against a fresh
container, the idempotent version silently skips failures that the original would
have caught. A fresh database where `booking_customer_changes` already existed from
a partial restore or fixture would silently skip creation instead of raising an
error. This hides real bugs in new setups.

**Existing development databases.**
Any developer who previously ran the original migrations has a database where those
objects exist with the exact expected definitions. After a `git pull` with rewritten
SQL, `alembic upgrade` may silently succeed via IF NOT EXISTS guards while the
existing object definition is stale. Drift goes undetected.

**Auditability.**
Migration files are the authoritative record of what was intentionally applied to
each environment, when, and why. The `validate_evidence()` function in
`migration_policy.py` checks `sha256` hashes of every source file in
`PREPARED_REVISIONS`. Rewriting a migration file changes its hash and immediately
invalidates every prior approval manifest that referenced it. Any rewrite of an
already-prepared revision (0038–0040) would break the entire Mumbai execution path.
A rewrite of 0041–0052 changes the git audit trail in a way that is unrecoverable
after push.

**Rollback.**
All 0041–0052 migrations raise `RuntimeError` from `downgrade()`. Making `upgrade()`
idempotent does not fix downgrade. A partially applied idempotent migration is harder
to detect because the IF NOT EXISTS guard may skip subsequent statements even when
earlier ones ran, obscuring the partial-apply state.

**Verdict:** Do not modify 0041–0052. The correct approach creates new files
(bridge revision, merge revision, amended policy) without touching existing ones.

---

## 3. Comparison of reconciliation approaches

### Approach A — Immutable historical files + new bridge revision + policy amendment

A new migration file `0053_production_baseline_bridge.py` is created with
`down_revision = "0040_fastapi_only_access"`. It absorbs the cumulative effect of
all absent migrations (0041–0048, 0051, 0052) using fully idempotent SQL, and is
transparent about skipping 0049/0050 which already exist.

`migration_policy.py` is amended to add `"0053_production_baseline_bridge"` to
`PREPARED_REVISIONS`. A reviewed approval manifest is prepared for 0053.

For production: establish a baseline stamp via a policy-authorized procedure (see
section 4 for the stamp paradox), then run the bridge. For fresh databases: the
bridge and the full chain (0041–0052) are both descendants of 0040, creating a
branched Alembic tree. A merge revision `0054_merge_prod_and_dev_chains.py` with
`down_revision = ("0052_booking_window_30_days", "0053_production_baseline_bridge")`
unifies both paths for all future migrations.

**Does it falsely mark any migration as applied?**
No. 0041–0052 remain absent from production's `alembic_version`. The bridge revision
carries an explicit name and docstring explaining its role. The chain shows:
`0040 → 0053 (bridge) → 0054 (merge)` for production, and
`0040 → 0041 → … → 0052 → 0054 (merge)` for fresh databases.

**Does it work within the policy framework?**
Partially — requires amending `PREPARED_REVISIONS` and producing an approval
manifest for 0053. The stamp paradox (section 4) requires separate resolution.

**Historical migration rewrites required?** None.

**Supports 0051 finance tables?** Yes — bridge SQL includes them.

**Requires isolated restore test?** Yes — full behavioral test required.

### Approach B — Reconciliation branch with parallel idempotent files

Multiple new migration files mirror 0041–0052 with idempotent SQL, on a separate
git branch. A merge revision joins this branch to the main line. Each file gets a
distinct revision ID from the original.

**Problem:** Multiple files are harder to review atomically than one bridge. The
separate branch creates ongoing confusion about which set of revisions is "the real"
migration chain for production vs. development. Each additional file requires a
separate entry in `PREPARED_REVISIONS` and a separate approval manifest.

**Verdict:** More complex than Approach A with no benefit. Not recommended.

### Approach C — Squashed migration replacing 0041–0052

A new revision `0041_production_squash` has `down_revision = "0040_fastapi_only_access"`
and represents all of 0041–0052 in one file. Historical revisions 0041–0052 are
deleted from `migrations/versions/`.

**Problem:** Deleting 0041–0052 breaks development databases that already ran them.
Their HEAD is at 0052; there is no path to `0041_production_squash`. Unresolvable
chain discontinuity for every developer. Also invalidates the git audit trail.

**Verdict:** Destructive to existing development environments. Not recommended.

### Approach D — Rewriting old migrations with idempotent guards

Addressed in section 2. Invalidates approval manifest SHA256 hashes. Not
recommended.

---

## 4. Recommended approach: A, with explicit stamp paradox resolution

### The stamp paradox

`migration_policy.py` line 76–77:
```python
if command in {"stamp", "do_stamp"} or isinstance(destination, (tuple, list)):
    raise CommandError("Alembic stamp is not authorized by migration policy; …")
```

The bridge plan requires `alembic stamp 0040_fastapi_only_access` to establish a
known starting point. This command is refused by policy.

**Resolution options (both require owner authorization):**

**Option 1 — Temporary policy suspension for the stamp-only step.**
Add `"0040_fastapi_only_access"` as an explicitly allowed stamp target (or
temporarily disable the stamp guard for this one command) in a reviewed PR.
The PR is merged, the stamp is run with the production database credentials and
confirmed, then the temporary allow is removed in a follow-up PR before any upgrade
is attempted. The stamp command produces a single row in `alembic_version` with no
SQL effects on the schema. The security risk is limited to this one controlled
operation.

**Option 2 — Direct SQL INSERT with owner supervision.**
As a one-time exception, the owner inserts the baseline row directly:
```sql
INSERT INTO alembic_version (version_num) VALUES ('0040_fastapi_only_access');
```
This bypasses Alembic entirely but avoids changing policy code. It requires owner
authorization, a supervised Supabase SQL console session, and is recorded as an
evidence artifact. The production schema is not changed (no DDL). After the insert,
`alembic current` should return `0040_fastapi_only_access`.

**Recommended:** Option 2 for the stamp step, as it avoids any policy code change for
a single INSERT of one known value, and produces a directly auditable SQL log.
Option 1 should be preferred if a policy amendment is being made anyway for the bridge
revision (they can be bundled in one PR).

### Amended implementation model

**Step 0 — Policy amendment PR**
Amend `migration_policy.py`:
- Add `"0053_production_baseline_bridge"` to `PREPARED_REVISIONS`
- If Option 1 stamp: add `"0040_fastapi_only_access"` to an explicit stamp allow-list
  (or accept Option 2 and skip policy change for stamp)
- This PR must be reviewed, merged, and present in the candidate image before any
  bridge execution

**Step 1 — Bridge revision `0053_production_baseline_bridge.py`**
```python
revision = "0053_production_baseline_bridge"
down_revision = "0040_fastapi_only_access"
branch_labels = None
depends_on = None
```
`upgrade()` runs idempotent SQL absorbing the missing schema from 0041–0052.
`downgrade()` raises `RuntimeError` (consistent with all migrations in this chain).

The bridge SQL must use only:
- `CREATE TABLE IF NOT EXISTS` for all new tables
- `CREATE OR REPLACE FUNCTION` / `CREATE OR REPLACE PROCEDURE` for all functions
- `ADD COLUMN IF NOT EXISTS` for all column additions
- `DROP COLUMN IF EXISTS` for column drops (0041/0042)
- `DROP TRIGGER IF EXISTS <name>; CREATE TRIGGER <name>` for triggers
- `CREATE UNIQUE INDEX IF NOT EXISTS` for indexes
- Conditional constraint addition via anonymous `DO $$ BEGIN … EXCEPTION WHEN … END $$` blocks
- Idempotent data updates using `WHERE <condition that is false if already applied>` guards

**Step 2 — Approval manifest for 0053**
Prepare `review-0053.json` containing:
- `approval_id`: a new UUID issued by the owner for this revision
- `project_ref`: `wqjlgpnbiapcrlkxumcp`
- `target_revision`: `0053_production_baseline_bridge`
- `status`: `approved`
- `approved_by`: owner name
- `source_sha256`: SHA256 of the final reviewed `0053_production_baseline_bridge.py`
  and `0053_production_baseline_bridge.sql`
- `review.path`, `review.sha256`, `review.status`: pointing to this document or a
  separate review artifact
- `preflight.path`, `preflight.sha256`, `preflight.status`: pointing to the
  isolated restore evidence document

**Step 3 — Create merge revision `0054_merge_prod_and_dev_chains.py`**
```python
revision = "0054_merge_prod_and_dev_chains"
down_revision = ("0052_booking_window_30_days", "0053_production_baseline_bridge")
branch_labels = None
depends_on = None
```
`upgrade()`: no-op (pure merge point).
`downgrade()`: raises `RuntimeError`.
Add `"0054_merge_prod_and_dev_chains"` to `PREPARED_REVISIONS`.

**Step 4 — Production execution (separately authorized)**
```bash
# Establish baseline (requires owner authorization; see stamp paradox above):
#   Option A (policy): alembic -x migration_policy=mumbai … stamp 0040_fastapi_only_access
#   Option B (SQL):    INSERT INTO alembic_version VALUES ('0040_fastapi_only_access');

# Run bridge (requires approved manifest):
alembic -x migration_policy=mumbai \
        -x mumbai_project=wqjlgpnbiapcrlkxumcp \
        -x approval_manifest=/path/to/review-0053.json \
        -x approval_id=<uuid> \
        upgrade 0053_production_baseline_bridge

# Advance to merge point (same manifest updated or new manifest):
alembic -x migration_policy=mumbai \
        -x mumbai_project=wqjlgpnbiapcrlkxumcp \
        -x approval_manifest=/path/to/review-0054.json \
        -x approval_id=<uuid> \
        upgrade 0054_merge_prod_and_dev_chains
```

**Step 5 — Future production upgrades**
All future migrations: `alembic upgrade <explicit-revision>` from `0054_merge_prod_and_dev_chains`.
Add each new revision to `PREPARED_REVISIONS` with its approval manifest before execution.

---

## 5. Truthfulness: how the bridge records production state without false claims

After bridge execution, `alembic_version` contains `0054_merge_prod_and_dev_chains`.
The Alembic chain shows:

```
0040 → 0053 (bridge, absorbed 0041-0052 effect) → 0054 (merge)
```

Anyone inspecting the chain sees:
- 0041–0052 are present in `migrations/versions/` but were not run on production.
  Their chain from 0041 through 0052 was bypassed via the bridge branch.
- 0053 is explicitly named `production_baseline_bridge` — the name is transparent
  about its purpose.
- The bridge's docstring and this review document explain exactly what it absorbed
  and why.

No revision in `alembic_version` claims that 0041–0052 executed on production.
The bridge's own revision ID (0053) is what was actually applied.

---

## 6. How future upgrades reach 0051 and 0052 safely

The bridge SQL absorbs the cumulative effect of 0051 and 0052 idempotently. After
the bridge completes:
- `salon_expenses`, `salon_cash_adjustments`, `salon_day_closes`, `salon_expense_rules`
  exist (absorbed from 0051 SQL via bridge)
- `get_available_slots` and `create_booking` carry the 30-day window (absorbed from
  0052 SQL via bridge)

Future migrations reference `0054_merge_prod_and_dev_chains` and build on a schema
that includes everything through 0052. On fresh databases, `alembic upgrade head`
runs `0001 → … → 0040 → 0041 → … → 0052 → 0054 → future`. On production after the
bridge, `alembic upgrade head` runs only new migrations above 0054. Both paths
converge at 0054.

---

## 7. Destructive changes, incompatible signatures, and transformations requiring dedicated verification

### Column drops (irreversible data loss if column had values)

| Change | Migration | Pre-bridge verification required |
|---|---|---|
| `ALTER TABLE salons DROP COLUMN description` | 0041 (via bridge) | Query: `SELECT count(*) FROM salons WHERE description IS NOT NULL AND description <> ''`. Any non-null rows represent data that will be permanently dropped. Coordinate with owner app and customer app to remove display of this field before running the bridge. |
| `ALTER TABLE services DROP COLUMN description` | 0041 (via bridge) | Same as above for services. |
| `ALTER TABLE salons DROP COLUMN category` | 0042 (via bridge) | Query: `SELECT count(*) FROM salons WHERE category IS NOT NULL`. If any rows exist, confirm with owner whether this data is worth preserving before bridge execution. |

### Function signature changes (call-site incompatibility)

| Change | Migration | Verification required |
|---|---|---|
| `get_salon_by_qr` returns `NULL::text` for description | 0041 | All QR scan display paths in the walk-in app must tolerate null description. Verify client source code. |
| `get_available_slots(uuid,date,int)` wraps 4-arg version | 0045 | Existing 3-arg Python callers still work. Verify no ORM-level call passes wrong arity. |
| `guard_booking_change_history()` body replaced | 0047 | Test: attempt UPDATE on `booking_customer_changes` without erasure context → must still raise exception. |
| `get_available_slots` and `create_booking` replaced | 0052 | Old customer app versions that book beyond 30 days will receive empty slots or `booking_window_exceeded`. Client rollout coordination required before bridge execution. |

### Trigger replacements

| Trigger | Risk |
|---|---|
| `t_salon_image_limits` (0041) | Blocks photo uploads exceeding 1 cover + 2 slides limit. Existing excess photos are retired by the migration's UPDATE. Test post-bridge: verify trigger fires and blocks over-limit inserts. |
| `booking_no_show_attendance_guard` (0043) | Blocks no-show status before 10-minute grace period. Any existing no-show workflow that marks status immediately will be blocked. |
| `stamp_checkout_policy_tg` (0044) | Every new booking INSERT stamps `checkout_policy_version`. Test: INSERT a booking, verify column returns `'customer_processing_v1'`. |
| `booking_terminal_finance` (0046) | Fires on terminal booking states. Requires `checkout_policy_version = 'u08-2026-10-23-v1'` to write a financial outcome. Default-policy bookings return NULL from the trigger — verify no exception is raised for them. |
| Finance append-only triggers (0051) | Block all DELETE, UPDATE (except erasure), TRUNCATE on money tables. Test: `DELETE FROM salon_expenses WHERE false` → must raise `finance_records_are_append_only`. |

### Data transformations (one-time, irreversible)

| Transformation | Pre-bridge verification required |
|---|---|
| Retired excess salon images (`is_active = false`) | Query: `SELECT salon_id, count(*) FROM salon_images WHERE is_active AND is_main GROUP BY salon_id HAVING count(*) > 1`. Rows indicate salons with multiple covers; the bridge will retire extras. Confirm with owner which cover should survive. |
| `subscription_plans` price UPDATEs (0049) | Query: `SELECT code, price_amount FROM subscription_plans WHERE code IN ('growth_6m','growth_12m','premium_6m','premium_12m')`. Confirm current values match expected 0049 targets. If prices have been admin-edited, the bridge's WHERE guards will skip those rows safely. |
| `support_tickets.customer_id` becomes nullable (0048) | Existing rows are unaffected. Test post-bridge: `SELECT count(*) FROM support_tickets WHERE customer_id IS NULL` — must still return 0. |

---

## 8. Restore-test evidence requirements beyond simple row counts

The isolated restore test must verify behavioral correctness, not just structural
presence. All of the following must pass before the approval manifest can be signed.

### Functional trigger tests

1. **Photo limits (0041):** Insert a second cover image for a salon that already has
   one → must raise `salon_photo_limit`. Insert a third slide image → same. Insert
   into a salon after the bridge's image retirement ran → verify exactly 1 cover and
   ≤ 2 slides remain active.

2. **QR function (0041):** `SELECT * FROM get_salon_by_qr('<valid_qr_token>')` →
   `description` column must be present but NULL.

3. **No-show grace (0043):** Attempt `UPDATE bookings SET status='no_show' WHERE
   start_datetime > NOW() - interval '5 minutes'` → must raise
   `no_show_grace_period`. Same update with `start_datetime < NOW() - interval '10 minutes'`
   and valid reason → must succeed.

4. **Checkout policy stamp (0044):** `INSERT INTO bookings (…) RETURNING
   checkout_policy_version` → must return `'customer_processing_v1'`. Attempt to
   UPDATE `checkout_policy_version` on an existing booking → must raise
   `checkout_policy_is_immutable`.

5. **Booking change (0045):** Call `booking_change_quote(booking_id, staff_id,
   service_ids, new_start)` on a booking with `checkout_policy_version =
   'u08-2026-10-23-v1'` → must return valid jsonb. Same with
   `'customer_processing_v1'` → must raise `booking_change_policy_unsupported`.

6. **Financial outcome (0046):** Transition a test booking with
   `checkout_policy_version = 'u08-2026-10-23-v1'` and `paid_amount > 0` to
   `completed` → verify row inserted in `booking_financial_outcomes`. Transition a
   booking with default policy → verify no row inserted and no exception raised.

7. **Finance append-only (0051):** `DELETE FROM salon_expenses WHERE false` → must
   raise `finance_records_are_append_only`. Valid `INSERT INTO salon_expenses (…)` →
   must succeed.

8. **Booking window (0052):**
   `SELECT count(*) FROM get_available_slots('<staff_id>', CURRENT_DATE + 31, 60)`
   → must return 0 rows. Same with `CURRENT_DATE + 29` on an open salon → must
   return > 0 rows.

### Schema equivalence queries (run on isolated restore after bridge)

```sql
-- Expected columns from 0041–0052 (10 rows expected)
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (
    (table_name = 'bookings'
     AND column_name IN ('change_version','committed_reschedules',
                         'service_fulfilment_amount','checkout_policy_version'))
    OR (table_name = 'booking_services' AND column_name = 'is_active')
    OR (table_name = 'salon_plan_prices' AND column_name = 'valid_until')
    OR (table_name = 'support_tickets'
        AND column_name IN ('retained_restricted','erasure_policy_version'))
    OR (table_name = 'subscription_billing_records'
        AND column_name IN ('benefits_erased_at','benefits_erasure_policy'))
    OR (table_name = 'booking_customer_changes' AND column_name = 'anonymized_at')
  )
ORDER BY table_name, column_name;
-- Expect 10 rows

-- Dropped columns (0 rows expected)
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'salons'
  AND column_name IN ('description', 'category');
-- Expect 0 rows

-- New tables from 0041–0052 (10 rows expected)
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'booking_customer_changes', 'booking_financial_outcomes',
    'booking_finance_commands', 'booking_policy_refund_jobs',
    'booking_finance_reconciliations', 'support_erasure_events',
    'salon_expenses', 'salon_cash_adjustments',
    'salon_day_closes', 'salon_expense_rules'
  );
-- Expect 10 rows

-- Function overloads
SELECT proname, pg_get_function_arguments(oid)
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
  AND proname IN ('get_available_slots', 'create_booking', 'booking_change_quote');
-- get_available_slots: must have both 3-arg and 4-arg overloads
-- create_booking: 1 overload with 30-day window in body
-- booking_change_quote: 1 overload

-- Alembic chain state after bridge (1 row expected)
SELECT version_num FROM alembic_version;
-- Expect: 0054_merge_prod_and_dev_chains (after bridge + merge run)
```

---

## 9. Client compatibility summary

| Change | Owner app | Customer app | Admin | Walk-in QR |
|---|---|---|---|---|
| 0041: DROP description | Null description in UI — breaking if field is required by old code | Same | Same | `get_salon_by_qr` returns NULL description — must tolerate null |
| 0041: Photo limit trigger | Upload attempts for >1 cover or >2 slides rejected — must show error | No impact (read only) | No impact | No impact |
| 0042: DROP category | Category field disappears | No impact | Admin salon list loses category column | No impact |
| 0043: No-show grace | Owner marking no-show <10 min after start will fail | No impact | No impact | No impact |
| 0044: checkout_policy_version | No direct client impact | No direct client impact | No direct client impact | No direct client impact |
| 0045: Booking change functions | Reschedule endpoints become available | Old versions cannot reschedule | No impact | No impact |
| 0046: Financial outcomes | Finance admin features available | No impact | Admin finance views work | No impact |
| 0047/0048: Erasure hardening | No visible client impact | No visible client impact | No visible client impact | No impact |
| 0049: Plan price UPDATEs | Subscription prices change at checkout | No impact | Admin sees new prices | No impact |
| 0050: valid_until on plan prices | Admin can set expiry on per-salon offers | No impact | Admin feature | No impact |
| 0051: Finance cashbook | New finance endpoints available | No impact | No impact | No impact |
| 0052: 30-day booking window | Calendar blocks beyond 30 days | **BREAKING** — availability queries > 30 days return empty; booking attempts fail with `booking_window_exceeded`. Client rollout coordination required. | No impact | Walk-in QR bookings (`p_source='qr_walkin'`) exempt from 30-day check |

**Critical coordination for 0052:** Only customer-app sourced bookings (`p_source = 'app'`)
are subject to the window. The check in `create_booking` is:
```sql
if p_source = 'app' and v_booking_date > v_today + 30 then
    raise exception 'booking_window_exceeded' …
```
Walk-in QR (`'qr_walkin'`) and manual walk-in (`'manual_walkin'`) sources are exempt.

---

## 10. Items requiring owner review before any bridge implementation begins

1. **Bridge SQL content** — the complete SQL of `0053_production_baseline_bridge`
   must be written, reviewed against each absent migration's intent, tested for
   idempotency on the isolated restore, and approved in a PR before production
   execution.

2. **Policy amendment PR** — `migration_policy.py` must be amended to add
   `"0053_production_baseline_bridge"` (and `"0054_merge_prod_and_dev_chains"`) to
   `PREPARED_REVISIONS`. This PR must be separate from or precede the bridge PR.

3. **Stamp baseline authorization** — owner must explicitly authorize the baseline
   `alembic_version` row insertion (either via a policy-authorized stamp or direct
   supervised SQL INSERT) before any upgrade command is issued.

4. **Salon description/category data export** — owner must query and review non-null
   values in `salons.description` and `salons.category` before bridge drops those
   columns. Any data worth preserving must be exported to an external record first.

5. **Excess salon image retirement** — owner must review which salons have >1 cover
   or >2 slides and confirm the retirement logic is acceptable. Retired images
   (`is_active = false`) cannot be recovered after the bridge runs.

6. **0049 subscription_plans price data** — owner must query current `price_amount`
   values for `growth_6m`, `growth_12m`, `premium_6m`, `premium_12m` and confirm
   the 0049 target prices are correct for the current business before bridge
   execution.

7. **0052 customer app coordination** — owner must confirm the customer app release
   plan for the 30-day booking window enforcement. The bridge absorbs 0052 SQL, so
   the window is enforced from the moment the bridge completes. Old customer app
   versions that book beyond 30 days will break.

8. **Isolated restore evidence document** — full evidence from bridge execution on
   the isolated restore (all functional trigger tests and schema equivalence queries
   from section 8) must be produced, reviewed, and included in the approval manifest
   before production execution.

9. **Merge revision correctness test** — `0054_merge_prod_and_dev_chains` must be
   tested on both a fresh database and the isolated restore to confirm Alembic
   produces a valid, single-head tree with no unresolved branches.

10. **Finance endpoint compatibility before code deployment** — the current main
    code registers finance routes unconditionally. Until 0051 tables exist, any
    request to `/v1/salons/me/ledger/…` or `/v1/salons/me/expenses/…` returns 500.
    This must be resolved before the first code-only deployment: either apply 0051
    first, or add a startup guard that returns a 503 when the tables are absent.

---

## Summary

| Question | Answer |
|---|---|
| Can Alembic begin at 0041 with zero rows? | No — fails on 0001, blocked by policy, 0049/0050 already exist |
| Is rewriting historical files safe? | No — invalidates approval manifest SHA256 hashes, breaks audit trail |
| Recommended approach | Approach A: immutable bridge revision (0053) + merge revision (0054) |
| Is alembic stamp authorized by current policy? | No — `validate_migration_target()` refuses it unconditionally |
| What must change in policy code before bridge can run? | Add 0053/0054 to `PREPARED_REVISIONS`; resolve stamp baseline separately |
| Minimum approvals required | 10 items listed in section 10 |
| Production state changed by this review | None |

---

## Confirmation

No production state changed while producing this review.
No migrations applied, no files modified, no database, Cloud Run, GitHub variable,
WIF/IAM, provider system, secret, backup, restore or deployment action was taken.
`AUTO_DEPLOY_ENABLED` remains `false`.
