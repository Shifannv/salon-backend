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
profile, media, caches and tokens. Past bookings are retained anonymized; an owner's salon is
removed from customer-facing screens and scrubbed. Deletion is blocked while open bookings
or pending requests exist. The public web deletion page required by Google Play lives in the
separate website repository and is **not built yet**. See `backend/docs/ACCOUNT_DELETION.md`.
