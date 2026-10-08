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

Jira is the source of truth for planned work and acceptance criteria. This document is
only a high-level capability summary.
