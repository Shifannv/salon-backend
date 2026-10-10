# Customer App Backend API Contract

This document describes the backend contract for customer-app integration. The
customer app must be updated to use the booking action request fields and endpoints.
The running FastAPI OpenAPI document at `/openapi.json` is the field-level source of
truth.

## Audit result

The earlier document incorrectly marked avatar upload and salon reporting as missing.
Both are implemented and tested:

- `POST /v1/customer/profile/avatar`
- `POST /v1/reports`

This review also added:

- `POST /v1/notifications/read-all`
- optional filters and pagination on `GET /v1/bookings`
- owner notifications when a customer creates or cancels a booking
- `can_cancel=false` once a booking start time has passed
- one consistent validation-error envelope

Reviews, cloud favorites, and style-photo publishing remain future features because the
provided app document does not define an active frontend integration or complete
acceptance criteria for them.

## Authentication

The app signs in with Supabase Auth and sends the access token on protected requests:

```http
Authorization: Bearer <supabase-access-token>
```

The backend verifies the JWT through Supabase JWKS and resolves the role from the
`profiles` table. OAuth and password exchange remain frontend-to-Supabase operations.
`POST /v1/auth/refresh` exists for clients that want backend-assisted refresh, but it is
not required when the Supabase client refreshes the session directly.

## Endpoint summary

Public endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Process health |
| GET | `/health/db` | Database health |
| GET | `/v1/salons` | Search/filter salons |
| GET | `/v1/salons/nearby` | Distance-sorted salons |
| GET | `/v1/salons/{salon_id}` | Salon details |
| GET | `/v1/salons/{salon_id}/services` | Active services |
| GET | `/v1/salons/{salon_id}/staff` | Active staff |
| GET | `/v1/catalog/categories` | Active categories |
| GET | `/v1/catalog/categories/{category_id}/subcategories` | Active subcategories |
| GET | `/v1/availability` | Database-owned availability |

Protected customer endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/customer/profile` | Current profile |
| PATCH | `/v1/customer/profile` | Update name, phone, or avatar URL |
| POST | `/v1/customer/profile/avatar` | Validate, upload, and persist avatar |
| POST | `/v1/bookings` | Create through `create_booking` |
| GET | `/v1/bookings` | List the customer's bookings |
| GET | `/v1/bookings/{booking_id}` | Booking details |
| POST | `/v1/bookings/{booking_id}/cancel` | Cancel an owned future booking |
| POST | `/v1/bookings/{booking_id}/cancellation-requests` | Request late cancellation |
| POST | `/v1/bookings/{booking_id}/payment-confirmation-requests` | Claim Pay at Salon payment |
| GET | `/v1/notifications` | List notifications |
| POST | `/v1/notifications/{notification_id}/read` | Mark one notification read |
| POST | `/v1/notifications/read-all` | Mark all notifications read |
| POST | `/v1/devices` | Register/reactivate a push token |
| DELETE | `/v1/devices/{token}` | Deactivate an owned push token |
| POST | `/v1/reports` | Submit a salon report |

## Important request contracts

### Avatar upload

```http
POST /v1/customer/profile/avatar
Content-Type: multipart/form-data
```

The form field is `image`. JPEG, PNG, and WebP files up to 5242880 bytes (5 MiB) are accepted. The
backend validates decoding and MIME agreement, corrects EXIF orientation, strips metadata,
resizes without upscaling to at most 512 px and encodes to at most 512000 bytes by default.
It preserves PNG/WebP transparency, uploads only the processed bytes to Cloudflare R2, updates
`profiles.avatar_url`, and returns:

```json
{ "avatar_url": "https://media.example.com/avatars/..." }
```

The frontend does not need a second profile PATCH after this call.

Both gallery and camera selections use the shared processing utility before upload.
Malformed, animated, unsupported or oversized inputs return 422 (`validation_error`);
HEIC/HEIF must first be converted on the device. The backend rejects images over
40 million pixels or 16384 px per edge. Failure never falls back to the original file.
Replaced managed avatars are retired only after committed database reference checks
by the cleanup worker; older unmarked production media is preserved. New hosted avatar
URLs supplied to profile PATCH must belong to the actor and have trusted processing
proof. Existing unchanged URLs and bundled avatar identifiers remain supported.

### Salon report

```json
{
  "salon_id": "uuid",
  "salon_name": "accepted but not trusted",
  "reason": "Rude behavior",
  "details": "Additional context",
  "created_at": "accepted but ignored"
}
```

Reporter identity and timestamps are server-owned. Response status is `201`:

```json
{ "id": "uuid", "status": "received" }
```

### Availability

```http
GET /v1/availability?staff_id=<uuid>&date=2026-09-25&service_ids=<uuid>&service_ids=<uuid>
```

The backend calls Postgres `get_available_slots`; clients must not compute slots.

### Create booking

```json
{
  "salon_id": "uuid",
  "staff_id": "uuid",
  "service_ids": ["uuid"],
  "start_datetime": "2026-09-25T09:00:00+05:30",
  "customer_name": "Customer name",
  "customer_phone": "+919876543210",
  "source": "app",
  "notes": null
}
```

The backend calls Postgres `create_booking`. A concurrent slot conflict returns `409`
with code `slot_unavailable`.

### Booking list filters

All parameters are optional. Omitting them preserves the existing unpaginated response.

| Parameter | Values |
| --- | --- |
| `status` | `pending`, `confirmed`, `rejected`, `completed`, `cancelled` |
| `source` | `app`, `manual_walkin`, `qr_walkin` |
| `date_from` | `YYYY-MM-DD`, inclusive |
| `date_to` | `YYYY-MM-DD`, inclusive |
| `limit` | 1-200 |
| `offset` | 0 or greater; used with `limit` |

### Bulk notification read

```http
POST /v1/notifications/read-all
```

```json
{ "updated_count": 5 }
```

## Booking action requests

`POST /v1/bookings/{booking_id}/payment` is owner/staff-only because it records a
booking as paid. The customer app must not call it.

Set `payment_preference: "pay_at_salon"` when creating a cash-at-visit booking. It stays
`payment_status: "unpaid"`. Once the visit begins and `can_confirm_payment` is true, the
customer may call `POST /v1/bookings/{id}/payment-confirmation-requests`. Booking
list/detail responses expose the latest request status, decision, and reason. Only an
owner `received` decision changes the booking to paid; `not_received` leaves it unpaid.

`can_cancel` enables direct cancellation before the server cutoff.
`can_request_cancellation` enables
`POST /v1/bookings/{id}/cancellation-requests` after the cutoff. The booking and slot
remain active until the salon approves. Online payment still requires a payment provider,
server-created payment intent, and verified webhook.

## Push and realtime behavior

- New app/QR bookings notify the salon owner.
- Customer cancellation notifies the salon owner.
- Owner approval, rejection, completion, cancellation, and delay events notify affected
  customers.
- Device registration uses `/v1/devices`.
- Supabase Realtime may be used as an invalidation signal; all business mutations still
  go through FastAPI.

Scheduled reminders are not produced by the request/response API. They require a
separate scheduled worker or cloud scheduler job.

## Error contract

Expected application and request-validation errors use:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": []
  }
}
```

Common codes are `unauthorized`, `forbidden`, `not_found`, `validation_error`,
`conflict`, `slot_unavailable`, `service_unavailable`, and `internal_error`. Raw SQL,
constraint names, credentials, and stack traces are never returned.
