# Progress: shifan-booking-api-followups

## Goal
Deliver the backend part of the owner/customer app requests: cancellation reason dedupe, multi-status booking filter, and owner archive of terminal bookings.

## Status
in progress

## Done
- Cancellation reason: `compose_cancellation_reason` in `booking_use_cases.py` drops free text that repeats the reason code or label (case, `_`, `-` ignored); label dicts are now module constants. Used by `cancel` and `barber_cancel`.
- `GET /v1/bookings?status=` accepts comma-separated or repeated values (`parse_booking_statuses` in `routes/bookings.py`, 422 on unknown); use case and repository take `booking_statuses`, SQL uses `= any(cast(... as booking_status[]))`.
- Tests: `tests/unit/test_booking_use_cases.py`, `test_booking_status_filter.py` (new), `test_list_bookings_scoping.py`. Unit suite 2261 passed; Ruff clean. Not run: integration suites, `scripts/check-ci.sh`.
- `docs/BACKEND_API_REFERENCE.md` bookings `status` row updated.

## In progress
- Nothing running.

## Next steps
1. Answer open questions below, then build owner archive (migration 0063 `bookings.owner_archived_at`, `POST /v1/bookings/{id}/archive` and `/unarchive`, `is_archived` in `BookingResponse`, default exclusion in `list_bookings`/`get_booking`). Use `alembic-migration` skill and `migration-reviewer`.
2. Update the other client docs (Salon-Owner and Customer API documents, CLIENT_DEVELOPER_HANDOFF) for the status filter.
3. Run `python-reviewer` and `code-reviewer`, then `bash scripts/check-ci.sh` before any commit.
4. Hand off to frontends: customer app sends `reason_text: null` for chip-only cancel; owner app uses existing `POST /v1/notifications/read-all`; owner scoping already exists in `GET /v1/bookings`.

## Decisions
- 2026-11-07: no `DELETE /v1/test/bookings` purge endpoint, because project rules 2 and 5 forbid direct booking writes and hard delete outside erasure; use disposable-DB cleanup instead.
- 2026-11-07: no new salon-scoped bookings or bulk-read route, because `GET /v1/bookings` already scopes owners to their salons and `POST /v1/notifications/read-all` exists.

## Files touched
- `backend/app/api/v1/routes/bookings.py`, `backend/app/application/use_cases/booking_use_cases.py`, `backend/app/infrastructure/db/repositories/platform/booking_queries.py`
- `backend/tests/unit/test_booking_use_cases.py`, `test_booking_status_filter.py`, `test_list_bookings_scoping.py`
- `docs/BACKEND_API_REFERENCE.md`

## Blockers and open questions
- Archive scope: owners only (assumed) or customers too?
- Is migration 0062 applied in production? 0063 must follow it.
- An owner with several salons sees all of them in `GET /v1/bookings`; add an optional `salon_id` filter only if the frontend confirms they need it.

## Review findings
- None yet; reviewers not run.

## Session log
- 2026-11-07: session started
- 2026-11-07: shipped items 1 and 3 test-first; archive design pending answers.
