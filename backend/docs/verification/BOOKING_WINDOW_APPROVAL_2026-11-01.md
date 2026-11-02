# Customer booking window approval — 1 November 2026

The owner explicitly confirmed: customers may book up to 60 days ahead.
This supersedes the prior 30-day assumption in the reconciliation check.

The existing SQL sidecar is historically named
`0052_booking_window_30_days.sql`, but its current bodies enforce the upper
boundary `v_today + 60`, based on salon-local dates. Availability hides dates
outside the window; customer booking creation repeats the upper-bound check.
The existing walk-in source behavior is unchanged.

The verification helper now checks the exact signatures and body hashes of
both `get_available_slots` and `create_booking` against that sidecar. Missing
functions, a 30-day body, or any other body difference fail. The result reports
hashes rather than printing restored function definitions. This is source
verification; boundary behavior requires the disposable PostgreSQL tests too.

No migration SQL, production function, data, traffic or deployment flag is
changed by this approval. The failed prior Gate A remains failed; a fresh
backup/isolated rehearsal is required before production migration approval.
