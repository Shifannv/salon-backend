# 0049 Subscription price reconciliation

**Date:** 2026-10-31  
**Type:** Read-only evidence audit  
**Prepared for:** Owner decision before Gate A is rerun

**Safety:** No production, database, Supabase, Cloud Run, GitHub, migration, or deployment action was taken. No secrets were read.

---

## 1. Summary finding

The Growth 6-month and Growth 12-month prices currently live in production do **not** match any migration file value. They appear to be a deliberate business price update made directly to the production database between 2026-10-28 and 2026-10-30. No commit, verification document, or approval record in this repository documents that change. This creates a blocker before Gate A can be rerun and before 0049 can be stamped.

---

## 2. All sources of evidence, with exact prices

### 2a. Migration 0031 — seed (INSERT baseline)

File: `backend/migrations/versions/0031_seed_subscription_plans.py`  
Statement: `INSERT ... ON CONFLICT (code) DO NOTHING`

| Plan code | Seeded price |
|-----------|-------------|
| growth_1m | ₹349.00 |
| growth_6m | ₹1,499.00 |
| growth_12m | ₹1,999.00 |
| premium_1m | ₹599.00 |
| premium_6m | ₹2,499.00 |
| premium_12m | ₹3,499.00 |

These are the only prices 0049's UPDATE guards will accept as "still at seed."

### 2b. Migration 0049 — original commit (2026-10-27 initial)

Commit `8edf2f4` applied first. Original 0049 SQL set prices as: 10% and 20% off seed values.

| Plan code | Price in original 0049 |
|-----------|------------------------|
| growth_6m | ₹1,885.00 |
| growth_12m | ₹3,350.00 |
| premium_6m | ₹3,235.00 |
| premium_12m | ₹5,750.00 |

### 2c. Migration 0049 — revised commit (2026-10-27 same day, 6ff578f)

Commit `6ff578f`: "feat: 6-month plans save 20% and yearly plans save 30%"  
Guard condition: only fires if price still equals the 0031 seed value.

| Plan code | Guard condition | Migration target price |
|-----------|----------------|------------------------|
| growth_6m | price = 1499.00 | **₹1,675.00** |
| growth_12m | price = 1999.00 | **₹2,932.00** |
| premium_6m | price = 2499.00 | ₹2,875.00 |
| premium_12m | price = 3499.00 | ₹5,032.00 |

This is the version currently in `backend/migrations/sql/0049_trial_salon_plan_prices.sql`.

### 2d. SUBSCRIPTION_0049_STAGING_2026-10-27.md — postflight after 0049 direct SQL apply

File: `backend/docs/verification/SUBSCRIPTION_0049_STAGING_2026-10-27.md`

> "Growth monthly/6-month/12-month prices: 349 / 1675 / 2932."

Confirmed that at **2026-10-27 14:31:34 UTC** (20:01 IST), immediately after 0049 was applied directly to the production database:

| Plan | Confirmed price |
|------|----------------|
| growth_1m | ₹349.00 |
| growth_6m | ₹1,675.00 |
| growth_12m | ₹2,932.00 |

0049's guards fired: prices were still at 0031 seed values at that moment.

### 2e. subscription-percentage-release-2026-10-28.md — Oct 28 offer feature release

File: `backend/docs/verification/subscription-percentage-release-2026-10-28.md`

> "For Mentrex Growth Monthly, entering 20% calculated and saved INR 399.20 against the current normal INR 499."

> "Final read-only database verification confirmed zero overrides, all six plan prices unchanged and Mentrex's original INR 499 monthly price."

Two things are visible in this document:

**Finding A — growth_1m = ₹499 (CONFIRMED, undocumented change)**  
At the time of the Oct 28 offer test, the Growth Monthly catalog price was already ₹499, not ₹349 (the 0031 seed). This change happened before Oct 28 and is not tracked in any migration or approval record.

**Finding B — "all six plan prices unchanged" after test cleanup**  
The per-salon offer (in `salon_plan_prices`) was created and deleted. The six catalog prices in `subscription_plans` were not modified by the test. This means growth_6m was still **₹1,675** and growth_12m was still **₹2,932** as of Oct 28 evening.

### 2f. GATE_A_ISOLATED_RESTORE_EVIDENCE_2026-10-30.md — production backup snapshot

File: `backend/docs/verification/GATE_A_ISOLATED_RESTORE_EVIDENCE_2026-10-30.md`  
Backup taken: **2026-10-30 06:46:59 UTC** (~12:16 IST)

| Plan code | Gate A found | Harness expected | Match |
|-----------|-------------|-----------------|-------|
| growth_6m | ₹2,000.00 | ₹1,675.00 | **FAIL** |
| growth_12m | ₹2,999.00 | ₹2,932.00 | **FAIL** |
| premium_6m | ₹2,875.00 | ₹2,875.00 | PASS |
| premium_12m | ₹5,032.00 | ₹5,032.00 | PASS |

### 2g. Website checkout prompt — docs/website/subscription-checkout-prompt.md

> "Pay ₹1,675"

The website checkout build instructions reference "Pay ₹1,675" as the example price for Growth 6-month. This document was written when the 0049 migration prices (1675/2932) were the intended catalog prices. The document has not been updated to reflect 2000/2999.

### 2h. SUBSCRIPTIONS.md and PAYMENT_DECISIONS.md — stale design docs

Both files reference the pre-0049 seed prices (growth_6m=1,499; growth_12m=1,999). These are stale and do not reflect the current production state.

### 2i. No document records the 2000 / 2999 change

A search of all files in `backend/docs/`, `backend/.artifacts/`, and the full git log between Oct 27 and Oct 30 found no commit, verification document, approval record, or admin action record that describes or authorizes changing growth_6m from 1675 to 2000 or growth_12m from 2932 to 2999.

---

## 3. Price timeline

| Date | Source | growth_6m | growth_12m | growth_1m |
|------|--------|-----------|------------|-----------|
| 0031 seed | migration | 1,499 | 1,999 | 349 |
| Pre-Oct 28 (unknown date) | Undocumented admin action | — | — | **→ 499** |
| 2026-10-27 20:01 IST | 0049 directly applied | **→ 1,675** | **→ 2,932** | 349 unchanged |
| 2026-10-28 evening | Oct 28 offer test (cleanup confirmed unchanged) | 1,675 | 2,932 | 499 |
| **UNKNOWN DATE/TIME** | **Undocumented price change** | **→ 2,000** | **→ 2,999** | unknown |
| 2026-10-30 12:16 IST | Gate A production backup | 2,000 | 2,999 | not checked |

The undocumented price change occurred between **2026-10-28 ~22:00 IST** and **2026-10-30 12:16 IST**.

---

## 4. Are ₹2,000 / ₹2,999 deliberate or unexplained drift?

**Assessment: most likely deliberate, but unconfirmed.**

Evidence supporting deliberate intent:
- Premium prices (2875, 5032) are unchanged from 0049 targets — only Growth plans changed.
- growth_1m = ₹499 (pre-existing undocumented change) fits a pattern where the owner has been updating prices directly in the database without migrations.
- ₹2,000 ≈ 499 × 4 (four months' price for six months, i.e. "save 2 months")
- ₹2,999 ≈ 499 × 6 (six months' price for twelve months, i.e. "save 6 months"), with a psychological ₹1 below ₹3,000

This pricing logic is consistent with the owner recalculating discounts based on the new ₹499/month rate rather than the original ₹349/month rate.

Evidence against deliberate intent:
- No approval record, commit message, or verification document records this change.
- The checkout prompt document still says "Pay ₹1,675".
- The Oct 28 doc confirms prices were 1675/2932 as of Oct 28 evening, and no further admin action is documented.

**Verdict: unknown at this time. Only the owner can confirm whether 2000/2999 is the intended current business price.**

---

## 5. Recommendation

**Ask the owner to confirm: are ₹2,000 / ₹2,999 the intended Growth plan prices?**

Two paths:

### Path A — Retain ₹2,000 / ₹2,999 (owner confirms these are correct)

1. Owner signs a pricing decision record confirming: growth_6m=2000, growth_12m=2999, growth_1m=499 are the current authorized catalog prices.
2. Update the reconciliation harness's expected values for `0049_subscription_plan_prices` to match: growth_6m=2000, growth_12m=2999.
3. Rerun Gate A from a fresh production backup — the 0049-equivalence check should pass.
4. Update `docs/website/subscription-checkout-prompt.md` and the stale docs to reflect the new prices.
5. Proceed to Gate B.

**Important:** 0049's UPDATE guards check `price_amount = 1499.00` (for growth_6m) and `price_amount = 1999.00` (for growth_12m). Since current prices are 2000/2999, the guards will NOT fire and the stamp is structurally safe — the prices will be preserved as-is. The stamp records structural equivalence only, not price identity.

### Path B — Revert to ₹1,675 / ₹2,932 (owner decides 0049 prices were correct)

1. Owner authorizes restoring the prices to the 0049 migration values.
2. A super-admin executes the guarded UPDATE in production. This requires a separate authorization record.
3. Take a new production backup.
4. Rerun Gate A. The harness should pass with the current expected values.
5. Proceed to Gate B.

**Both paths lead to the same Gate A rerun. Neither path requires any migration file change.**

---

## 6. Whether migration 0049 may be policy-stamped after documented structural equivalence

Yes, subject to the following conditions being met:

1. **Owner confirms the authoritative prices** (Path A or B above — which price is correct).
2. **Harness expected values updated** to match the confirmed prices (Path A requires updating the harness; Path B does not).
3. **Gate A reruns from a fresh backup** and all phases pass, including:
   - `preflight` (PASS in first run — expected to pass again)
   - `0049-equivalence` with updated or unchanged expected prices
   - `schema-check`
   - rollback rehearsal (not run in first Gate A due to stop)
4. **Gate A evidence signed** by the owner.
5. **Gate B manifest** prepared with SHA256 hashes and stop conditions.

The policy stamp for 0049 is already authorized in `migration_policy.py` (`STAMP_ALLOWED_REVISIONS`). The structural reason the stamp is needed (instead of an upgrade) is that the `salon_plan_prices` table was created directly in production outside Alembic — running the 0049 upgrade would fail on `CREATE TABLE salon_plan_prices` because the table already exists (no `IF NOT EXISTS` in the migration SQL).

---

## 7. Exact Gate A checks that must be rerun from a fresh backup

These checks did not run or failed in the first Gate A and must complete before Gate B is authorized:

| Phase | Check | Must-pass condition |
|-------|-------|---------------------|
| `0049-equivalence` | `0049_subscription_plan_prices` | growth_6m = **[owner-confirmed price]**; growth_12m = **[owner-confirmed price]**; premium_6m = 2875; premium_12m = 5032 |
| `schema-check` | All checks | PASS |
| Rollback rehearsal | Backup restored to second local DB; core tables accessible | PASS |

Additionally, if Path A is chosen:
- The harness source file (`backend/scripts/migrations/reconciliation_harness.py`) must be updated to reflect the confirmed prices before running, and the change must be committed and tracked.

---

## 8. Blockers

| # | Blocker | Required action |
|---|---------|----------------|
| B1 | growth_6m and growth_12m prices in production do not match any documented authorized value | **Owner must confirm the authoritative price for each plan** |
| B2 | growth_1m = ₹499 in production; 0031 seed = ₹349 | **Owner should confirm whether 499 is the correct monthly price** (this does not block Gate B but should be reconciled in documentation) |
| B3 | No document records when or why growth_6m changed from 1675→2000, growth_12m from 2932→2999 | A signed pricing decision record must be created before Gate B |
| B4 | Harness expects 1675/2932; current production has 2000/2999 | After B1 resolved: update harness expected values if Path A, or revert prices if Path B |
| B5 | Gate A phase `schema-check` and rollback rehearsal never ran | Must complete in the next Gate A run from a fresh backup |

---

## 9. No production action taken

This document was produced by reading local files and git history only. No Supabase, database, Cloud Run, GitHub, migration, backup, stamp, or deployment action was performed.
