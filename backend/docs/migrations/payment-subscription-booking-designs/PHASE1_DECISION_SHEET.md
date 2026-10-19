# Phase 1 decision sheet

Prepared 2026-10-19 and updated after the owner's answers. The
[approval register](APPROVAL_REGISTER.md) (records U06 and U07) is the source of truth;
this sheet is a working summary of it. Statuses: **Approved** (recorded in the register),
**Rejected**, or **Approval required** (not yet decided). No code, SQL, database or
provider access is part of this sheet.

"Gate": **schema** = blocks the migration for that group; **code** = blocks service logic;
**inert** = can ship disabled behind a flag.

## A. Handoff rules

| # | Rule | Status | Gate |
| --- | --- | --- | --- |
| A1 | Owner cancels without advance admin approval; reason required; customer notified; admin reviews afterwards. TA02's extra admin gate is dropped. | **Approved** (U06) | schema |
| A2 | Customer may reschedule the same booking at most two times. The count never resets. Only committed reschedules count; a failed reschedule does not. | **Approved** (U06) | schema |
| A3 | New slot is secured before the old slot is released. A failed reschedule leaves the original booking unchanged. Every change is audited. | **Approved** (U06) | schema |
| A2b | After a reschedule, cancellation eligibility uses the new appointment start time. | **Approved** (U06) | schema |
| A4 | Owner/admin cancellation before check-in gives a full refund, started asynchronously. The platform bears non-recoverable provider fees. | **Approved** (U06) | code |

## B. Money rules

| ID | Question | Status | Gate |
| --- | --- | --- | --- |
| Q25 | Flat fee at 48 hours or more | **Approval required.** Exact INR amount not given; the value stays configurable with no default. | schema |
| Q25 | Base for the 5% and 35% penalties | **Approved** (U06): captured amount before provider fees. Caps and partial or unpaid captures remain open. | schema |
| Q26 | Recipients of each penalty | **Approved** (U06): 70% salon / 30% platform of the retained pool, all bands. | schema |
| Q17 | Provider fees per band | **Approved** (U06): `retained_pool = penalty - nonrefundable_provider_costs`. Costs never reduce the customer refund. If costs exceed the pool, the salon gets zero and the platform absorbs the shortfall. Platform share rounded half-up in integer paise; residual paise go to the salon. Tax components and reserve/true-up for unknown fees remain open. | schema |
| Q19 | Payout hold for cancellations | **Approved** (U07): customer cancellation `hold_until = max(cancellation_time + 48 hours, appointment_start)`; confirmed no-show `hold_until = max(no_show_confirmation_time, appointment_start + 10 minutes) + 48 hours`. Payout stays blocked during a dispute or provider-fee uncertainty. Dispute scope and release remain open. | schema |
| Q29 | Owner/admin cancels before check-in | **Approved** (U06/U07): full async refund; platform bears non-recoverable fees; no salon payout unless separately approved. | code |
| Q29 | Owner/admin cancels after check-in | Restricted and audited. **Monetary remedy: Approval required** (pending review). | inert |
| Q02 | Money for a confirmed no-show | **Approved** (U06): under-4-hour treatment (refund zero, costs deducted, 70/30 split). | code |
| Q18 | Exactly four hours | **Approved** (U03): 35% band. | none |

## C. Technical defaults TA01 to TA10

| ID | Status | Gate |
| --- | --- | --- |
| TA01 | Checked-in remedy: restricted and audited; amount **Approval required** | inert |
| TA02 | **Rejected** (U06) | schema |
| TA03 | **Approved** (U06): five retries after the first dispatch; 1m, 5m, 30m, 2h, 12h | code |
| TA04 | **Approved** (U06): five-minute fenced lease | code |
| TA05 | **Approved** (U06): dead-letter after permanent error or exhausted retries | code |
| TA06 | **Approval required**: needs the admin email address and Sentry project | inert |
| TA07 | **Changed and approved** (U06): single super-admin with `aal2`; reason, approval record and full audit trail; no two-person approval | inert |
| TA08 | **Approved** (U06): 90-day retention for resolved outbox rows | code |
| TA09 | **Approval required**: financial audit retention period awaits accountant or legal | schema |
| TA10 | **Design approved only** (U06): Google Cloud KMS and Secret Manager. Creating any resource needs a separate approval. | schema |

## D. Still needing a decision

Q25 flat fee amount, TA06 alert targets, TA09 retention period, the Q29 checked-in
monetary remedy, dispute scope and release (Q19), tax components and reserve/true-up for
unknown fees, and all Cashfree evidence (P01 to P06), which remains unverified.

## E. Items that can stay unresolved (ship inert, disabled by flag)

P01 to P06 (need a Cashfree account), L01 to L05, Q23 zero-refund wording, Q22 offer
binding, Q21 owner-visible allowlist (minimal U02 set), Q10 staff commission formulas, Q11
availability numbers, Q12 healthy hold limits, Q08 deposits, Q06 and Q07 calendar details.
Defaults I would propose for Phase 5, to confirm later: trial ends two calendar months
after admin approval (Asia/Kolkata, end exclusive, no restart); renewal grace seven calendar
days; staff commission as a percentage of the booking's snapshot price, earned on
completion, none on cancelled bookings.

## F. What happens next

Writing Alembic revisions (A01) needs its own approval and is not implied by this sheet or
by U06/U07.
