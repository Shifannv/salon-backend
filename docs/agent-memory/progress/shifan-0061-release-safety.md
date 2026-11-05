# Progress: shifan-0061-release-safety

## Goal
Make migration 0061 safe to apply and release the multi-professional visit API without breaking salon erasure or checkout contracts.

## Status
in progress

## Done
- Added bounded migration execution, fail-closed function patching, least-privilege grants, and complete category backfill checks.
- Preserved permanent salon erasure for the new category and booking-segment tables.
- Kept multi-professional checkout quotes and booking creation consistently limited to Pay at Salon.
- Passed 44 focused migration, erasure, and contract tests against disposable PostgreSQL 18.

## In progress
- Running the complete local CI preflight before commit and push.

## Next steps
1. Run `bash backend/scripts/check-ci.sh` and resolve every failure.
2. Commit and push the focused branch, then require green GitHub checks for the exact commit.
3. Merge through a pull request, apply reviewed migration 0061, deploy the exact tested image, and verify production health and schema.

## Decisions
- 2026-11-05: Reuse the encrypted November 2 recovery backup for this release, per the owner's explicit instruction.
- 2026-11-05: Keep production migrations as a separate reviewed operation instead of running Alembic at container startup.

## Files touched
- `backend/migrations/sql/0061_staff_service_visits.sql`
- `backend/app/application/use_cases/booking_use_cases.py`
- `backend/app/application/use_cases/checkout.py`
- `backend/app/infrastructure/db/repositories/platform/admin_salon_erasure.py`
- `backend/tests/integration/`
- `backend/tests/unit/test_staff_service_contract.py`
- `backend/docs/STAFF_SERVICE_VISITS.md`

## Blockers and open questions
- None currently; production remains unchanged until local and GitHub gates pass.

## Review findings
- [fixed] critical, `backend/migrations/sql/0061_staff_service_visits.sql`: new restrictive foreign keys originally broke permanent salon erasure.
- [fixed] high, `backend/app/application/use_cases/checkout.py`: segmented visits could be quoted for online payment although booking creation rejected them.
- [fixed] high, `backend/migrations/sql/0061_staff_service_visits.sql`: function rewrites needed exact-definition guards and a bounded statement timeout.

## Session log
- 2026-11-05: Hardened migration 0061 and its API contract; focused PostgreSQL 18 suite passes 44 tests.
