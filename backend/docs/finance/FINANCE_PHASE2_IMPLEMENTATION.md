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
  identity and cost approval (Phase 4). WhatsApp is out of scope (F09): the dormant "service
  completed" WhatsApp message code was removed.
- **Admin access.** Owner only, as decided (F04). A super-admin may audit where authorized but
  never writes through the owner workflow.

## Deviations from the Phase 1 design (each deliberate)

1. **Owner only**, not admin (above).
2. **Trial counts as Growth, and an ended plan is read-only (F05, F11).** A salon on its free
   trial has no subscription row, so its plan features are empty; enforcing `daily_ledger`
   literally would lock out every trial owner. Writes need the paid plan to include
   `daily_ledger`, or the trial to be active (started, not expired, not at its booking limit);
   otherwise they are refused with `entitlement_required`. **Reads are always allowed to the
   owner**, so past records stay visible, and the daily ledger reports `can_write` for the app.
   **This is the first server-side enforcement of a plan feature in the backend.**
3. **Cash adjustments gained `reverses_id`** (mirror rule: opposite direction, same amount).
4. **Opening cash (F03).** If the day before was closed, its counted cash is the opening and a
   client cannot restate it. Otherwise (first ever close, or an unclosed day in between) the
   opening is **never assumed or carried silently**: the ledger reports `needs_confirmation` with
   the last count plus the cash that moved since as a *suggestion*, and closing the day requires
   the owner to state `opening_cash_paise` (`opening_cash_required` if missing). A re-count of the
   same day keeps the opening the owner already confirmed.
5. **Day-close idempotency** replays the stored close; a different body is `idempotency_key_reuse`.

## Gaps found while testing (read these)

- **Manual cash and UPI receipts cannot be refunded in the platform today.** The database requires a
  manual receipt to stay `captured` (`ck_booking_payments_manual_is_settled`) and its own refund
  trigger would move it out of that state. The ledger's refund figures therefore read zero for
  manual receipts. **A proper `Cash Refund` financial event is required before any public refund
  workflow launches (F12)**: linked to the original booking/receipt, with amount, actor,
  timestamp, reason and audit history. Until it exists, the generic cash adjustment is for audited
  *internal corrections only* and must not be presented as a customer refund. The refund query is in
  place and tested with seeded data.
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

## API additions since the Phase 1 contract (2026-10-29)

| Change | Why |
| --- | --- |
| `GET /salons/me/ledger/daily` adds `expenses_total_paise` | The server sums cash and non-cash expenses, so no client adds money figures together. |
| `GET /salons/me/ledger/daily` adds `can_write` | `false` once the trial or plan has ended (F05, F11): reads stay open, every write returns 403 `entitlement_required`. |
| `opening_cash_source` gains `needs_confirmation` | The day before was not closed; `opening_cash_paise` is only a suggestion (F03). |
| New error `opening_cash_required` (422) | Closing a day whose opening is `not_set` or `needs_confirmation` needs `opening_cash_paise`; it is never assumed. |
| `entitlement_required` now means "writes locked", not "no access" | Reads are always allowed to the owner. |

Owner-app record: [FINANCE_PHASE3_OWNER_APP.md](FINANCE_PHASE3_OWNER_APP.md).

## Expense v2: custom name, batch push, change feed, month summary (2026-10-29)

Built for the owner app's local-first Expenses tab: the phone keeps expenses on the device and syncs
in batches, so it does not call the API on every view or tap. The backend stays the authority and
every expense still reaches the Daily Ledger.

| Endpoint (owner only, `/v1`) | Purpose |
| --- | --- |
| `POST /salons/me/expenses/batch` | Up to 50 items, each `{client_id, title, category, amount_paise, payment_method, occurred_at, note?}`. `client_id` is the item's idempotency key. Each item stands alone: results are `created`, `replayed` or `rejected` (with a `code`); a refused item never blocks the rest. Whole call is 403 `entitlement_required` once the plan has ended. |
| `GET /salons/me/expenses/changes?after=N&limit=` | Entries (expenses and cancelling entries) recorded after cursor N, oldest first, with `next_cursor` and `has_more`. An empty answer keeps the cursor. Readable after the plan ends. |
| `GET /salons/me/expenses/summary?month=YYYY-MM` | Server-computed per-day and month totals (cash, non-cash, total, count) in the salon's time zone, net of cancellations. The app adds nothing up. |

Schema changes to **0051 (edited in place)**: `title` (the owner's own name for the expense, 1-80
characters, free text redacted on erasure), `seq` (identity change cursor, `UNIQUE (salon_id, seq)`),
the append-only trigger and the reversal mirror trigger extended, partial `created_by` indexes, no
TRUNCATE for `service_role`, no public access to the sequence.

**Editing 0051 in place is safe only while it has never been applied anywhere**, including local
Supabase, CI snapshots and the Mumbai environment, and is not recorded in a migration-history table.
That was true when this was written (every test ran on throwaway databases). If it has been applied
anywhere, add a 0052 instead (ADD COLUMN needs a backfill because `title` is NOT NULL).

### A bug in Phase 2, found while designing this, and fixed
A cancelling entry was dated "now". Cancelling yesterday's mistaken 500-rupee expense today made
today's expenses -500 and inflated today's expected cash for money that never moved. A cancelling
entry now carries the **original's date, title, amount and method** (the mirror trigger enforces all
of it), so a cancellation nets out on its own day and never disturbs another. Because a day can now
change after it was closed, the daily ledger reports `close.changed_since_close`; the stored count is
never rewritten.

### Review (database-reviewer, 2026-10-29) and what was done
- Cursor: `seq` order equals commit order only because every writer takes the salon lock first. The
  lock is now `FOR NO KEY UPDATE`: `FOR UPDATE` would have blocked every booking and payment insert
  (they take `KEY SHARE` on the salon row). A test proves a booking-style `KEY SHARE` is not blocked
  while another finance writer is.
- Redaction can now only blank a column or set `Removed`; it can never write new text, and the
  permission is switched off again when the scrub ends.
- A lock timeout, deadlock or dropped connection is no longer reported as a refused expense (the
  phone would have discarded a valid one); only constraint and guard failures are verdicts.
- A cancellation reads the original only after taking the lock; a retry written in another time zone
  is the same request; the cursor has an upper bound (422, not 500); erasure skips an older copy of
  the table that has no `title` column.
- Not changed: the erasure race the reviewer raised is already covered, because `erase_database`
  locks the owner's salons `FOR UPDATE` before scrubbing, which conflicts with finance writes.
- Unverified: which database role the production backend connects as (RLS is on with no policy, so
  it must be the owner or a BYPASSRLS role such as `postgres`/`service_role`). The new tables use the
  same grants as `booking_payments`.

## Repeating expenses (E4, 2026-10-29)

"Rent on the 1st", "tea every day". Added to **0051** (still never applied anywhere; same in-place
condition as the expense v2 addendum above).

| Endpoint (owner only, `/v1`) | Purpose |
| --- | --- |
| `GET /salons/me/expense-rules` | The salon's rules (running first, at most 100). Readable after the plan ends; carries `can_write`. |
| `POST /salons/me/expense-rules` | Create a rule. `Idempotency-Key` required; a retry replays. Needs an active plan. |
| `POST /salons/me/expense-rules/{id}/stop` | Stop a rule once. Needs an active plan; other salons' rules are 404. |

- **A rule records nothing by itself.** The owner's phone turns each due day into an ordinary expense
  through the existing batch endpoint, with client id `rule:<rule id>:<YYYY-MM-DD>` and `occurred_at`
  at midnight salon time. The same day therefore replays instead of doubling, on any phone, and a
  cancelled occurrence is never brought back (the replay returns the stored, cancelled record).
- **Rules are never edited** (`guard_expense_rule` allows only a one-way stop, plus `created_by` ->
  NULL when a profile is deleted). To change one: stop it and make another.
- **The server checks every `rule:` id** (`_check_rule_occurrence`): the rule must exist in that salon,
  the day must fall on the rule (`rule_applies_on`: daily; weekly on the start weekday; monthly on the
  start day, a short month using its last day), must not be after the stop day, must not be before the
  start, and the title, amount, category, method, note and salon-local date must equal the rule's. A
  stale phone therefore cannot add days after a stop, and two phones cannot record one logical day
  under two ids. Refused with `rule_occurrence_invalid` per item.
- Limits: 30 running rules per salon; start no more than 31 days back and 366 days ahead (checked
  only for a new rule, so a retry of an old create still replays). The app fills missed days for at
  most 31 days back.
- Erasure deletes the owner's rules (configuration that can name people); occurrence expenses are
  redacted like any other expense.
- Reviewed by `database-reviewer`: two MEDIUM findings fixed (the `created_by` exemption in the guard,
  server-side `rule:` validation) plus replay-before-window, `search_path`/function privileges, the
  stale "every table is append-only" header and a bound on the list.
