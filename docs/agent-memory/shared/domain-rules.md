# Domain rules

Source: `backend/docs/BOOKING_FLOW.md`, `AUTHORIZATION.md`, `ACCOUNT_DELETION.md`, `domain/entities/`.

## Roles
`customer`, `owner`, `staff`, `super_admin`. Role is read from `profiles`, never from JWT claims. `super_admin` needs `aal2` when `ADMIN_REQUIRE_MFA=true` (403 `mfa_required`). Ownership checks are in use cases; RLS is defense in depth.

## Booking
- Create only via Postgres `create_booking`; availability only via `get_available_slots`.
- Sources: `app`, `manual_walkin`, `qr_walkin`.
- Statuses in code: pending, confirmed, checked_in, no_show, rejected, completed, cancelled. Core flow: pending -> confirmed -> completed; pending -> rejected; pending/confirmed -> cancelled.
- Slot taken between availability and create -> 409. Client refetches availability.
- `salons.accepting_bookings=false` blocks all sources (409 `salon_not_accepting_bookings`).
- Customer cancellation is immediate before `CUSTOMER_CANCELLATION_CUTOFF_MINUTES`; after it, it is a request the salon decides.

## Payments
Ledger rows in `booking_payments`; a trigger recomputes `payment_status`, `paid_amount`, `refunded_amount`. Preferences: pay_at_salon, pay_advance, pay_full. Cash plus online beyond the total is refused (`payment_overcollection`). Online collection is DORMANT until `PAYMENT_PROVIDER` is set. Webhooks: `POST /v1/webhooks/{provider}`; the signature over the raw body is the only credential.

## Public salon visibility
`approval_status='approved'` AND `is_active` AND `profile_completed` for all public reads (list, search, nearby, details, services, staff, QR).

## Account deletion
Only customer and owner. Target is the JWT `sub`. Verification code, `DELETE` confirmation, immediate lockout, then durable background erasure by the account-deletion worker. Bookings are kept anonymized; an owner's salon becomes an inert "Closed salon" shell. Hard delete is allowed only here.
