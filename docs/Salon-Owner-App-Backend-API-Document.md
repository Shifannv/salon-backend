# Salon Owner App Backend API Contract

This document describes the backend contract currently supported by the salon owner
app. Use `/openapi.json` for exact generated schemas.

## Audit result

The previous document claimed every owner endpoint was connected, but
`POST /v1/bookings/{booking_id}/delay` did not exist and holiday deletion returned
`501`. Both are now implemented. The review also added optional booking filters and
owner notifications for customer-created and customer-cancelled bookings.

The previous storage guidance was also stale. Backend-managed media uses Cloudflare R2,
not ImageKit. Clients upload through backend-issued signed gateway URLs; the backend
validates and processes bytes before writing R2 objects.

## Authentication

The owner app signs in with Supabase Auth and sends its access token as a bearer token.
The normal startup sequence is:

1. Complete Supabase OAuth.
2. Call `POST /v1/auth/owner-access` idempotently.
3. Call `GET /v1/auth/me`.
4. Call `GET /v1/salons/me`.
5. If `profile_completed` is false, complete onboarding through
   `POST /v1/salons/me/complete-profile`.
6. Read `approval_status` from the returned salon. Show the waiting screen for
   `pending`; show `rejection_reason` and allow corrections/resubmission for
   `rejected`. Enter daily business only when the salon is active, completed, and
   `approved`. Poll `GET /v1/salons/me` to refresh this state.

Completing onboarding returns 200 and saves the profile; it does not approve the
salon. Unapproved daily-business API calls return 403 with
`error.code = awaiting_admin_approval`. Setup editing remains available. See the
[salon approval contract](../backend/docs/SALON_APPROVAL.md) for the super admin
review endpoints and migration deployment steps.

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
| POST | `/v1/profiles/me/avatar-upload-url` | Signed gateway avatar upload |
| GET | `/v1/salons/me` | Owner salon |
| PATCH | `/v1/salons/me` | Update salon profile |
| POST | `/v1/salons/me/complete-profile` | Submit onboarding for super admin review |
| PATCH | `/v1/salons/me/settings` | Approval mode and working hours |
| GET | `/v1/salons/me/qr` | QR image URL or SVG |
| GET | `/v1/salons/me/payout-account` | Masked payout account (owner only) |
| PUT | `/v1/salons/me/payout-account` | Save UPI / bank payout details (merge) |
| GET | `/v1/salons/me/setup-status` | New-owner setup checklist |

### Images, services, and staff

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/v1/salons/me/images/upload-url` | Signed gateway salon-image upload |
| GET/POST | `/v1/salons/me/images` | List/create image records |
| PATCH/DELETE | `/v1/salons/me/images/{image_id}` | Update/soft-delete image |
| GET/POST | `/v1/salons/me/services` | List/create services |
| PATCH/DELETE | `/v1/salons/me/services/{service_id}` | Update/deactivate service |
| GET/POST | `/v1/salons/me/staff` | List/create staff |
| PATCH/DELETE | `/v1/salons/me/staff/{staff_id}` | Update/deactivate staff |
| POST | `/v1/salons/me/staff/{staff_id}/photo-upload-url` | Signed gateway staff-photo upload |
| GET/POST | `/v1/salons/me/staff/{staff_id}/services` | List/assign services |
| GET/PUT | `/v1/salons/me/staff/{staff_id}/services/{assignment_id}/languages` | Languages |

### Closures and blocked time

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | `/v1/salons/me/holidays` | List/create holidays |
| DELETE | `/v1/salons/me/holidays/{holiday_id}` | Soft-delete holiday |
| GET/POST | `/v1/salons/me/blocks` | List/create blocked slots |
| DELETE | `/v1/salons/me/blocks/{block_id}` | Delete ephemeral blocked slot |
| POST | `/v1/salons/me/closures/preview` | Preview affected active bookings |
| POST | `/v1/salons/me/closures` | Confirm closure and notify exact impact set |

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
| GET | `/v1/booking-action-requests` | List pending/resolved customer requests |
| POST | `/v1/booking-action-requests/{request_id}/respond` | Resolve a request |

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

Pay at Salon claims and late cancellations require migration
`0013_booking_action_requests`. Payment decisions are `received`/`not_received`;
cancellation decisions are `approve`/`decline`, and decline requires a reason. A stale
second decision returns `409`. Closure application requires the exact IDs returned by
the latest preview and also returns `409` if the overlap set changed.

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

## Payout account and setup checklist

Owner only (staff, customers and admins get 403). Both work while the salon is still
pending admin approval, like `complete-profile`.

`GET` and `PUT /v1/salons/me/payout-account` return the same masked shape:

```json
{"configured": true, "account_holder_name": "Asha Nair", "upi_id": "asha@okbank",
 "bank_name": "HDFC", "bank_account_last4": "9012", "ifsc": "HDFC0001234",
 "has_upi": true, "has_bank": true, "updated_at": "2026-10-11T10:00:00Z"}
```

When nothing is saved: `configured=false`, `has_upi=false`, `has_bank=false`, all else null.
The full account number is never returned.

`PUT` body (all optional, `extra` fields rejected): `account_holder_name` (2-100),
`upi_id` (`name@bank`, lowercased), `bank_name` (<=100), `bank_account_number` (9-18
digits), `ifsc` (uppercased, `AAAA0XXXXXX`). Merge semantics: an omitted field keeps its
stored value, an explicit `null` (or blank string) clears it. The merged result must have
a holder name and a UPI ID or (account number and IFSC), else 422.

`GET /v1/salons/me/setup-status` returns `completed_count`, `total_count`, `is_complete`
and `items` in this fixed order, each `{key, title, description, done, action}`:
`profile_basics`/`business_profile` (name, category, address, city), `working_hours`/
`working_hours` (one open day), `photos`/`photos` (one active image), `services`/`services`
(one active service), `staff`/`staff` (one active staff member), `payout`/`payout`.

## Media upload flow

For profile avatars, salon images, and staff photos:

1. Process the selected/captured image using the shared frontend utility.
2. Request a signed URL from the matching upload-url endpoint using the encoded MIME
   type and matching filename extension. The URL expires after 300 seconds.
3. `PUT` the processed binary to the returned backend gateway `upload_url` with the
   exact content type. It returns 204 after validation, processing and R2 storage.
4. Persist `public_url` using the relevant profile, salon-image, staff or service endpoint.

Only JPEG, PNG and WebP are accepted. Inputs are limited to 5242880 bytes, 40 million
pixels and 16384 pixels per edge; animation and malformed files are rejected. HEIC/HEIF
must be converted on the device, with a useful error if decoding is unavailable.
Output defaults: avatars 512 px/512000 bytes; staff 1024 px/1048576 bytes;
gallery and service photos 1600 px/1048576 bytes. Aspect ratio and alpha are preserved;
EXIF orientation is corrected and metadata stripped. JPEG/WebP quality starts at 84
with at most five encoding attempts; PNG uses lossless encoding and bounded resizing.

New photo references require the correct resource namespace and signed proof that
the stored object passed backend processing. Missing, foreign, unprocessed, expired,
spoofed or oversized uploads/references return 422 with `error.code=validation_error`.
Authentication and ownership failures retain their existing 401/403/404 behavior.
Existing legacy URLs still render and can remain unchanged; assigning a different
external URL is rejected. Bundled avatar identifiers remain supported.

An identical PUT retry against a still-valid grant succeeds without overwriting;
different bytes are rejected. The owner client retries network/5xx PUT failures once
using the same encoded bytes and grant. Repeating a gallery attachment with the same
URL returns its existing active row; change captions/ordering through PATCH.
Unreferenced managed media is retired by the scheduled cleanup worker. See
[media operations](../backend/docs/IMAGE_MEDIA.md) for deployment and retention details.

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

## Account deletion (owner)

Same four calls as the customer app (`POST /v1/account/deletion/challenges`, `.../verify`,
`POST /v1/account/deletion`, `GET /v1/account/deletion/{id}` with `X-Status-Token`).

- **Changed:** open bookings and pending booking-action requests no longer produce
  `409 deletion_blocked` for an owner. After the final confirm the backend (1) cancels every
  upcoming pending/confirmed booking at the owner's salons with `cancellation_reason:
  "salon_closed"`, (2) resolves open booking-action requests, (3) notifies each customer with
  fixed text that names no one, (4) refunds captured **online** payments through the payment
  gateway (cash / manually recorded payments are not refunded by the platform - the customer
  notice says so), (5) waits for refunds to settle, then (6) erases. There is no grace period.
- `409 deletion_blocked` for an owner now means only an active paid subscription
  (`details.active_subscriptions`, and only when a subscription provider is configured).
- The challenge response includes `bookings_to_cancel`: show "N upcoming bookings will be
  cancelled and refunded" before the final confirmation.
- The status response includes `stage` (`queued | refunding | waiting_for_refunds | erasing |
  completed`). While refunds settle `status` is `pending` and `stage` is
  `waiting_for_refunds`; this is normal and can last hours if the payment provider is slow.
- What is removed: the account, the salon's name/city/address/description/coordinates/QR/hours,
  images, holidays, payout details and their history, and provider references; staff logins that
  exist only for this salon are deleted. The salon remains as an anonymous "Closed salon" shell
  so customers keep their booking history. Details: `backend/docs/ACCOUNT_DELETION.md`.

## Payments and payout history (backend, dormant until a provider is configured)

Owner endpoints: `GET /v1/salons/me/payout-account/history` (newest first; entries have
`changed_at`, `action`, `changed_fields`, `changed_by_name`, `before`, `after` where
account numbers appear only as `bank_account_last4`), `GET /v1/salons/me/earnings`,
`GET /v1/salons/me/settlement-account`, `POST /v1/salons/me/settlement-account/register`,
`POST /v1/bookings/{id}/payments/{payment_id}/refund`, `GET /v1/bookings/{id}/payments`.
All POSTs need an `Idempotency-Key` header. `POST /v1/bookings/{id}/payment` keeps its
contract and may now return 409 `payment_in_progress`. `POST
/v1/booking-action-requests/{id}/respond` accepts optional `payment_method`
(`cash` default, or `online`). `BookingResponse` adds `currency`, `deposit_amount`,
`paid_amount`, `refunded_amount`, `payment_state`. With no provider, money endpoints return
503 `payment_provider_not_configured`. See `backend/docs/PAYMENTS.md`.

Status: BUILT (backend); DORMANT pending a provider; NOT BUILT: owner-app screens.
