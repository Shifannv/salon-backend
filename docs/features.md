# Features

The backend currently supports:

- Supabase JWT verification, refresh, current-profile lookup, and owner access
- Customer profiles, avatars, salon discovery, nearby search, and reports
- Owner salon profiles, settings, images, QR codes, holidays, services, and staff
- Super admin salon review, rejection/resubmission, and approval gates for daily business
- Database-backed availability and booking creation
- Booking approval, rejection, completion, cutoff-based cancellation, and payment state
- Customer payment-confirmation/cancellation requests with owner decisions and audit history
- Booking delay estimates, role-scoped filtering, and optional pagination
- Walk-in QR resolution, phone verification, and walk-in booking
- Soft-deletable holidays plus previewed, confirmed, customer-notified closures
- Notifications, bulk read, device tokens, and optional Firebase/Expo push delivery
- Health checks, Alembic migrations, Docker deployment, tests, and linting

This document summarizes implemented capabilities. Deployment status must be verified
against the running release; source changes alone do not mean a feature is live.

Current website integration additions include full super-admin onboarding review,
discovery visibility and home placement controls, optional enforced admin MFA, and
QR-scoped booking retries. See the website implementation prompt for exact contracts.
Paid subscription checkout/webhooks remain unimplemented; existing activation is manual/test.

## Account deletion (implemented, not yet production-verified)

Customers and owners can permanently delete their account from either app through one
backend workflow: verification code to their own verified email/phone, explicit `DELETE`
confirmation, immediate lockout, then durable background erasure of the Auth identity,
profile, media, caches and tokens. Past bookings are retained anonymized. An owner's salon
becomes an inert "Closed salon" shell (no name, city, address, hours, payout details, holidays
or provider references) so other customers keep their own history; staff logins that exist only
for that salon are deleted. There is no grace period. **An owner's upcoming bookings do not
block deletion: they are cancelled (`salon_closed`), each customer is notified (fixed copy,
names no one) and online payments are refunded through the payment gateway before anything is
erased; cash receipts are not refunded by the platform and the notice says so.** A failed
refund is recorded for the operator and does not block erasure after a retry cap. Customers
are still blocked by their own upcoming bookings/pending requests, and owners by an active
paid subscription when a subscription provider is configured. The worker has a heartbeat
healthcheck and refuses to start with incomplete storage/Supabase settings. The public web
deletion page required by Google Play lives in the separate website repository and is **not
built yet**. Status: BUILT and SQL-verified on a throwaway PostgreSQL; refund path DORMANT
until a payment provider exists (verified with a fake gateway only); NOT staging-tested. See
`backend/docs/ACCOUNT_DELETION.md`.

## Payment collection (backend)

- BUILT: payment ledger (`booking_payments`), refunds, webhook intake with replay gate,
  DB-backed idempotency, retry/reconcile worker, derived `payment_state`, advance/full
  payment preferences, owner earnings, payout-account audit history.
- DORMANT: online payment end to end until `PAYMENT_PROVIDER` and credentials are set
  (reference adapter for one provider is included, tested against a mock transport only).
- NOT BUILT: per-salon provider credentials (customer pays salon directly), platform-held
  disbursement (licensed activity), commission policy, encryption at rest of the account
  number, subscription payments. Details: `backend/docs/PAYMENTS.md`.
