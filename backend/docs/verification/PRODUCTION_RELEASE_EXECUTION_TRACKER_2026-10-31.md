# Production Release Execution Tracker — 2026-10-31

**Project:** Salones backend — Mumbai (wqjlgpnbiapcrlkxumcp)  
**Branch:** shifan  
**Tracker created:** 2026-10-31  
**AUTO_DEPLOY_ENABLED:** false (production environment variable; unchanged until Gate C signed)

---

## Safety constraints (non-negotiable)

- Never rewrite historical migrations (0041-0052 are immutable).
- Never stamp a revision without approved equivalence evidence.
- Never deploy an old image after a newer main commit exists.
- Never enable automatic deployment before successful migration and release verification.
- Never expose credentials or customer data.
- Never silently change subscription prices.
- Never run any Phase 5 action without explicit owner approval.
- `AUTO_DEPLOY_ENABLED` remains false until Gate C signed.

---

## Approved prices (owner confirmed 2026-10-31, Path A)

| Plan | Authoritative production price |
|------|-------------------------------|
| growth_1m | ₹499.00 |
| growth_6m | ₹2,000.00 |
| growth_12m | ₹2,999.00 |
| premium_6m | ₹2,875.00 (unchanged from 0049 SQL target) |
| premium_12m | ₹5,032.00 (unchanged from 0049 SQL target) |

Source: owner business decision recorded in
`backend/docs/verification/0049_SUBSCRIPTION_PRICE_RECONCILIATION_2026-10-31.md`, Path A.

> Note: 0049 SQL migration sets 1675/2932 on a clean DB from 0031 seed. Production prices diverged
> to 2000/2999 after 0049 was applied directly. Tests that replay 0049 SQL assert 1675/2932 correctly.

---

## Phase status

| Phase | Status | Evidence |
|-------|--------|---------|
| Phase 0 — Continuity and safety check | ✅ COMPLETE | This document. |
| Phase 1 — Resolve 0049 price drift locally | ✅ COMPLETE | All fixtures, docs, and tests updated. 1834 pass. |
| Phase 2 — Complete harness, verify CI/CD | 🔧 PREPARATION COMPLETE — REAL RESTORE VERIFICATION PENDING | Harness code extended; advisories added; CI/CD verified. Schema/lock/rollback claims unverified until Phase 3 passes. |
| Phase 3 — Isolated restore rehearsal | ✅ GATE B ISOLATED FULL-DATA REHEARSAL PASSED | All 9 post-gate-b checks PASS against real production data. 1834 tests pass. Awaiting production maintenance-window approval. |
| Phase 4 — Release readiness review | ⏸ NOT STARTED | Requires owner Gate B approval before proceeding. |
| Phase 5 — Production execution | 🚫 BLOCKED — requires explicit owner approval | Gate C not authorized. |

---

## Phase 1 checklist

### Code changes — COMPLETE

- [x] `backend/tests/prices.py` — NEW canonical price module (499/2000/2999); all fixtures import from here
- [x] `backend/scripts/migrations/reconciliation_harness.py` — `EXPECTED_0049_PRICES`: growth_1m=499, growth_6m=2000, growth_12m=2999
- [x] `backend/tests/support_subscription.py` — FakeBillingRepo.PLAN: growth_1m 349→499 (via prices.py), growth_6m 1675→2000
- [x] `backend/tests/unit/test_subscription_billing.py` — all plan-price assertions and webhook paise updated (349→499, 34900→49900)
- [x] `backend/tests/unit/test_cashfree_subscription.py` — mock HTTP handler amounts updated (349→499)
- [x] `backend/tests/unit/test_plan_prices.py` — FakePlanRepo 349→499, discount calc 279.20→399.20, "must be below" boundary 349→499
- [x] `docs/website/subscription-checkout-prompt.md` — example prices 1675→2000
- [x] `backend/docs/verification/ISOLATED_RESTORE_EVIDENCE_TEMPLATE.md` — expected price table 1675/2932 → 2000/2999
- [x] `docs/Salon-Owner-App-Backend-API-Document.md` — growth_1m example 349→499, paise 34900→49900

### Regression tests added — COMPLETE

- [x] `test_canonical_prices_module_matches_harness_expectations` — prices.py constants == harness EXPECTED_0049_PRICES
- [x] `test_fake_billing_repo_plan_matches_canonical_prices` — FakeBillingRepo.PLAN matches prices.py
- [x] `test_harness_expected_prices_match_owner_approved_values` — harness constants are 499/2000/2999
- [x] `test_0049_sql_guards_will_not_fire_at_approved_prices` — guards check 1499/1999, not current prices

### Tests NOT changed (correct for what they test)

| File | Why unchanged |
|------|---------------|
| `test_plan_prices_sql.py:226-243` | Replays immutable 0049 SQL on fresh DB; SQL sets 1675/2932 from 0031 seed — assertions are correct. |
| `test_subscription_billing_sql.py:172` | Same: tests 0049 SQL migration output on a fresh local DB. |
| `docs/deploy/codex-0049-subscription-deploy-prompt.md` | Historical deployment record for what 0049 SQL did (1675/2932). Accurate as a historical artifact. |

### New unit tests required

- [ ] Harness EXPECTED_0049_PRICES match approved prices (2000/2999/499)
- [ ] 0049 structural equivalence check passes when prices match approved values
- [ ] Alembic stamp does not fire 0049 price guards (guards check for 1499/1999 — not current prices)
- [ ] No automatic price update is attempted when prices are already at approved values

### Validation

- [ ] `python -m pytest -q` — full backend tests pass
- [ ] `python -m ruff check app tests migrations` — no lint errors
- [ ] `git diff --stat` reviewed — no unexpected files changed
- [ ] No secrets in diff

---

## Phase 2 checklist — PREPARATION COMPLETE (restore verification pending)

- [x] Harness phases added: `preflight`, `0049-equivalence`, `schema-check`, `post-0041-0048`, `post-gate-b`, `post-0050`, `post-0051`, `post-0052`, `report`
- [x] 0041 destructive DDL check: verifies salons.description, services.description dropped; t_salon_image_limits trigger created
- [x] 0042 destructive DDL check: verifies salons.category dropped
- [x] Lock-timeout / write-freeze advisory added to `schema-check` and `post-0041-0048` phases
- [x] PITR advisory added to `preflight` phase: Supabase PITR enabled; Gate A restore must use local Docker, not production PITR
- [x] Maintenance-window approach documented in advisories: write-freeze required before 0041; rollback = restore-from-backup
- [x] CI/CD workflow verified: `cloud-run-auto.yml` gates on `AUTO_DEPLOY_ENABLED`, restricts to `refs/heads/main`, requires merged-PR proof
- [x] All harness tests: 86 passed, 6 skipped
- [x] Ruff clean on harness and all changed files

---

## Phase 3 checklist — FULL-DATA RESTORE REHEARSAL COMPLETE

### Schema-only rehearsal (superseded by full-data restore below)
- [x] Schema-only rehearsal completed (GATE_A_ISOLATED_RESTORE_EVIDENCE_2026-10-31.md)
- [x] All harness phases passed against schema-only restore with synthetic prices
- [x] Superseded: premium_1m was synthetic 599; real value is 699

### Full-data restore rehearsal (authoritative)
- [x] Fresh encrypted backup: roles + schema + data dumps, all SHA256-verified
- [x] Backup manifest `BACKUP_MANIFEST_20261031T061145Z.json` with row counts and timestamps
- [x] `salon_fullrestore` DB created: `salon_restore_rollback_test` template (correct pre-migration schema)
- [x] Real production data decrypted and applied (no plaintext intermediate) — 26 tables, exact row counts
- [x] `RESTORE_DB_URL=127.0.0.1:15432/salon_fullrestore`, `MUMBAI_PROJECT_CONFIRM=wqjlgpnbiapcrlkxumcp`
- [x] Harness: `preflight` → all PASS — alembic empty, tables present, ACL correct
- [x] Harness: `0049-equivalence` → all PASS — real prices 499/2000/2999/699/2875/5032 verified
- [x] Gate B sequence: stamp 0040, apply 0041-0048, stamp 0049, apply 0050 — all succeeded against real data
- [x] 0041 UPDATE 5 — confirmed running against real salon rows
- [x] Harness: `post-0041-0048` → all PASS (description/category dropped, trigger created)
- [x] Harness: `schema-check` → all PASS
- [x] Harness: `post-0050` → PASS
- [x] Harness: `post-gate-b` → all PASS (9/9 checks against real data)
- [x] Harness: `report` → FAIL expected (alembic=0050, 0051/0052 Gate C)
- [x] New evidence JSONs saved (7 files, timestamps 06:19-06:25)
- [x] SHA256 computed and recorded in GATE_A_ISOLATED_RESTORE_EVIDENCE_FULL_DATA_2026-10-31.md
- [x] Lock-timeout test: LOCK TABLE + SET LOCAL pass inside transaction (PASS)
- [x] Backend test suite: 1834 passed, 301 skipped — EXIT 0
- [x] Rollback rehearsal: `salon_fullrestore_rollback` — 45 tables, alembic empty, description present, real data — PASS
- [x] Gate C assessed: 0051 additive (can apply first), 0052 BLOCKER (behavioral change)
- [x] Table count reconciliation: 45 public vs 84 all-schema — documented and explained
- [ ] Owner reviews Gate A evidence and approves production maintenance window
- [ ] Docker container stopped and removed after owner sign-off

---

## Phase 4 checklist

- [ ] All Phase 3 items confirmed complete
- [ ] Gate A evidence reviewed against stop conditions
- [ ] Gate B manifest prepared with SHA256 hashes of all revision files
- [ ] Client compatibility confirmed (see PRODUCTION_MIGRATION_EXECUTION_RUNBOOK.md)
- [ ] Maintenance window approach chosen (Option 1 recommended for destructive migrations)
- [ ] Owner asked final approval question

---

## Phase 5 (BLOCKED — explicit owner approval required)

> Do not proceed with any Phase 5 action until the owner has reviewed Phase 4's
> single final approval question and provided explicit written approval.

Production execution steps (Gate B, when authorized):
1. Start maintenance window / write freeze.
2. Take final production backup.
3. Stamp 0040, upgrade 0041→0048, equivalence-check+stamp 0049, upgrade 0050.
4. Verify with `alembic current`, harness schema-check, API smoke test.
5. End maintenance window.

Gate C (separate authorization required):
- 0051 finance tables, 0052 booking window, `AUTO_DEPLOY_ENABLED=true`.

---

## Key evidence files

| File | Purpose |
|------|---------|
| `backend/docs/verification/0049_SUBSCRIPTION_PRICE_RECONCILIATION_2026-10-31.md` | Price audit and Path A decision |
| `backend/docs/verification/GATE_A_ISOLATED_RESTORE_EVIDENCE_2026-10-30.md` | Gate A stopped — price mismatch (superseded) |
| `backend/docs/verification/GATE_A_ISOLATED_RESTORE_EVIDENCE_2026-10-31.md` | Gate A schema-only rehearsal (superseded) |
| `backend/docs/verification/GATE_A_ISOLATED_RESTORE_EVIDENCE_FULL_DATA_2026-10-31.md` | **Gate A full-data rehearsal — all Gate B checks PASS — awaiting owner approval** |
| `backend/docs/verification/ISOLATED_RESTORE_EVIDENCE_TEMPLATE.md` | Template for next Gate A run |
| `backend/docs/verification/PRODUCTION_MIGRATION_EXECUTION_RUNBOOK.md` | Corrected three-gate runbook |
| `.github/workflows/cloud-run-auto.yml` | CI/CD workflow (verified: AUTO_DEPLOY_ENABLED gate confirmed) |

---

## Stop conditions

Any of these stops all further work immediately:

- Any production database, Supabase, Cloud Run, or GitHub settings action before Phase 5 approval.
- Any migration stamp or upgrade without Gate B manifest signed.
- AUTO_DEPLOY_ENABLED set to true without Gate C authorization.
- Any secret appearing in a diff, log, or document.
- Any price shown to a customer that does not match owner-approved 499/2000/2999.
