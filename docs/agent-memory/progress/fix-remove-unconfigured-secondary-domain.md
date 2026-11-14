# Progress: fix/remove-unconfigured-secondary-domain

## Goal
Remove the unmapped `apiv1.mudassirmhd.in` host from `PUBLIC_CHECKS` in `cloud_run_auto.py` so Cloud Run automatic deploys pass the baseline health gate.

## Status
**DONE — committed and pushed (2c5a7ac). Ruff clean. 2505 unit tests pass.**
PR `fix/remove-unconfigured-secondary-domain` → `main` must be opened and merged.

## What was done
- Root cause: `PUBLIC_CHECKS` in `backend/scripts/cloud_run_auto.py` probed two hosts — `api.salones.in` AND `apiv1.mudassirmhd.in`. The second domain is not mapped in Cloud Run, so the baseline health check always returned an error, surfacing as "Previous revision health/identity is not established" in every automatic deploy.
- Fix: removed the second host so `PUBLIC_CHECKS` probes only `https://api.salones.in` on five paths (`/health/ready`, `/version`, `/health`, `/health/db`, `/health/redis`).
- Committed as `2c5a7ac fix: remove unconfigured secondary domain from production health checks` on branch `fix/remove-unconfigured-secondary-domain`.
- Pushed to `origin/fix/remove-unconfigured-secondary-domain`.

## Context from this session
- All Alembic migrations 0053–0070 are now applied to production. `alembic_version = 0070_booking_no_show_warnings`.
- The production API at `https://api.salones.in` is live and healthy (commit `52197d5`). That is not the latest `main` commit (`cf67229`).
- After this PR merges to `main`, the `cloud-run-auto.yml` workflow will run and should deploy `cf67229` automatically.

## Files touched
- `backend/scripts/cloud_run_auto.py` — PUBLIC_CHECKS narrowed to `api.salones.in` only (line 25)

## Next steps
1. Open PR `fix/remove-unconfigured-secondary-domain` → `main` on GitHub.
2. Merge it; watch the `cloud-run-auto.yml` Actions run complete.
3. Verify `https://api.salones.in/version` returns `cf67229` after deploy.
4. Private the GitHub repo (user deferred until after deploy).

## Blockers
None — code change is committed and pushed.

## Session log
- 2026-11-13: session started (context-compacted continuation), wrap completed
- 2026-11-13: session started (/start, no task given)
