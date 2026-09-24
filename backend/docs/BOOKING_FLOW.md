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
