# Booking flow

1. The client requests availability with the staff member, date, and selected services.
2. The API totals the selected service duration and calls Postgres
   `get_available_slots`.
3. The client submits the chosen start time and services.
4. The API authorizes the actor and calls Postgres `create_booking`.
5. Postgres validates the slot under concurrency and returns the booking ID.

If another booking takes the slot between steps 2 and 4, the API returns a conflict.
The client must fetch availability again.

Booking sources are customer app, manual walk-in, and QR walk-in. Manual and QR flows
use the same database function so overlap protection remains consistent.

Typical status transitions are:

```text
pending -> confirmed -> completed
pending -> rejected
pending/confirmed -> cancelled
```

Never compute slots or insert booking rows directly in Python.

Owners and assigned staff can record an `estimated_end_datetime` for an active delayed
booking. This does not change the reserved `end_datetime` or rewrite availability.
When requested, later customers whose start time falls within the delay window receive
a notification.

## Action requests

`payment_preference=pay_at_salon` leaves the booking unpaid. After the visit begins, the
customer may create one pending payment-confirmation request. `received` records cash
payment once; `not_received` leaves the booking unpaid and allows a later claim.

Before `CUSTOMER_CANCELLATION_CUTOFF_MINUTES`, customer cancellation is immediate.
Inside the cutoff window, cancellation remains pending until the salon approves it.
Requests and booking changes are resolved under row locks; stale or duplicate decisions
return a conflict.

Owners preview holiday/leave impact through `/v1/salons/me/closures/preview`, then apply
the exact set through `/v1/salons/me/closures`. Applying creates the closure, cancels only
the overlapping active bookings, and persists a notification for each customer in one
transaction.

## Pausing new bookings

`salons.accepting_bookings` (default `true`) lets an approved salon's owner pause new
bookings with `PATCH /v1/salons/me/settings {"accepting_bookings": false}`. Staff,
customers, admins and unapproved salons get 403.

- Enforced in Postgres (migration `0022`): `get_available_slots` returns no rows and
  `create_booking` raises `salon_not_accepting_bookings` for every source, including
  owner/staff `manual_walkin`. The API maps it to `409` with error code
  `salon_not_accepting_bookings`.
- Existing bookings are untouched: no cancellation, no notifications.
- `accepting_bookings` is exposed on `OwnerSalonResponse`, salon list/detail and the
  walk-in QR payload so apps can show "Not accepting bookings right now". Toggling
  clears the `salon:{id}:*` and `walkin:qr:{token}` cache keys.
- Idempotent replays of a booking created before the pause still return that booking.

## Payment

Payment sits beside, not inside, the booking state machine. `create_booking` computes
`total_price` in Postgres; when the customer picks `pay_advance`/`pay_full`, the booking's
`deposit_amount` is derived in SQL from it (`PAYMENT_ADVANCE_PERCENT`). `payment_preference`
accepts `pay_at_salon|pay_advance|pay_full`.

Money is recorded only as ledger rows (`booking_payments`): a manual receipt
(`POST /bookings/{id}/payment`, or the owner confirming a customer's "I paid" request, which
now records the method the salon states instead of always `cash`) or a gateway intent. A
trigger recomputes `payment_status`/`paid_amount`/`refunded_amount`. A deposit leaves the
booking `unpaid` with `payment_state: partially_paid`. Cash plus an online capture that
would exceed the total is refused (`payment_overcollection`). `can_record_payment` is now
enforced in `BookingUseCases.record_payment` (owner/staff only; super admins no longer pass).

BUILT: ledger, manual receipt, derived columns. DORMANT: online intents, confirm, refund,
webhooks (no provider configured). NOT BUILT: auto-cancelling an unpaid-deposit booking.
