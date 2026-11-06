# Booking management Option A

Prepared migration: 0062_booking_management, after 0061_staff_service_visits. Apply through reviewed Alembic release procedures; no application startup schema mutation.

Pay at Salon self-bookings use a singleton database policy: 3 reservations per appointment date, 5 active upcoming appointments, 8 creations per rolling seven days, across salons. Customer cancellation releases active/date capacity but retains weekly creation consumption. Trusted salon cancellation/rejection releases weekly consumption. Per-customer advisory locking protects concurrent quota checks and overlapping self-bookings. A multi-staff visit counts once.

Customers may cancel pending/confirmed appointments before their start without an owner action request. The repository locks the booking and checks the database wall clock. Owner cancellation notifications are informational. Refund bands and durable refund processing remain the existing U08 policy; cancellation is not provider refund completion. GET cancellation-quote previews verified gateway amounts, excludes excess collection, accounts for processed refunds and requires review for unsupported/manual payment histories.

Complete-visit edits use the existing change endpoints with optional segments plus POST change-availability. Legacy single-staff quote/commit requests normalize into that same itinerary path. Availability and replacement plans remain PostgreSQL functions. Commit locks the salon, booking and catalog, re-quotes, validates version/fingerprint and permission, replaces all segments atomically, preserves service snapshots/history, and publishes owner/customer notifications once. Idempotency replay returns the committed booking. Moving secondary start times also consumes a reschedule. Immediate handovers only.

For fully prepaid online bookings, the proposed service total must equal the booked fulfilment total (or authoritative original service-line total for legacy nullable fulfilment). Retained prepaid obligations remain preserved. Lower/higher service totals are rejected at commit. Pay at Salon may reprice. Existing change cutoff and two-reschedule limit remain.

New helper/commit functions are not executable by browser-facing roles. Backend use cases retain ownership checks. No online provider activation is included. Friend/attendee bookings are deferred.

Clients require quote can_commit before enabling edits. Deploy backend plus migration before advertising the new edit policy. Customer cancellation supports a missing preview endpoint using existing server booking permission, without fabricating a refund estimate.

Validation: migration/security source reviews completed; final preflight result is recorded in the customer integration handoff and local CI log. No production data or provider payment operation was performed.
