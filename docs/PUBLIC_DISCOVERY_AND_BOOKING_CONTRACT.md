# Public discovery, QR and booking contract

For the customer website, customer app and any other client of the public salon API.
Everything below is implemented and tested; no database migration was needed.
Regenerate your OpenAPI client after pulling this change.

## 1. Search salons by name, area and service

`GET /v1/salons` and `GET /v1/salons/nearby` accept the same text filters. All are optional, combine with AND,
are case-insensitive and at most 80 characters (longer returns 422 `validation_error`). `%` and `_` are literal.

| Parameter | Matches |
|---|---|
| `search` | salon name, city **or** address (contains) |
| `city` | the city exactly, ignoring case and surrounding spaces |
| `service` | a bookable service's name or subcategory name (contains), for example `haircut`, `facial` |
| `category` | service category name (existing; unchanged) |
| `lat`/`lng` (or `latitude`/`longitude`) | distance ordering and `distance_km`; works without `city` |

A service counts only if the salon could be booked for it right now: the service and its subcategory are
active and at least one active staff member of that salon is assigned to it. Salons that are hidden, inactive,
unapproved, incomplete or not booking-eligible never appear, whatever the filters. Results are the same
`SalonSummaryResponse` items as before (the matched service is not returned; fetch `/v1/salons/{id}/services`).

No index was added: the contains-matches cannot use a btree index, and the table is small. If the salon count
grows into the tens of thousands, add `lower(city)` and a `pg_trgm` index on `name` in a reviewed migration.

## 2. Payment capability (`payment_options`)

Backend-owned and recomputed on every response (never cached). Present on `SalonSummaryResponse`,
`SalonDetailResponse` and the walk-in resolver `WalkInSalonResponse`:

| Field | Meaning |
|---|---|
| `accepts_bookings` | `false` while the owner has paused bookings |
| `payment_options` | methods permitted for a **new booking at this salon right now**: `[]` when paused, `["PAY_AT_SALON"]` normally, plus `"PAY_ONLINE"` only when the platform gateway is enabled |
| `online_payment_available` | `true` only when `PAY_ONLINE` is listed |
| `online_payment_unavailable_reason` | customer-facing text, `null` when available |

Online payment (UPI/Cashfree) stays disabled: `PAY_ONLINE` is not listed and `payment_preference` of
`pay_advance`/`pay_full` returns **422 `online_payment_unavailable`** ("Online payment coming soon.") until the gateway is enabled. It is checked inside the booking command on both `POST /v1/bookings` and the QR route, before any booking, notification or idempotency record is written, so nothing is created.
Customer-specific blocks are not salon capabilities; they come back when booking as 409
`pay_at_salon_daily_limit`, `pay_at_salon_temporarily_blocked` or `payment_collection_required`. 409 `slot_unavailable` means only a real slot conflict, so a client may offer other times on it; never retry a 422 unchanged.
UIs should show a payment method only when it is in `payment_options`, and nothing about payment otherwise.

## 3. QR contract

- **Printed payload:** `<WALKIN_BASE_URL>/<qr_token>`. `WALKIN_BASE_URL` must end with the web route, so a deployed
  value is `https://<website-origin>/s` and the QR encodes `https://<website-origin>/s/<qr_token>`
  (the code default is now `http://localhost:3000/s`).
- **Token:** issued by the database (`encode(gen_random_bytes(16), 'hex')`): 32 lowercase hex characters, unique,
  with no time-based expiry; the API has no rotation endpoint. Clients should treat it as opaque and accept URL-safe characters
  `A-Za-z0-9_-`, 3 to 128 long; the backend rejects anything else without a lookup.
- **Where a token may appear:** only in the route-specific resolver `GET /v1/walkin/{qr_token}` (which echoes the
  caller's own token) and in the owner's own salon payload. It is **not** in `/v1/salons`, `/v1/salons/nearby`,
  `/v1/salons/{id}`, `/services` or `/staff` (removed from the schemas and the SQL; a stale cache entry cannot
  leak it because the response model filters it).
- **Failures:** a malformed, unknown, rotated, erased or unpublished token returns one response, 404 with
  `error.code = "qr_not_found"` (message "Salon not found or not accepting walk-ins"). The cause is not revealed.
  Cached salon data is revalidated against Postgres on every hit, so a token stops working immediately.
  A token is invalidated by rotation/regeneration (account erasure issues a new one), by salon unpublication or by
  account erasure. No time-based expiry is currently implemented.
- **Booking by QR:** `POST /v1/walkin/{qr_token}/bookings` needs a customer bearer token (401 without; 403 `forbidden`
  for owners and staff). A `salon_id` that differs from the token's salon returns 422 `qr_salon_mismatch`.
  The server always sets `source = "qr_walkin"` itself after validating the token; the client need not send `source`, and any value it sends is overwritten. `pay_advance`/`pay_full` return 422 `online_payment_unavailable` while online payment is disabled, as on `POST /v1/bookings`.

## 4. Booking directly by salon id

This already exists and is now explicit: **`POST /v1/bookings`** with `source: "app"`.

- **Auth:** bearer token of an active `customer` (or `owner`, booking as a customer). Role comes from the
  database. 401 without a token; 403 for staff.
- **Trusts nothing priced:** the body is `salon_id`, `staff_id`, `service_ids`, `start_datetime`, `customer_name`,
  optional `customer_phone`, `notes`, `payment_preference`. Price, duration and end time are computed by Postgres
  `create_booking()` from the service ids; unknown fields are ignored. The slot is validated by the database
  (`get_available_slots()` rules): a taken or invalid slot returns 409 `slot_unavailable`.
- **Salon must be public:** unpublished salons return 404 `not_found`; a paused salon returns 409
  `salon_not_accepting_bookings`.
- **Source cannot be forged:** `source: "qr_walkin"` on this route returns 422 `booking_source_not_allowed`.
  `manual_walkin` stays owner/staff only. The QR flow is unchanged.
- **Source:** a direct booking is stored with `source = "app"` (no separate website source exists). Only the QR route
  stores `qr_walkin`, which it assigns itself after validating the token.
- **Idempotency (both routes):** send `Idempotency-Key` (8-200 characters). The stored record is unique per
  *authenticated customer id* + *scope* + *key*, with a SHA-256 fingerprint of the whole request:
  - scope is `booking:create` on `POST /v1/bookings` and `booking:qr:<validated salon id>:<hash of token>` on the QR route;
  - same customer, scope, key and request: the original booking is replayed (no second booking or notification);
  - another customer with the same key gets their own record, never the first customer's booking;
  - same customer and key with a different request: **422 `idempotency_key_reused`**;
  - a duplicate sent while the first is still running waits for it in the database and then replays it;
    a failed first attempt leaves no record, so the key can be retried;
  - the token and salon are revalidated before a replay, so an invalidated token returns 404 `qr_not_found`;
  - records expire after 24 hours.

**Open decision (not built):** this route needs a signed-in customer. The customer app signs in with Supabase
phone OTP. The website's only OTP route today is keyed by QR token (`/v1/walkin/{qr_token}/verify-phone`). A
salon-id OTP endpoint would let anyone with a public salon id trigger SMS, so it was **not** added. Choose one:
sign in through Supabase phone OTP from the website BFF (no backend change), or approve a salon-id OTP route with
its own rate limits and CAPTCHA.

## 5. Error codes

All errors use `{"error": {"code", "message", "details?"}}`. New or newly guaranteed codes:

| Code | HTTP | When |
|---|---|---|
| `qr_not_found` | 404 | QR token malformed, unknown, rotated, erased or its salon unpublished (tokens have no time-based expiry) |
| `qr_salon_mismatch` | 422 | QR booking names a different salon than the token |
| `booking_source_not_allowed` | 422 | `source: "qr_walkin"` on `POST /v1/bookings` |
| `unauthorized` | 401 | missing bearer token (previously a bare `{"detail": ...}`; `detail` is still returned) |
| `not_found` | 404 | unknown route (same envelope, `detail` kept) |
| `validation_error` | 422 | over-long `search`, `city` or `service` |
| `online_payment_unavailable` | 422 | `pay_advance`/`pay_full` while online payment is off (direct and QR) |
| `idempotency_key_reused` | 422 | booking `Idempotency-Key` reused by the same customer for a different request (payments keep 409 `idempotency_key_reuse`) |

Existing: `slot_unavailable` (409, real slot conflict only), `salon_not_accepting_bookings`, `pay_at_salon_daily_limit`,
`pay_at_salon_temporarily_blocked`, `payment_collection_required`, `forbidden`, `conflict`.

## 6. Client follow-ups

- Regenerate OpenAPI types (the customer app's `openapi.generated.ts` and the website's committed schema still
  list `qr_token` on public salon models and lack `payment_options`, `service` and `qr_not_found`).
- Website: use `service` for service search, `payment_options` for payment wording, and drop the proxy's
  `qr_token` stripping once nothing depends on it.
- Printed QR codes made before `WALKIN_BASE_URL` ends in `/s` was set would not resolve; confirm the deployed value.

## 7. What was verified, and how

- **Real PostgreSQL 18** (a throwaway container on `127.0.0.1:55432`, schema built by the Alembic chain to the
  portable CI revision, then removed): `backend/tests/integration/test_booking_contract_sql.py`, 8 tests. They run
  the actual `create_booking()` and `payment_idempotency_keys`, and cover: QR booking stored as `qr_walkin`; direct
  booking stored as `app`; client-sent price, end time and duration ignored (250.00, 30 minutes); two overlapping
  attempts give one booking and one 409 `slot_unavailable`; same-key replay; two customers with one key never
  sharing a booking; 422 `idempotency_key_reused`; online payment refused with no booking and no idempotency row.
  `test_checkout_safety_sql.py` (15 tests) also passes against it.
- **Mocked repository only** (`backend/tests/unit/test_walkin_qr_contract.py`): HTTP routing and authorization,
  error envelopes, token-format rejection, notification suppression on replay, scope string contents.
- **Redis recovery** (`test_redis_recovery_sql.py`, throwaway Redis on `127.0.0.1:16479` plus the same PostgreSQL):
  16 of 20 pass, including the booking replay and changed-payload test, which now expects 422
  `idempotency_key_reused`, with one booking and no extra notification. The 4 Playwright browser tests could not run
  because the Node `playwright` module is not installed; they do not exercise booking.
- **Not verified:** a database that has Supabase-only objects; the 4 browser tests; any deployed environment.
