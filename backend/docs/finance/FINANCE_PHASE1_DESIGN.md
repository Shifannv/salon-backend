# Owner finance: Phase 1 schema and API design (review only)

Date: 2026-10-29. Status: **design for review. Nothing here is executable.** No Alembic revision,
SQL file, route or provider call has been created. Nothing is applied to Mumbai, staging or
production, and no migration number is reserved. The SQL below is a proposal written as text.

Builds on [FINANCE_PHASE0_DISCOVERY.md](FINANCE_PHASE0_DISCOVERY.md). The money rules are pinned
by executable design tests: `tests/unit/test_finance_design_fixtures.py` with
`tests/fixtures/finance/example_day.json` (the brief's 700-rupee example) and the reference
arithmetic in `tests/support_finance_reference.py`. Those use no database and no app code.

## 0. Assumptions used (the Phase 0 questions are not answered yet)

Each is my recommendation. If you answer differently, only the marked section changes.

| Q | Assumption | Changes if different |
| --- | --- | --- |
| Q1 | Integer **paise** (`bigint`) in all new tables and every API field | sections 2 and 6 |
| Q2 | Owner-facing responses omit `owner_net`, `salon_share`, `gateway_fees`, `staff_percent`, platform fees | section 6 |
| Q3 | Opening cash = previous local day's actual close, else its expected cash; the first day is entered by the owner | section 2.3 |
| Q4 | Owner and approved admin may write; staff get 403 | section 7 |
| Q5 | Entitlement `daily_ledger` (Trial and Growth, as seeded) | section 6 |
| Q7 | Commission scope precedence: staff+service, staff, service, salon default | section 2.5 |
| Q10 | An owner may re-attribute a service line only **before** completion | section 2.4 |

Q6 (retention years) has **no default** and stays open: erasure keeps money rows but the purge
schedule cannot be designed until you set it (section 8).

## 1. Principles

1. The ledger is **derived**. Daily totals are computed from immutable rows at read time; there is
   no editable daily-total row to drift.
2. Every new table is **append-only**: no UPDATE, no DELETE. A correction is a new row that
   references the old one.
3. Cash and UPI are **salon-level receipts**. Staff earnings come from service lines and a frozen
   policy, never from how a customer paid.
4. Only `bookings`, `booking_services`, `booking_payments` and `payment_refunds` are read for
   receipts, sales and refunds. Nothing is copied, so Finance and Analytics cannot disagree.
5. All day and month boundaries use `salons.timezone` as a half-open interval `[start, end)`.
6. Existing tables are **not altered**. Every change is additive, so rollback is dropping the new
   tables (section 9).

## 2. Proposed tables (text proposal, public schema, `salon_id uuid not null` everywhere)

Common to every table: `id uuid pk default gen_random_uuid()`, `created_at timestamptz not null
default now()`, `created_by uuid null references profiles(id) on delete set null` (null only after
erasure), `idempotency_key text not null`, `unique (salon_id, idempotency_key)`, and RLS enabled
with no policy (section 7).

### 2.1 `salon_expenses`
```
entry_type      text   not null check (entry_type in ('expense','reversal'))
reverses_id     uuid   null references salon_expenses(id)
category        text   not null check (category in ('supplies','rent','utilities','salary_advance','maintenance','other'))
amount_paise    bigint not null check (amount_paise > 0)
payment_method  text   not null check (payment_method in ('cash','non_cash'))
occurred_at     timestamptz not null
note            text   null check (char_length(note) <= 500)
check ((entry_type = 'reversal') = (reverses_id is not null))
unique (reverses_id)                                  -- an expense is reversed at most once
```
A reversal must copy the original's salon, category, amount and method; enforced by a constraint
trigger (the reference test `net_expense_total` states the rule). Index `(salon_id, occurred_at)`.

### 2.2 `salon_cash_adjustments`
```
direction       text   not null check (direction in ('in','out'))
amount_paise    bigint not null check (amount_paise > 0)
reason          text   not null check (char_length(btrim(reason)) between 3 and 500)
occurred_at     timestamptz not null
reverses_id     uuid   null references salon_cash_adjustments(id), unique (reverses_id)
```
Used for corrections after a day is closed. Never edits an earlier row.

### 2.3 `salon_day_closes` (one row per revision)
```
local_date            date   not null
revision              integer not null check (revision >= 1)
opening_cash_paise    bigint not null check (opening_cash_paise >= 0)
expected_cash_paise   bigint not null          -- computed by the server when closing
actual_cash_paise     bigint not null check (actual_cash_paise >= 0)
difference_paise      bigint generated always as (actual_cash_paise - expected_cash_paise) stored
difference_reason     text   null
check (difference_paise = 0 or char_length(btrim(coalesce(difference_reason,''))) >= 3)
unique (salon_id, local_date, revision)
```
A day is closed when it has a revision. Closing never locks history: later corrections are cash
adjustments, and a re-close inserts revision + 1. The server, not the app, computes
`expected_cash_paise`; a request that supplies one is rejected. `local_date` must not be in the
future (`day_in_future`).

### 2.4 `booking_service_staff` (per-service attribution)
```
booking_id   uuid not null
service_id   uuid not null
staff_id     uuid not null
revision     integer not null check (revision >= 1)
foreign key (booking_id, service_id) references booking_services(booking_id, service_id)
unique (booking_id, service_id, revision)
```
Current attribution is the highest revision. A new revision is allowed only while the booking is
`pending`, `confirmed` or `checked_in` (error `attribution_after_completion`); a trigger checks
it under the booking lock. If a line has no row, the booking's own `staff_id` applies and the API
labels it "booking staff". **Same-salon rule:** `staff` has no `(id, salon_id)` key today, so the
proposal adds `unique (id, salon_id)` to `staff` (additive) and keys the FK on both columns.

### 2.5 `staff_commission_rule_versions` (extends the approved G06 design)
```
staff_id             uuid null references staff   -- null = salon default
service_id           uuid null references services
version              integer not null check (version >= 1)
commission_type      text   not null check (commission_type in ('NONE','FIXED_PER_SERVICE','PERCENT_OF_SERVICE_VALUE'))
rate_basis_points    integer null check (rate_basis_points between 0 and 10000)
fixed_amount_paise   bigint  null check (fixed_amount_paise >= 0)
effective_from       timestamptz not null
check ( (commission_type='NONE'                     and rate_basis_points is null and fixed_amount_paise is null)
     or (commission_type='FIXED_PER_SERVICE'        and rate_basis_points is null and fixed_amount_paise is not null)
     or (commission_type='PERCENT_OF_SERVICE_VALUE' and fixed_amount_paise is null and rate_basis_points is not null))
```
Rules are never edited; a change is a new version. G06's temporal exclusion on overlapping active
rules stays. With no matching rule the result is `NONE`: there is no implicit default rate.

### 2.6 `staff_earning_events` (append-only)
```
booking_id, service_id, staff_id                    -- same salon as the booking
event_type           text   not null check (event_type in ('earned','reversal','adjustment'))
amount_paise         bigint not null check (amount_paise > 0)
direction            text   not null check (direction in ('credit','debit'))  -- earned credit, reversal debit
service_value_paise  bigint not null                -- snapshot of the line price at completion
rule_version_id      uuid   null references staff_commission_rule_versions(id)
commission_type      text   not null                -- frozen copy of the policy at completion
rate_basis_points    integer null
fixed_amount_paise   bigint null
refund_id            uuid   null references payment_refunds(id)
reverses_id          uuid   null references staff_earning_events(id)
reason               text   null
unique (booking_id, service_id) where event_type = 'earned'   -- one earning per line, ever
unique (refund_id, reverses_id) where event_type = 'reversal'
```
The earning is written in the same transaction that sets the booking `completed`. Cancelled,
rejected and no-show bookings never reach it. A refund after completion writes a reversal of
`earned x cumulative_refunded / service_value` minus reversals already written (half-up), so the
sum never drifts or exceeds the earning (tests: `test_reversals_never_drift_or_exceed_the_earning`).

### 2.7 Premium messaging (built only at Phase 4; shown so the schema is reviewed once)
```
salon_messaging_usage       (salon_id, window_start, key unique, provider_message_id, accepted_at)
messaging_outbound_intents  (id, salon_id, booking_id null, template, channel, status
                             in ('queued','sent','rejected','expired'), idempotency_key unique,
                             attempts smallint check (attempts <= 1), created_at)
messaging_action_codes      (code unique, salon_id, booking_id, profile_id, action in ('A','D','C'),
                             expires_at, consumed_at null)
messaging_inbound_actions   (provider_message_id unique, sender_phone_hash, code, action, result, received_at)
```
Only a **hash** of the sender number is stored. A usage row exists only for a send the provider
accepted, so a refusal never costs quota. `attempts <= 1` is the "no retry loop" guarantee.
Nothing here is created until a provider, sender identity, consent wording and cost are approved.

## 3. Reads that build the Daily Ledger (no new table)

For `[start, end)` from the salon's timezone, all in paise (existing rupee columns x 100, exact):

| Figure | Source |
| --- | --- |
| Gross completed sales | `bookings` where `status='completed'` and `completed_at` in range |
| Cash collected | `booking_payments` manual captured, `collection_method='CASH'`, `captured_at` in range |
| Non-cash received | same, `collection_method='UPI_DIRECT'` |
| Outstanding due | completed bookings with `payment_status='unpaid'` (all dates, shown separately) |
| Refunds, split cash and non-cash | `payment_refunds` processed in range |
| Expenses | `salon_expenses` expense rows minus reversals, by `occurred_at` |
| Expected closing cash | opening + cash collected - cash refunds - cash expenses +/- adjustments |

Index needs (verified against the current schema, which has `booking_payments(salon_id, created_at)`
but not `captured_at`): add `booking_payments(salon_id, captured_at)` and
`bookings(salon_id, completed_at) where status='completed'`.

## 4. Lock order (every write follows it, to avoid deadlock)

1. `salons` row (`for update`) - only for day close and adjustments.
2. `bookings` row - completion, attribution, refund reversal.
3. `booking_services` line, then `staff_commission_rule_versions` (read).
4. Append the new rows. Idempotency is checked first by the unique `(salon_id, idempotency_key)`.

A day close takes the salon lock, recomputes expected cash inside the transaction and inserts the
next revision, so two owners closing at once get distinct revisions, never a lost update.

## 5. Audit events

`expense.created`, `expense.reversed`, `cash_adjustment.created`, `day.closed`, `day.reclosed`,
`attribution.changed`, `commission_rule.created`, `earning.recorded`, `earning.reversed`. Each
records actor, salon, entity id, time and (for adjustments and differences) the reason. They go
to the existing audit foundation (G01 / 0047) once approved; until then each table's own actor and
timestamp columns are the record, and append-only triggers stop alteration.

## 6. API contracts (all under `/v1`, JSON, paise, `Idempotency-Key` required on every write)

Common: owner or approved admin only; staff get 403; a record from another salon returns 404;
plan without `daily_ledger` gets 403 `entitlement_required`; errors use
`{"error": {"code": "...", "message": "..."}}`. Owner-facing responses never include platform
fees, `owner_net`, `salon_share`, `staff_percent`, bank details or tokens.

### `GET /salons/me/ledger/daily?date=YYYY-MM-DD`
```json
{ "date": "2026-10-29", "timezone": "Asia/Kolkata", "status": "open",
  "gross_completed_sales_paise": 70000,
  "cash_collected_paise": 40000, "non_cash_received_paise": 30000,
  "outstanding_due_paise": 0,
  "refunds": {"cash_paise": 10000, "non_cash_paise": 0},
  "expenses": {"cash_paise": 5000, "non_cash_paise": 20000},
  "cash_adjustments": {"in_paise": 0, "out_paise": 0},
  "opening_cash_paise": 100000, "expected_closing_cash_paise": 125000,
  "close": null, "needs_review": false }
```
`needs_review` is true when a completed booking has no recorded payment or a refund is pending;
the app must not show those totals as final. After a close: `"status": "closed"` and
`"close": {"revision": 1, "actual_cash_paise": 124500, "difference_paise": -500, "difference_reason": "...", "closed_at": "..."}`.
An empty day returns zeros, never 404. Labels: there is no "profit" field.

### `GET /salons/me/ledger/range?from=&to=` (max 93 days)
`{"days": [{"date": "...", "gross_completed_sales_paise": 0, "cash_collected_paise": 0, "non_cash_received_paise": 0, "expenses_paise": 0, "status": "open|closed"}], "totals": {...}}`

### `POST /salons/me/ledger/days/{date}/close`
Body `{"actual_cash_paise": 124500, "difference_reason": "Tip jar emptied"}`. Returns the same
shape as the daily ledger. Errors: `day_in_future`, `difference_reason_required`, `validation_error`.

### `POST /salons/me/ledger/adjustments`
Body `{"direction": "in|out", "amount_paise": 2500, "reason": "...", "occurred_at": "..."}` -> 201.

### `POST /salons/me/expenses`, `GET /salons/me/expenses?from=&to=&limit=&offset=`, `POST /salons/me/expenses/{id}/reverse`
Body `{"category": "supplies", "amount_paise": 5000, "payment_method": "cash", "occurred_at": "...", "note": "..."}`.
Reverse takes no amount: it mirrors the original. Errors: `expense_already_reversed`, `not_found`.
Copy shown to owners: "Expense record. Not a tax invoice or official accounting ledger."

### `GET /salons/me/staff-earnings?from=&to=`
```json
{ "staff": [{"staff_id": "...", "name": "Hafis", "services_completed": 2,
             "attributable_value_paise": 50000, "earned_paise": 20000,
             "reversed_paise": 4000, "net_paise": 16000, "attribution": "explicit"}] }
```
Owner and admin only. A staff login gets 403 (self-view stays off until approved). The response
has no cash or UPI split per staff.

### `PUT /bookings/{id}/services/{service_id}/staff`
Body `{"staff_id": "..."}`. Errors: `attribution_after_completion`, `staff_not_in_salon`, `not_found`.

### `GET|POST /salons/me/commission-rules`
Existing contract, extended with `commission_type` and `rate_basis_points` or `fixed_amount_paise`.

Error codes added: `day_in_future`, `difference_reason_required`, `expense_already_reversed`,
`attribution_after_completion`, `staff_not_in_salon`, `idempotency_key_required`,
`idempotency_key_reuse` (the last two exist already).

## 7. Privileges and row-level security

Same posture as `booking_payments`: `alter table ... enable row level security`, no policy for
`anon` or `authenticated`, `revoke all ... from anon, authenticated`, access only through the
backend's service role. Append-only is enforced by a `before update or delete` trigger that raises,
with one exception: a `security definer` erasure function owned by a dedicated role may clear the
free-text columns (section 8). The owner app never reads these tables directly.

## 8. Account erasure and retention

| Column | Treatment |
| --- | --- |
| `amount_paise`, `category`, `payment_method`, dates, `entry_type`, `direction`, snapshots | keep (money record) |
| `note`, `reason`, `difference_reason` | **clear** to null on erasure (free text may name people) |
| `created_by`, `staff_id` links | set null / replaced by "Former staff" |
| `sender_phone_hash` | delete with the messaging rows (Phase 4) |

Every new text column must be added to `COLUMN_TREATMENT` or the existing guard test fails. Known
gap from the Mumbai reconciliation: that guard misses newer tables, so it is extended in the same
change. Purge after the retention period depends on **Q6**, which has no default and blocks it.

## 9. Corrections and rollback

- **Mistake in a record:** append a reversal or adjustment. No row is ever edited or deleted.
- **Mistake in a day close:** insert the next revision, or add a cash adjustment.
- **Wrong attribution after completion:** an audited earning adjustment, not a rewritten snapshot.
- **Rolling back the release:** everything is additive, so removing the feature is dropping the
  new tables and the two new indexes; no existing column or row changes. Money already recorded
  would be exported first. Roll-forward is preferred.
- **Migration safety:** no `alembic upgrade` or `stamp` against Mumbai. When approved, the SQL is
  applied as one reviewed file in one transaction, like 0049.

## 10. What still needs your decision before Phase 2

Answers to Q1 to Q10 in Phase 0 (this design used the recommendations in section 0), a retention
period (Q6), approval of the tables above, and a plan for the Mumbai history gap. Phase 2 also
needs explicit approval to create executable migrations.
