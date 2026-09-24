# Salon Owner App Backend API Contract

This document describes the backend contract currently supported by the salon owner
app. Use `/openapi.json` for exact generated schemas.

## Audit result

The previous document claimed every owner endpoint was connected, but
`POST /v1/bookings/{booking_id}/delay` did not exist and holiday deletion returned
`501`. Both are now implemented. The review also added optional booking filters and
owner notifications for customer-created and customer-cancelled bookings.

The previous storage guidance was also stale. Backend-managed media uses Cloudflare R2,
not ImageKit. Clients may upload directly only through backend-issued presigned URLs.

## Authentication

The owner app signs in with Supabase Auth and sends its access token as a bearer token.
The normal startup sequence is:

1. Complete Supabase OAuth.
2. Call `POST /v1/auth/owner-access` idempotently.
3. Call `GET /v1/auth/me`.
4. Call `GET /v1/salons/me`.
5. If no salon exists, complete onboarding through
   `POST /v1/salons/me/complete-profile`.

The backend also exposes `POST /v1/auth/refresh`, although the Supabase client may
refresh directly. Profile changes use `/v1/profiles/me`; account email changes remain a
Supabase Auth operation.

## Endpoint summary

### Profile and salon

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/v1/auth/owner-access` | Claim/confirm owner access |
| GET | `/v1/auth/me` | Current actor |
| GET | `/v1/profiles/me` | Current profile |
| PATCH | `/v1/profiles/me` | Update name, phone, or avatar URL |
| POST | `/v1/profiles/me/avatar-upload-url` | Presigned avatar upload |
| GET | `/v1/salons/me` | Owner salon |
| PATCH | `/v1/salons/me` | Update salon profile |
| POST | `/v1/salons/me/complete-profile` | Complete onboarding/go live |
| PATCH | `/v1/salons/me/settings` | Approval mode and working hours |
| GET | `/v1/salons/me/qr` | QR image URL or SVG |

### Images, services, and staff

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/v1/salons/me/images/upload-url` | Presigned salon-image upload |
| GET/POST | `/v1/salons/me/images` | List/create image records |
| PATCH/DELETE | `/v1/salons/me/images/{image_id}` | Update/soft-delete image |
| GET/POST | `/v1/salons/me/services` | List/create services |
| PATCH/DELETE | `/v1/salons/me/services/{service_id}` | Update/deactivate service |
| GET/POST | `/v1/salons/me/staff` | List/create staff |
| PATCH/DELETE | `/v1/salons/me/staff/{staff_id}` | Update/deactivate staff |
| POST | `/v1/salons/me/staff/{staff_id}/photo-upload-url` | Presigned staff-photo upload |
| GET/POST | `/v1/salons/me/staff/{staff_id}/services` | List/assign services |
| GET/PUT | `/v1/salons/me/staff/{staff_id}/services/{assignment_id}/languages` | Languages |

### Closures and blocked time

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | `/v1/salons/me/holidays` | List/create holidays |
| DELETE | `/v1/salons/me/holidays/{holiday_id}` | Soft-delete holiday |
| GET/POST | `/v1/salons/me/blocks` | List/create blocked slots |
| DELETE | `/v1/salons/me/blocks/{block_id}` | Delete ephemeral blocked slot |

Holiday deletion requires migration `0011_holiday_soft_delete`. Deleted holidays no
longer close availability or block booking creation.

### Bookings

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/availability` | Database-owned slots |
| POST | `/v1/bookings` | Create manual walk-in |
| GET | `/v1/bookings` | Role-scoped booking list |
| GET | `/v1/bookings/{booking_id}` | Booking details |
| POST | `/v1/bookings/{booking_id}/approve` | Confirm pending booking |
| POST | `/v1/bookings/{booking_id}/reject` | Reject with reason |
| POST | `/v1/bookings/{booking_id}/complete` | Complete booking |
| POST | `/v1/bookings/{booking_id}/delay` | Record delayed estimate |
| POST | `/v1/bookings/{booking_id}/cancel/barber` | Cancel with owner reason |
| POST | `/v1/bookings/{booking_id}/payment` | Mark payment recorded |

`GET /v1/bookings` accepts optional `status`, `source`, `date_from`, `date_to`,
`limit`, and `offset` parameters. Existing clients can omit all parameters and continue
receiving the complete role-scoped list.

Delay request:

```json
{
  "estimated_end_datetime": "2026-09-24T12:30:00+05:30",
  "notify_affected_customers": true
}
```

The estimate must be later than the booking's original `end_datetime`. The response
includes `estimated_end_datetime`. When notification is enabled, customers with later
active bookings for the same staff whose start falls inside the delay window receive a
`booking_delayed` notification. This requires migration `0012_booking_delay`.

### Notifications, devices, and catalog

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/notifications` | Owner notifications |
| POST | `/v1/notifications/{notification_id}/read` | Mark one read |
| POST | `/v1/notifications/read-all` | Mark all read |
| POST | `/v1/devices` | Register/reactivate push token |
| DELETE | `/v1/devices/{token}` | Deactivate owned token |
| GET | `/v1/catalog/categories` | Active categories |
| GET | `/v1/catalog/categories/{category_id}/subcategories` | Active subcategories |

## Media upload flow

For profile avatars, salon images, and staff photos:

1. Request a presigned URL from the matching upload-url endpoint.
2. `PUT` the binary directly to `upload_url` with the exact requested content type.
3. Persist `public_url` using the relevant profile, salon-image, or staff endpoint.

Never place R2 credentials in the owner app. The customer multipart avatar endpoint is
separate and should not be reused for salon or staff images.

## Push and realtime behavior

- App and QR bookings notify the salon owner.
- Customer cancellations notify the salon owner.
- Approval, rejection, completion, salon cancellation, and applicable delay events
  notify customers.
- Realtime on `bookings` and `blocked_slots` may invalidate cached screens, but all
  writes continue through FastAPI.

## Remaining boundaries

- “Any staff” availability is not implemented because no request/response selection
  contract was provided. Continue requesting availability per selected staff member.
- Scheduled reminders need a scheduler/worker and are not produced by an HTTP request.
- Online payment requires a payment provider and verified webhook. The existing payment
  endpoint records an owner/staff-confirmed payment only.
- OpenAPI already exists at `/openapi.json`; frontend types can be generated from it.
