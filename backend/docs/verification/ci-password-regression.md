# CI password regression ? 2026-10-14

The failed main run for merge b0c1be8 stopped in pytest, before image build or deployment. The supplied log reports 925 passed, 14 skipped and one failure in `test_shared_pool_keeps_business_transactions_and_probe_autocommit`.

## Cause and fix

`str(safety.engine.url)` masks the password as `***`. Passing that display string into a new SQLAlchemy engine causes password authentication failure against the CI PostgreSQL service. This is a test connection configuration error, not evidence of incorrect production secrets or a broken application pool.

The regression now renders its connection URL with `hide_password=False` only when constructing its private test settings. No URL is printed or committed. Shared-pool, actor-context, rollback and transaction-isolation assertions remain intact. No workflow gate is bypassed and no production configuration is changed.

## Repository and Docker cleanup

Remove the 112 previously tracked paths under `backend/.pytest_tmp/` in a follow-up commit; do not amend or force-push the merged history. Ignore that directory in Git. Exclude `.pytest_tmp/` and `.artifacts/` from the backend Docker build context. Application code and migrations are unchanged.

## Verification

- Fresh disposable PostgreSQL 18 container on loopback port 55440, password authentication enabled with the same synthetic credential as CI.
- Original test reproduced `InvalidPasswordError`; the original source copy and log remain in ignored local artifacts.
- Corrected full suite: **926 passed, 14 skipped**, one upstream Starlette/AnyIO warning, 67.62 seconds. Full log remains in ignored `.artifacts/ci-after.log`.
- Ruff and pip dependency validation passed.
- Backend-only Docker build passed.
- Existing container smoke script passed: non-root runtime, custom port 8080, health, worker imports and migration files.
- All deployment shell syntax checks and template-only Docker Compose validation passed.

The current workflow deploys only main after its test and image jobs pass. A fix branch/PR verifies the patch without deploying production. Merging to main also invokes the workflow's existing explicit migration step; review pending migrations before approving that merge. This verification itself applies migrations only inside disposable local test databases and performs no production deployment.
