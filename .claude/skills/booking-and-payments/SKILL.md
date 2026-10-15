---
name: booking-and-payments
description: Use when working on availability, booking creation or transitions, walk-in flows, payment ledger, refunds, idempotency or webhooks. Encodes the Postgres-only paths and conflict, retry and dormancy rules.
---

# Booking and payments

Details: `backend/docs/BOOKING_FLOW.md`, `PAYMENTS.md`, `PAYMENT_DECISIONS.md`.

## Hard rules

- Availability only from Postgres `get_available_slots`. Booking only via `create_booking`. No Python slot math, no direct inserts into `bookings` or `booking_services`.
- Prices and deposits are computed in Postgres (`total_price`, `deposit_amount` from `PAYMENT_ADVANCE_PERCENT`). Do not recompute in Python.
- Three sources: `app` (customer), `manual_walkin` (owner/staff), `qr_walkin`. All go through the same DB function.

## Status flow

`pending -> confirmed -> completed`; `pending -> rejected`; `pending/confirmed -> cancelled`. The enum also has `checked_in` and `no_show` (`domain/entities/booking.py`); check `domain/services/booking_policy.py` before adding a transition. Customer cancellation is immediate before `CUSTOMER_CANCELLATION_CUTOFF_MINUTES`; after, it is a pending request the salon decides. Decisions run under row locks; stale or duplicate ones return 409.

## Conflicts

Slot taken between availability and create, `salon_not_accepting_bookings`, stale action requests, and `payment_overcollection` all map to 409 with a stable error code. The client refetches availability. Idempotent replay returns the original booking. Never leak the Postgres message.

## Payments

- Money exists only as ledger rows in `booking_payments`. A trigger recomputes `payment_status`, `paid_amount`, `refunded_amount`; the derived `payment_state` (e.g. `partially_paid`) is read-only.
- Manual receipts: owner/staff only (`BookingUseCases.record_payment`). A customer "I paid" is a pending request, never money received.
- Idempotency keys are DB-backed; reuse the existing mechanism for any new money-moving call. Commit before calling the provider so a crash can be reconciled.
- Webhooks: `POST /v1/webhooks/{provider}`; verify the signature over the raw body in constant time, gate replays, then enqueue. The `payment-webhook-worker` retries and reconciles; handlers must be idempotent.
- Refunds reverse the commission snapshot proportionally.

## Dormant

Online collection is DORMANT until `PAYMENT_PROVIDER` and credentials are configured (Cashfree adapter tested with mock transport only; not sandbox-tested or deployed). Do not describe it as live. Keep new code behind the provider-configured check.

## Tests

Use fake gateways and `tests/integration/test_payment_ledger_sql.py`, `test_checkout_safety_sql.py` patterns for SQL-level behavior. Include a concurrent double-booking test for any change near `create_booking` (see `pytest-testing`).
