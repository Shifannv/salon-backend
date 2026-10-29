# Owner finance: Phase 2 (local backend) implementation record

Date: 2026-10-29. Status: **built and tested on a disposable local PostgreSQL only.** Nothing was
applied to Mumbai, staging or production; no deployment, provider call, SMS or Cashfree action took
place. Migration 0051 is prepared, not released.

## What was built (the cash book)

| Area | Where |
| --- | --- |
| Migration (additive, append-only, RLS) | `migrations/sql/0051_owner_finance_cashbook.sql`, `migrations/versions/0051_owner_finance_cashbook.py` |
| Rules (pure) | `app/domain/services/finance_ledger.py` |
| Queries and writes | `app/infrastructure/db/repositories/finance_repository.py` |
| Use cases | `app/application/use_cases/finance.py` |
| Routes and schemas | `app/api/v1/routes/finance.py`, `app/api/v1/schemas/finance.py` |
| Erasure of free text | `app/infrastructure/db/repositories/account_deletion/erasure.py` (`_scrub_owner_finance`) |
| New error codes | `entitlement_required`, `day_in_future`, `difference_reason_required`, `expense_already_reversed` |

Endpoints (owner only, `/v1`, integer paise, writes need `Idempotency-Key`):
`GET /salons/me/ledger/daily`, `GET /salons/me/ledger/range`, `POST /salons/me/ledger/days/{date}/close`,
`POST /salons/me/ledger/adjustments`, `POST|GET /salons/me/expenses`, `POST /salons/me/expenses/{id}/reverse`.

## Not built yet (and why)

- **Staff earnings** (per-service attribution, commission rule versions, earning and reversal
  events). It changes booking completion, so it needs its own review and tests. The commission
  scope question (Phase 0 Q7) is still unanswered.
- **Premium SMS persistence** (usage, intents, inbound actions). Waits for a provider, sender
  identity, consent wording and cost approval (Phase 4).
- **Admin access.** The routes are `/salons/me/...`, which has no meaning for an admin with no
  salon. Phase 1 assumed "owner and approved admin"; this build is owner only.

## Deviations from the Phase 1 design (each deliberate)

1. **Owner only**, not admin (above).
2. **Trial counts as Growth.** A salon on its free trial has no subscription row, so its plan
   features are empty. Enforcing `daily_ledger` literally would lock out every trial owner, so the
   gate is: the paid plan includes `daily_ledger`, or the trial is active (started, not expired,
   not at its booking limit). Expired or exhausted trials are refused with `entitlement_required`.
   **This is the first server-side enforcement of a plan feature in the backend.**
3. **Cash adjustments gained `reverses_id`** (mirror rule: opposite direction, same amount).
4. **Opening cash** is the previous close's counted cash plus the net cash of any unclosed days
   since. Only the very first close accepts an owner-entered opening amount; later closes reject it.
5. **Day-close idempotency** replays the stored close; a different body is `idempotency_key_reuse`.

## Gaps found while testing (read these)

- **Manual cash and UPI receipts cannot be refunded in the platform today.** The database requires a
  manual receipt to stay `captured` (`ck_booking_payments_manual_is_settled`) and its own refund
  trigger would move it out of that state. The ledger's refund figures therefore read zero for
  manual receipts. Until a manual-refund feature exists, cash returned to a customer is recorded as
  a cash adjustment (out) with a reason. The refund query is in place and tested with seeded data.
- **Gateway (online) payments are not in the cash book.** Receipts are manual rows only (cash and
  direct UPI). That matches "no Cashfree, no online payment" and must be revisited if that changes.
- **`needs_review`** is true when a completed booking is marked paid but has no receipt row, or a
  refund is pending. The app must not present those totals as final.
- **The range endpoint runs one query per day** (at most 93). Fine for now; fold into one grouped
  query if it is ever slow.
- **The salon lock serialises writes per salon.** Intended (it prevents a double close and a racing
  idempotent write); expense and adjustment writes are low volume.

## Bug found by the tests and fixed in the migration

The append-only trigger compared every column except the free text, but `salon_day_closes` has a
stored generated column (`difference_paise`) that PostgreSQL computes after BEFORE triggers run, so
even a legitimate erasure redaction was refused. The column is excluded from the comparison; it
derives from `actual_cash_paise` and `expected_cash_paise`, which stay frozen. The migration is not
applied anywhere outside disposable databases, so it was corrected in place.

## Erasure

Owner erasure clears `salon_expenses.note` and replaces `salon_cash_adjustments.reason` and
`salon_day_closes.difference_reason` with "Removed". Amounts, categories, dates and the computed
difference are retained like every other financial record. `created_by` becomes NULL through the
foreign key when the profile is deleted (the trigger permits exactly that). The step is skipped
when the tables do not exist, so erasure still works before the migration is applied. Retention
years remain undecided (Phase 0 Q6), so no purge exists.

## Verification (disposable PostgreSQL 18, loopback, throwaway container)

- `tests/integration/test_owner_finance_sql.py`: constraints, append-only, reversals, privileges, indexes.
- `tests/integration/test_owner_finance_api.py`: real bookings, cash and UPI collection and completion
  flowing into the ledger; close and re-close; idempotency; validation; role, plan and tenant isolation.
- `tests/integration/test_owner_finance_erasure.py`: the real erasure on the prepared schema 0038..0051.
- `tests/unit/test_finance_design_fixtures.py`: the 700-rupee example, now also pinned to the production rules.
- `tests/unit/test_migration_policy.py` and `test_payment_flows.py`: head pins updated to 0051 (no guard weakened).
