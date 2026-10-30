# First supervised production release — execution plan

**30 October 2026. Planning document only. No execution has occurred.**
No deployment, migration, cloud mutation, secret access, commit or push was performed while producing this document. `AUTO_DEPLOY_ENABLED` remains `false`.

---

## Current merged CI/CD proof

**Merge commit:** `53af804d4c1937e503bb09293bee4ca85e9986a8`
**Message:** Merge pull request #25 from Shifannv/shifan
**Merged at:** 2026-10-30 01:25:13 +0530

**Merged workflow (`cloud-run-auto.yml`, blob `b18944d0e65d33c8012e32c05b0e9cadae194bb7`):**

- Concurrency at **workflow level** (`production-cloud-run`, `cancel-in-progress: false`) — queue-ordering fix is present.
- Trigger: `push: branches: [main]` only. Feature branch and PR events do not trigger this workflow.
- `gate` job reads `AUTO_DEPLOY_ENABLED` from the `production` environment and calls `cloud_run_auto.py gate`. A false/absent/non-exact value outputs `enabled=false` and produces no external call or cloud authentication.
- `release` job condition: `needs.gate.outputs.enabled == 'true' && ... github.ref == 'refs/heads/main' && github.actor_id == '172572480'`. All GCP authentication steps are behind `if: steps.admit.outputs.eligible == 'true'`.

**Workflow run on merge:** The GitHub Actions plugin was unavailable for direct verification. However, because `AUTO_DEPLOY_ENABLED` is owner-confirmed `false`, `gate()` could only have output `enabled=false`. The `release` job's `if` condition requires `enabled == 'true'`; it is structurally impossible for the deployment branch to have executed. The `gate` and CI jobs are read-only: no cloud authentication, GCP mutation, migration, database access or traffic change could have occurred.

**Static evidence verified locally:**

| Check | Result |
|---|---|
| `python -c "import yaml; d=yaml.load(open('.github/workflows/cloud-run-auto.yml'), Loader=yaml.BaseLoader); assert d['concurrency']['group'] == 'production-cloud-run' and d['concurrency']['cancel-in-progress'] == 'false' and 'concurrency' not in d['jobs']['release']"` | Passes — workflow-level concurrency confirmed, no release-job concurrency |
| `pytest tests/unit/test_release_configuration.py tests/unit/test_cloud_run_auto.py` | 77 passed, 0 failed |
| `PRODUCTION_AUTO_DEPLOY_ENABLED` absent from workflow file | Confirmed |
| `cloud-run-candidate.yml` is a read-only disabled notice | Confirmed |

---

## Production blockers

All of the following must be resolved and owner-approved before `AUTO_DEPLOY_ENABLED` is set to `true`.

### B1 — Migration reconciliation and schema gap (BLOCKING)

**Production baseline image** packages migrations 0001–0040 (confirmed in `bootstrap-subpct-20261028.json`). The Alembic version table has zero rows at last observation; actual applied SQL objects are unknown above 0040 except by direct catalogue inspection.

**Main code requires migrations up to 0052 (`0052_booking_window_30_days`).** The gap is:

| Migration | Content | Risk |
|---|---|---|
| 0041 | Salon photo limits | Previously rehearsed; retention confirmation needed |
| 0042 | Remove business category | Schema-breaking for old owner clients that still send the field |
| 0043 | No-show/attendance guards | Function/policy state not recorded; unknown |
| 0044 | Versioned checkout policy | Function/policy state not recorded |
| 0045 | Customer booking changes | Previously absent; full-file reconciliation needed |
| 0046 | Financial outcomes tables | Payment behavior; separate scope |
| 0047 | Booking audit/erasure | Worker compatibility required |
| 0048 | Support billing erasure | `support_erasure_events` previously absent |
| 0049 | Trial plan prices | Previously applied separately; do not replay |
| 0050 | Plan price `valid_until` | Previously applied separately; do not replay |
| 0051 | Finance cashbook (4 tables, 5 functions) | **Absent at last observation. Forward-only (no downgrade). Append-only money tables.** |
| 0052 | 30-day booking window (`get_available_slots`, `create_booking` replacements) | **Unknown adoption. Breaks old booking clients if applied without client rollout.** |

**No guessed version row stamping, no `alembic upgrade head`, no replaying already-applied files.**

### B2 — Shared staging/production database (BLOCKING)

At last observation, staging and production share `wqjlgpnbiapcrlkxumcp`. A staging migration is a production mutation. An isolated staging database is required before any rehearsal migration run.

### B3 — Bootstrap baseline incompatibility (BLOCKING)

The serving image (`salon-api-production-subpct-20261028`) is a hybrid overlay with no proven single Git source label. The automatic release system requires `BASELINE_COMMIT` to be a proven Git SHA from a source-labelled image. A bootstrap release (separate, supervised path) is required to produce the first source-labelled image before any subsequent automatic or source-verified release can proceed.

The bootstrap path in `cloud_run_candidate.py` is disabled for automatic releases (`require(not bootstrap_enabled(), "Automatic bootstrap is forbidden")`). The first release must be supervised and use the bootstrap path explicitly, with the bootstrap attestation manifest verified against the serving image inventory.

### B4 — Old-client backward compatibility not certified (BLOCKING for 0042/0052)

- **0042 (remove category):** Old owner app versions still send `category`/`description` fields. Must verify strict/lenient schema behavior on deployed API or require a coordinated client rollout.
- **0052 (booking window):** `get_available_slots` and `create_booking` are replaced. Old customer app versions that book outside the 30-day window will receive slot-not-found or rejection errors. Client rollout coordination required, or a separate migration-only release with the old function retained.
- **Finance endpoints (0051):** Routes are registered unconditionally. Until 0051 is applied, any request to `/v1/salons/me/ledger/...` or `/v1/salons/me/expenses/...` will fail with 500 (table not found). Old clients that probe these endpoints will see errors.

### B5 — Erasure worker compatibility (BLOCKING for 0047/0048/0051)

Migration 0047 adds audit/erasure fields. Migration 0051 adds `creator` fields to money tables that must be nulled on erasure. A deployed rollback image (older revision) may omit these new erasure steps. Prove all deployed and rollback-candidate images apply correct erasure before accepting finance or audit entries.

### B6 — Production-environment readback and OIDC not live-verified

The `gate` job reads `AUTO_DEPLOY_ENABLED` from the production environment using `actions: read` permission. The exact `environments/production/variables/AUTO_DEPLOY_ENABLED` API path has not been exercised in a real GitHub Actions run. The `id-token: write` / WIF exchange has not been tested against actual GCP. These require the first supervised run to verify before enabling automatic mode.

### B7 — GitHub Free / private enforcement limitation

Merge protection rules are not enforced server-side on GitHub Free private repositories. Merged-PR admission (`merge_commit_sha` check in `guard()`) reduces direct-push risk but is not equivalent to server-enforced protection. Owner review remains essential. Do not claim server-enforced review.

---

## Required backup and restore test

Before any production migration:

1. Take a named Supabase point-in-time snapshot or `pg_dump` of the production database. Record the exact snapshot timestamp and size.
2. Restore the snapshot to an **isolated** database (not staging, not production). This database must not share any pooler, Supabase project or DNS with production.
3. Run the target migrations against the restore.
4. Verify: all expected tables/functions/triggers exist; all existing bookings, payments, subscriptions, profiles remain readable; erasure worker runs cleanly against test data.
5. Record the backup and restore SHA/timestamp as evidence for the release receipt.

The restore test must be repeated for any migration run that is not a pure additive no-risk set. Migrations 0041–0052 are not pure additive (0042 drops a column; 0052 replaces existing functions).

---

## Required migration reconciliation

Before choosing the migration scope:

1. Obtain fresh catalogue access (`pg_catalog`, `information_schema`) against production. Record current objects as of the query timestamp.
2. Compare each migration's intended effect against the live catalogue. Classify each as: already equivalent, absent, partial/drifted, or deferred.
3. For any migration previously applied outside Alembic (0049, 0050 were noted as separately applied): verify the live objects match the reviewed SQL exactly. Do not re-execute unless a drift is found and reviewed.
4. For migrations 0043–0048: record every function/trigger/policy state before deciding whether to run.
5. Write a new evidence document with the exact catalogue state. No migration may proceed without that document.

**Recommended minimum scope for a safe first app-only release (if catalogue confirms):**

A release of the main source with **0041–0050 confirmed equivalent** and **0051–0052 deliberately deferred** is feasible if:
- All 0041–0050 objects exist in production and are schema-equivalent to the reviewed SQL.
- Finance endpoints return a meaningful error rather than crashing (they currently would 500 — this must be confirmed and, if needed, a compatibility guard added before the first release).
- 0052's `get_available_slots` / `create_booking` are not yet replaced (old behavior continues until 0052 is approved).
- Old clients do not depend on the removed category/qr_token fields in a way that breaks the deployed API.

**This is a "confirm objects exist, verify equivalence, do not run migrations" path.** The release system checks `git diff --name-only baseline..candidate -- backend/migrations` and refuses if any migration file differs from the baseline commit. A source-labelled baseline commit is required (see B3).

---

## Staging validation

Before any production release:

1. Provision an isolated staging database (separate Supabase project or RDS instance with no shared pooler).
2. Restore the production backup to the isolated staging database.
3. Deploy the target main commit to a staging Cloud Run service with the isolated staging database URL.
4. Verify: CI passes on the staging deployment; all smoke endpoints return 200; finance endpoints return the correct error when 0051 is not applied; booking endpoints work within the 30-day window if 0052 is applied.
5. Run the full test suite with the staging database credentials.
6. Record the staging run ID and passing commit SHA.

---

## First supervised production release steps

This checklist is ordered. Do not skip a step or proceed past a blocker.

**Pre-release (all items required before any deployment):**

- [ ] **B1** Complete fresh catalogue inspection and write evidence document.
- [ ] **B2** Provision isolated staging database. Confirm staging/production are not sharing a project.
- [ ] **B3** Complete backup and restore test; record backup timestamp and restore SHA.
- [ ] **B4** Resolve old-client compatibility for 0042 and 0052, or define the exact migration scope that avoids the breaking changes.
- [ ] **B5** Verify all deployed + rollback images apply correct erasure for 0047/0048/0051 scope.
- [ ] **B6** Run the first supervised dispatch (workflow_dispatch via `cloud-run-candidate.yml`'s disabled path or a separately approved first-run procedure) to verify WIF/OIDC, environment variable readback and CI artifact exchange actually work before enabling automatic mode.
- [ ] Owner (Shifan) explicitly approves the migration scope, client rollout plan and release timing.

**Release execution:**

1. Confirm `AUTO_DEPLOY_ENABLED` is `false`. Do not change it yet.
2. Trigger `workflow_dispatch` on the approved supervised release procedure (this is the separately approved bootstrap path — not the automatic path). This is the first run that actually authenticates against GCP.
3. Monitor: `gate` job should read `enabled=false` from the production environment. The release should proceed only via the explicit supervised path with `APPROVE_DEPLOYMENT=true` and `DEPLOY_CONFIRMATION="DEPLOY api.salones.in"`.
4. Watch the candidate receipt (`candidate-result.json` artifact): confirm `status: PASS_CANDIDATE_VERIFIED`, matching commit SHA, smoke all passing, no migration differences, image digest matches the CI-tested image.
5. Verify both `api.salones.in` and `apiv1.mudassirmhd.in` return 200 on `/health/ready` and `/version` with the expected commit SHA.
6. Explicitly promote traffic only after review of the candidate receipt.
7. Record the exact deployed revision, previous revision, rollback command, and deployment timestamp.

---

## Rollback steps

If any health check fails after promotion:

1. The release system automatically rolls back traffic via `patch_traffic(current, copy.deepcopy(before["traffic"]))` if health fails during promotion.
2. If the automatic rollback runs but rollback health also fails (status `ROLLBACK_HEALTH_FAILED`): do not attempt further automated changes. Execute the exact `rollback_command` from the `candidate-result.json` receipt manually via `gcloud run services update-traffic`.
3. If `production_traffic_promoted` is `None` in the receipt: the rollback itself failed. Operator action is required; inspect traffic manually in the Cloud Run console.
4. Schema changes from 0051/0052 (if applied) are forward-only: traffic rollback to the previous code revision retains the additive tables. The old code must be compatible with the new schema. If not, a forward-fix migration is required rather than data restoration.
5. If a pre-migration snapshot was taken and data loss is acceptable: restore the snapshot to the isolated restore environment first, verify, then escalate to the owner before any production restore.

---

## Exact conditions for changing `AUTO_DEPLOY_ENABLED` from false to true

Change `AUTO_DEPLOY_ENABLED` to `true` (in GitHub Settings → Environments → production → Environment variables) **only after all of the following are true:**

1. The first supervised production release has completed successfully (B3 and B6 cleared).
2. A source-labelled production image is serving (bootstrap baseline established).
3. The migration scope for the current main commit is confirmed safe (B1 cleared) and either: all pending migrations are applied and verified, or the release system's migration guard confirms zero differences.
4. Old-client compatibility is certified or coordinated client rollout is complete (B4 cleared).
5. Erasure worker compatibility is verified (B5 cleared).
6. Isolated staging exists and at least one staging validation has passed (B2 cleared).
7. WIF/OIDC and environment readback have been verified in a real live run (B6 cleared).
8. Owner (Shifan) has given explicit written approval for automatic mode.

Until all eight conditions are met, `AUTO_DEPLOY_ENABLED` must remain `false`. The gate is the only control that prevents automatic deployment; it must not be changed until the supervised path has been successfully completed.

---

## What later PR merges will do after activation

Once `AUTO_DEPLOY_ENABLED` is `true` and all blockers are cleared:

1. A feature branch push or PR update triggers CI only (`backend.yml`). No production workflow runs.
2. A merged PR to `main` triggers `cloud-run-auto.yml`. The workflow acquires the `production-cloud-run` concurrency slot at the workflow level (not the release job level).
3. CI and the gate run. If `AUTO_DEPLOY_ENABLED` is `true` and all conditions pass, the release job is eligible.
4. `guard()` re-checks that the running commit is still the tip of `main`. If a newer commit arrived during CI, this run skips with `eligible=false` and the newer commit's workflow (which holds the pending slot) runs next.
5. The exact CI-tested image is loaded (not rebuilt), verified, pushed to Artifact Registry, deployed as a zero-traffic candidate revision, smoke-tested, and promoted to 100% traffic if all checks pass.
6. A health failure after promotion triggers automatic rollback to the previous revision. Both `api.salones.in` and `apiv1.mudassirmhd.in` are probed.
7. Each release produces a `candidate-result.json` artifact with full provenance, smoke results, commit identity, and the exact rollback command.
8. To pause releases: set `AUTO_DEPLOY_ENABLED` to `false`. Do not cancel an in-flight production mutation or rollback.
9. No migration runs automatically. If a merged PR includes new migration files, the release system compares the candidate's migration directory against the baseline commit and refuses the release if any difference is found. The migration must be applied separately, reviewed, and the baseline commit updated before the release can proceed.
