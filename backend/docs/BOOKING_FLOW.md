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
