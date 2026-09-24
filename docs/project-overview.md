# Project overview

The Salon Platform API is the shared backend for customer, owner/barber, admin, and
walk-in clients. It verifies Supabase identities, applies business authorization,
coordinates booking workflows, stores platform data in Supabase Postgres, uploads media
to Cloudflare R2, and sends push notifications through Firebase.

This repository is backend-only. Client applications consume the versioned HTTP API
through environment-configured base URLs.

The application follows these dependency directions:

```text
api -> application -> domain
infrastructure -> application/domain ports
```

The database owns concurrency-sensitive booking rules. Availability comes from
`get_available_slots`, and bookings are created through `create_booking`.

Current scope includes authentication, customer profiles, salon discovery, owner salon
management, catalog and staff management, availability, bookings, walk-in QR flows,
notifications, devices, reports, health checks, and deployment support.
