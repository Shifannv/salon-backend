# Owner finance: Phase 0 discovery and approval request

Date: 2026-10-28. Status: **design only, awaiting approval.** No migration, table, route, SMS or
provider call exists or was run for this document. Nothing here is applied to Mumbai, staging or
production.

Scope (from the owner's brief): a Daily Ledger (salon cashbook), Expenses, Staff Earnings from
per-service attribution, a Finance area in the owner app, and a Premium SMS fallback. The backend is
the financial authority; the app only displays what the backend sends.

Reviewers: this document answers what exists, what is missing, what we propose to reuse, and which
decisions are still yours. Section 9 is the list of questions that need an answer before Phase 1.

---

## 1. Summary

1. Receipts and refunds already have an immutable home: `booking_payments` (manual rows are
   `channel='manual'`, `status='captured'`, `collection_method` `CASH` or `UPI_DIRECT`) and
   `payment_refunds`. The Daily Ledger should **read these**, not copy them into a second table.
2. Completed sales come from `bookings` (`status='completed'`, `completed_at`, `total_price`).
   `completed_at` is set by a database trigger, so it is the right clock for "sales on a local day".
3. Genuinely new: expenses, audited cash adjustments, day-close records, per-service staff
   attribution, and the `FIXED_PER_SERVICE` commission type.
4. Staff earnings should **extend the existing G06 design** (rule versions, snapshots, append-only
   entries) instead of inventing a second one. G06 is design-only and still waits on approval Q10.
5. Premium SMS is already specified (MARKETPLACE_CONTRACT section 7). No provider, sender, consent
   wording or persistent usage store exists, so it stays switched off.
6. Two conflicts need a decision: the money unit (rupees in the database, paise in the brief) and
   the old ledger response shape, which exposes internal split fields (section 6).

## 2. What exists today (verified in code)

| Area | Fact | Where |
| --- | --- | --- |
| Receipts | One row per collection: `amount numeric(10,2)` rupees, `currency` text default `INR`, `method` cash/online, `collection_method` CASH/UPI_DIRECT, `recorded_by`, `captured_at`, `status` | `booking_payments` (0026, 0035) |
| Manual collection | `POST /v1/bookings/{id}/payment` body `cash` or `upi_direct`; owner and staff only; idempotent via `Idempotency-Key`; inserts a manual captured row for the outstanding balance | `routes/bookings.py`, `platform/booking_payments.py` |
| Refunds | `payment_refunds` with `kind` (owner, customer_cancellation, salon_cancellation, closure) and `deduction_amount` | 0026, 0033 |
| Completion rule | A pay-at-salon booking cannot complete until a manual payment is recorded (409 `payment_collection_required`) | `platform_repository.py` |
| Completion time | `bookings.completed_at timestamptz`, set by trigger when status becomes completed | `001_supabase_schema.sql` |
| Salon-local date | `bookings.booking_calendar_date` (IST) | 0035 |
| Booking lines | `booking_services(booking_id, service_id)` with price and duration snapshots. **No per-line staff**; one `staff_id` on the booking | `001_supabase_schema.sql` |
| Staff | `staff` has no commission fields | `001_supabase_schema.sql` |
| Owner earnings | `GET /v1/salons/me/earnings` totals the payment ledger (online, platform fees, manual) | `payments.py` |
| Analytics | No owner analytics route; the owner app derives Reports from `GET /bookings` | owner app `useAnalyticsBookings` |
| Admin analytics | Counts each status separately; sales are `completed` only, by IST date | `admin_insights_repository.py` |
| Entitlements | `subscription_plans.features` jsonb; Growth has `split_bill`, `daily_ledger`; Premium adds `sms_alerts` and `monthly_alert_cap` 300 | `0031_seed_subscription_plans.py` |
| Erasure | Bookings are anonymised; payment amounts and provider references are kept; every text column must be classified in `COLUMN_TREATMENT` | `ACCOUNT_DELETION.md` |
| Expenses / cashbook | Nothing exists | (none) |
| Messaging | No WhatsApp or SMS sender. Phase B added a provider-neutral port, templates, quota maths and a fake gateway, all switched off | `app/application/ports/messaging_gateway.py` |

Prepared but **not applied** (held): `booking_financial_outcomes` and `booking_finance_commands`
(0046 SQL), staff commission design G06, audit foundation G01. Mumbai has no Alembic history
rows, and revisions 0038 to 0050 are unapplied. Executable migrations need separate approval.

## 3. Reuse, do not duplicate

| Need | Reuse | New |
| --- | --- | --- |
| Cash and direct UPI received | `booking_payments` manual captured rows | none |
| Refunds | `payment_refunds` | none |
| Gross completed sales | `bookings` completed in the salon-local day | none |
| Outstanding due | completed or served bookings where `payment_status='unpaid'` | none |
| Expenses | none | `salon_expenses` (append-only) |
| Cash corrections | none | `salon_cash_adjustments` (append-only) |
| Day close | none | `salon_day_closes` (append-only revisions) |
| Commission rules, snapshots, earnings | G06 design | per-line staff attribution; `FIXED_PER_SERVICE` check |
| SMS quota and intents | MARKETPLACE_CONTRACT section 7 | persistent usage and intent tables (Phase 4) |

Reading existing tables for receipts means Finance and Analytics cannot disagree: both sum the same
rows.

## 4. Proposed data model (proposal only; no revision ID assigned)

Money unit: see decision Q1. Proposed: new tables store `amount_paise bigint check (> 0)`. Existing
`numeric(10,2)` rupee columns convert exactly (two decimals), so the API can speak paise everywhere.
Currency stays `INR`.

### 4.1 `salon_expenses` (append-only)

`id uuid pk`, `salon_id` fk salons, `entry_type` (`expense` | `reversal`), `reverses_id uuid null`
fk self, `category` check (`supplies`, `rent`, `utilities`, `salary_advance`, `maintenance`, `other`),
`amount_paise bigint > 0`, `payment_method` (`cash` | `non_cash`), `occurred_at timestamptz`,
`note text null` (max 500, classified for erasure), `created_by uuid null` fk profiles, `created_at`,
`idempotency_key text`.
Constraints: unique `(salon_id, idempotency_key)`; a reversal must have `reverses_id`, the same
salon, category, amount and method, and at most one reversal per expense; no UPDATE or DELETE
(trigger refuses). Index `(salon_id, occurred_at)`.

### 4.2 `salon_cash_adjustments` (append-only)

Same shape as expenses with `direction` (`in` | `out`), `reason text not null`, and a mandatory
`created_by`. Used for corrections after a day is closed, never for editing history.

### 4.3 `salon_day_closes` (append-only revisions)

`id`, `salon_id`, `local_date date`, `revision integer`, `opening_cash_paise`, `expected_cash_paise`
(as computed when closed), `actual_cash_paise`, `difference_paise` (generated),
`difference_reason text` (required when difference is not zero), `closed_by`, `closed_at`.
Unique `(salon_id, local_date, revision)`. A day is "closed" when it has a revision. Closing never
locks later corrections: those are adjustments, and a re-close creates the next revision.

### 4.4 Per-service staff attribution

Do **not** alter `booking_services`. G06 already keys earnings by `(booking_id, service_id)` and
holds staff in its allocation rows. Proposal: one allocation per line with weight 10,000 basis
points, staff chosen by an owner action before completion, defaulting to the booking's staff. The
snapshot is written when the booking completes, so later rule changes never rewrite history.

### 4.5 Commission policy

Types `NONE`, `FIXED_PER_SERVICE`, `PERCENT_OF_SERVICE_VALUE`. G06 already supports exactly one of
percentage or fixed amount per rule and forbids an implicit default rate; no rule means no
commission. Precedence between staff, service and salon default scopes is still Q10.

## 5. Daily Ledger arithmetic (per salon-local day)

All figures are derived at read time from immutable rows:

- Gross completed sales = sum of `total_price` of bookings completed that local day.
- Cash collected = manual captured rows with `CASH` that day, minus nothing else.
- Non-cash received = manual captured rows with `UPI_DIRECT` (and card or manual non-cash, if added).
- Outstanding due = completed bookings still unpaid.
- Refunds = `payment_refunds` processed that day, split cash and non-cash.
- Expenses = expense rows minus their reversals, split cash and non-cash.
- Expected closing cash = opening cash + cash collected - cash refunds - cash expenses
  +/- cash adjustments.
- Actual closing cash and difference come only from a close record.

Rules kept from the brief: expenses never reduce sales; there is no "Profit" figure; "Net operating
cash" is used only where the formula above is exact; a completed unpaid service raises sales and
due but not cash. Opening cash for a day is Q3.

## 6. Proposed API (owner and admin only; staff get 403; cross-salon ids return 404)

Keeps the paths the owner app already calls where they exist.

| Method and path | Purpose |
| --- | --- |
| `GET /v1/salons/me/ledger/daily?date=` | One day: totals above, entries, close state. **Response shape changes**, see below |
| `GET /v1/salons/me/ledger/range?from=&to=` | Per-day totals for the history and date filter |
| `POST /v1/salons/me/ledger/days/{date}/close` | Record actual cash; reason required when different |
| `POST /v1/salons/me/ledger/adjustments` | Audited cash in or out, with reason |
| `POST /v1/salons/me/expenses`, `GET`, `POST /{id}/reverse` | Append an expense, list, reverse |
| `GET /v1/salons/me/staff-earnings?from=&to=` | Per staff: services, attributable value, earned commission, reversals |
| `PUT /v1/bookings/{id}/services/{service_id}/staff` | Attribute one line to one staff member before completion |
| `GET/POST /v1/salons/me/commission-rules` | Existing contract, extended with `FIXED_PER_SERVICE` |

Error codes (all inside the existing `{"error": {"code", "message"}}` envelope):
`entitlement_required`, `forbidden`, `not_found`, `validation_error`, `idempotency_key_required`,
`idempotency_key_reuse`, `day_in_future`, `difference_reason_required`, `expense_already_reversed`,
`attribution_after_completion`, `staff_not_in_salon`.

**Conflict to resolve (Q2).** The agreed section 5 response exposes `owner_net`, `salon_share`,
`gateway_fees` and `staff_percent`. Your rule says internal platform and salon allocation
percentages are never shown to owners or staff. The owner-facing Finance response will therefore
omit those fields. The owner app's existing `ledger.repository.ts` schema is rewritten in Phase 3.

Analytics and Finance read the same sources: a shared status definition for completed, cancelled,
rejected and no-show, and completed sales from `bookings`. The owner app source has been changed (built, not yet released) to show
**Gross completed sales** (completed bookings only) and to keep Cancelled and Rejected separate. The
Reports screen still reads `GET /bookings`; it moves to a backend analytics route that shares Finance's
query in Phase 2.

## 7. Safety, privacy and erasure

- Tenant isolation inside each query (`salon_id` from the actor's salon); cross-salon id gives 404.
- Idempotency keys on every write; unique constraints make a repeat harmless.
- Lock order for writes that touch several rows: salon, then booking, then rows being appended.
- RLS: new tables carry the same service-role-only posture as `booking_payments`; the app never
  talks to the database.
- Audit: every write records actor and time; reversals and adjustments name a reason.
- Erasure: money rows are kept for the retention period (`FINANCIAL_RECORD_RETENTION_YEARS` has
  **no default**, Q6). Free-text `note` and `reason` are cleared on erasure; amounts, categories
  and dates stay. Every new text column must be added to `COLUMN_TREATMENT`, or the existing guard
  test fails. Known gap: the guard misses newer tables (Mumbai reconciliation open item).
- No bank numbers, QR tokens, provider keys, customer phone numbers in messages, or internal split
  fields appear in any response or log.

## 8. Premium SMS (design status)

Specified in section 7 of the marketplace contract: trigger after 5 minutes without a push
acknowledgement, 300 provider-accepted sends per salon per local month (SMS and WhatsApp combined),
no carry-over, owner sees used, remaining and reset date, push continues when exhausted.
Built so far (Phase B, switched off): provider-neutral port, approved templates with a guard that
rejects phone numbers, links, amounts and references, monthly quota arithmetic, a gateway that
sends nothing, a fake gateway for tests, and a completion-message service with ordered guards and
one-attempt-per-booking idempotency. **Not built:** a real provider, sender identity, DLT or
WhatsApp template approval, inbound webhook and signature checks, persistent usage and intent
tables. Feature key: the seeded plans use `sms_alerts`, the brief says `premium_sms_alerts` (Q8).

## 9. Decisions

### Already recorded (no action)
Platform commission has no default; staff commission has no implicit rate (G06); no earned
commission for a cancelled service; corrections are append-only; the app never computes pricing,
refunds or access; Cashfree and all provider money stay off; online payment UI is not built; SMS is
Premium, server-side, 300 per month, combined with WhatsApp.

### Needs your answer
| # | Question | Recommendation |
| --- | --- | --- |
| Q1 | Money unit for new tables and the API: paise integers, or keep rupee decimals? | Paise integers; convert existing rupee columns exactly |
| Q2 | Drop `owner_net`, `salon_share`, `gateway_fees`, `staff_percent` from owner-facing responses? | Yes |
| Q3 | Opening cash for a day: previous day's actual close, else expected? First-ever day entered by the owner? | Previous actual, else expected; owner enters the first |
| Q4 | Who may close a day and add expenses: owner only, or owner plus approved admin? | Owner and admin; never staff |
| Q5 | Plan gating: Growth and Trial (as seeded for `daily_ledger`) or Premium only? | Growth and Trial |
| Q6 | Financial retention years (no default exists) | Needs your policy; blocks purge design |
| Q7 | Commission scope precedence and basis (G06 Q10) | Staff+service, then staff, then service, then salon default |
| Q8 | SMS feature key: keep `sms_alerts` or rename to `premium_sms_alerts`? | Keep `sms_alerts` |
| Q9 | Customer "service complete" WhatsApp: allowed at all, consent wording, and does it count toward the 300? | Not before consent wording; if allowed, count it |
| Q10 | Can an owner re-attribute a completed line, or only before completion? | Only before; after that, an audited adjustment |

### Needed before any code
Approval of the tables in section 4, a reviewed Alembic revision (next free number after 0050), a
plan for the Mumbai history gap (never `alembic upgrade` or `stamp` there), and a named SMS provider
with cost, sender and compliance approval (Phase 4 only).

## 10. Migration compatibility risks

1. Mumbai `alembic_version` is empty; 0038 to 0050 are unapplied. Staging and production share one
   database, so any SQL applies to both at once.
2. G06 filenames are locators, not execution order; no revision IDs or parents are assigned.
3. Guard tests refuse unclassified text columns and newer tables; new tables must be classified first.
4. Per-line staff attribution needs a backfill rule for old bookings: none implied. Existing
   completed bookings would show attribution by the booking's staff, labelled as such.
5. `completed_at` is a trigger default (`coalesce(..., now())`); a repair or import that sets it
   changes historical day totals. Reads must use it as-is and never rewrite it.

## 11. Proposed phases (unchanged from the brief)

Phase 1: detailed schema, lock order, grants, API contracts and fixtures, review only.
Phase 2: local backend with disposable PostgreSQL tests. Phase 3: owner-app Finance UI against the
approved contract. Phase 4: SMS provider work after provider approval. Each phase stops for review.
