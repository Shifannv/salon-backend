# Booking Flow

Booking implementation is intentionally not migrated in Phase 1.

Required Phase 4 rules:

- Availability delegates to `get_available_slots`.
- Booking creation delegates to `create_booking`.
- The API must not insert directly into `bookings` or `booking_services`.
- `booking_services` rows are immutable snapshots from the database function.
- `SlotUnavailableError` maps to HTTP `409`.

## Customer App

```mermaid
sequenceDiagram
  participant Client
  participant API
  participant DB
  Client->>API: GET /v1/availability
  API->>DB: select * from get_available_slots(...)
  DB-->>API: slots
  Client->>API: POST /v1/bookings
  API->>DB: select create_booking(...)
  DB-->>API: booking snapshot
```

## Manual Walk-in

```mermaid
sequenceDiagram
  participant Owner
  participant API
  participant DB
  Owner->>API: POST /v1/bookings source=manual_walkin
  API->>DB: select create_booking(...)
```

## QR Walk-in

```mermaid
sequenceDiagram
  participant Web
  participant API
  participant Supabase
  participant DB
  Web->>API: GET /v1/walkin/{qr_token}
  Web->>API: POST /v1/walkin/{qr_token}/verify-phone
  API->>Supabase: OTP send/verify
  Web->>API: POST /v1/walkin/{qr_token}/bookings
  API->>DB: select create_booking(...)
```
