# Architecture

The FastAPI service is the shared API layer between the client apps and Supabase.

---

## Layer Diagram

```
┌───────────────────────────────────────────────────────────────┐
│  Clients (customer app, owner app, walk-in QR, admin panel)   │
└──────────────────────────┬────────────────────────────────────┘
                           │  HTTP (JWT bearer token)
                           ▼
┌───────────────────────────────────────────────────────────────┐
│  api/  — FastAPI routers, request/response Pydantic schemas,   │
│          auth extraction via Depends, dependency wiring        │
│          NO business logic. NO SQL.                           │
└──────────────────────────┬────────────────────────────────────┘
                           │  calls use cases
                           ▼
┌───────────────────────────────────────────────────────────────┐
│  application/  — use cases, DTOs, gateway ports (Protocols)   │
│          Owns authorization and business flow.                 │
│          Uses domain entities and repository/gateway ports.   │
│          NO FastAPI. NO SQLAlchemy. NO HTTP Pydantic schemas. │
└──────────────────────────┬────────────────────────────────────┘
                           │  calls domain / infrastructure
                      ┌────┴────┐
                      ▼         ▼
   ┌─────────────────────┐  ┌─────────────────────────────────┐
   │  domain/            │  │  infrastructure/                │
   │  Pure Python.       │  │  Implements ports:              │
   │  Entities, value    │  │  - PlatformRepository (raw SQL) │
   │  objects, domain    │  │  - SupabaseAuthGateway          │
   │  services.          │  │  - SupabaseAuthAdminGateway     │
   │  No external deps.  │  │  - FCMGateway (push)            │
   └─────────────────────┘  └─────────────────────────────────┘
```

---

## Dependency Rules (enforced by convention, enforced in CI by import analysis)

| Layer | May import from | Must NOT import from |
|---|---|---|
| `domain/` | stdlib only | `api/`, `application/`, `infrastructure/`, FastAPI, SQLAlchemy, Pydantic HTTP schemas |
| `application/` | `domain/`, stdlib | `api/`, FastAPI, SQLAlchemy, Supabase SDK, Firebase SDK |
| `infrastructure/` | `domain/`, `application/ports`, SQLAlchemy, Supabase SDK, Firebase SDK | `api/` |
| `api/` | `application/`, `domain/entities`, FastAPI | Direct DB/SDK access; must go through use cases |

---

## Booking Architecture (Non-Negotiable)

Booking creation and availability computation are delegated entirely to the database.

**Why?**
- Concurrent slot allocation requires database-level locking (handled by Postgres).
- The `create_booking` function uses `SELECT ... FOR UPDATE` to prevent double-booking.
- Python-level computation would race under concurrent requests.

```
GET /availability
  → BookingUseCases.availability()
    → PlatformRepository.get_available_slots()
      → SQL: SELECT slot_start, slot_end FROM get_available_slots(:staff_id, :date, :duration)
      → Slot starts advance by the selected service duration, not by app code.

POST /bookings
  → BookingUseCases.create_booking()
    → PlatformRepository.create_booking()
      → SQL: SELECT create_booking(:salon_id, :staff_id, :services, :start, ...)
```

Python **must never**:
- Compute available slots in Python
- Insert directly into `bookings` or `booking_services`

---

## Push Notification Architecture

Booking status changes trigger customer push notifications via a FastAPI `BackgroundTask`.

```
POST /bookings/{id}/approve
  → BookingUseCases.approve()
    → PlatformRepository.update_booking_status()   # synchronous — HTTP waits for this
    → background_tasks.add_task(_notify_customer)  # asynchronous — HTTP returns
      → PlatformRepository.create_notification()   # writes notifications row
      → FCMGateway.fan_out()                       # fires to all active device tokens
        → PlatformRepository._write_delivery()     # writes notification_deliveries row
```

FCM is a no-op if `FIREBASE_CREDENTIALS_JSON` is not configured.

---

## Auth Flow

```
Client  →  Authorization: Bearer <Supabase JWT>
        →  SupabaseJWTVerifier.verify_subject(token)
               → Fetches JWKS from Supabase (cached in-process)
               → Verifies signature, audience, issuer
               → Returns JWT sub (= Supabase user UUID)
        →  SQLProfileRepository.get_by_id(sub)
               → Resolves UUID to profiles row (role, is_active, etc.)
               → Role comes from the database — never from the token body
        →  set_actor_context(session, profile.id)
               → SET LOCAL request.jwt.claims = '{"sub": "..."}'
               → Lets audit triggers stamp the correct actor
```
