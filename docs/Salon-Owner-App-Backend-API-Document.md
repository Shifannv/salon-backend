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

### Payments and payee onboarding: stage 1 additions (backend only, dormant, not sandbox-tested)

Money is `Decimal` strings in rupees. All POSTs require `Idempotency-Key` (same key + same body replays).

`POST /v1/salons/me/settlement-account/register` (owner of an approved salon). Body is required for providers
that need KYC (Cashfree) and optional otherwise. Either `bank_account_number` + `ifsc`, or `upi_id`:

```json
{"legal_name": "Asha Salon", "contact_email": "owner@example.com", "contact_phone": "9876543210",
 "account_type": "individual", "business_type": "salon", "pan": "ABCDE1234F",
 "bank_account_number": "123456789012", "ifsc": "HDFC0001234"}
```

These values are sent once to the provider and never stored, logged, returned or echoed in an error (a 422 shows
only field names and messages, never the submitted values). 200 and `GET /v1/salons/me/settlement-account`:

```json
{"provider_enabled": true, "supported": true, "requires_details": true, "onboarding_status": "pending",
 "requirements": ["Your KYC details are being reviewed."], "account_reference_masked": "...g1"}
```

`onboarding_status` is one of `not_started | pending | needs_action | active | rejected | suspended`;
`requirements` is actionable text (empty when `active`). Customers can pay only while `active`. Calling register
again after a bank detail change (from any non-pending status) starts a fresh registration: the status returns
to `pending`, an audit row is written and online payments pause until it is `active` again. Errors: 403 not an
owner, 422 invalid details or missing details, 502 `payment_provider_error` / `payment_outcome_unknown` (retry
with the same key; the pending registration is reused), 503 provider not configured.

`GET /v1/salons/me/earnings` -> 200 (all from the immutable commission snapshot; provider fees/taxes are not
included):

```json
{"currency": "INR", "online_collected": "1000.00", "online_refunded": "400.00", "platform_fees": "100.00",
 "commission_reversed": "40.00", "platform_commission_net": "60.00", "overcollected": "0.00",
 "online_net": "540.00", "manual_recorded": "0.00", "online_payment_count": 1, "manual_payment_count": 0,
 "note": "..."}
```

`POST /v1/bookings/{id}/payments/{payment_id}/refund` body `{"amount": "250.00", "reason": "..."}` (`amount`
optional). The row is created before the provider is asked; a 502 `payment_outcome_unknown` means it may still
have been issued: retry with the SAME `Idempotency-Key` (the same provider refund id is re-sent). Refunds go to
the provider that holds the payment. If the payment has an `overcollected_amount`, the excess is refunded first
(omit `amount` to refund it; a larger amount is 422) and the booking stays paid. The commission share is
reversed proportionally (not for excess refunds). `GET /v1/bookings/{id}/payments` shows `refunds[].applies_to_excess`.

## Subscription billing (backend only, dormant, not sandbox-tested)

**Website purchase flow.** The owner mobile app must NOT show prices or a purchase control (store policy);
it only reads entitlement. The website uses the same Supabase JWT. Provider default is `none`: every money
route answers `503 payment_provider_not_configured`. Money is a `Decimal` **string in rupees** (`"349.00"`);
only `client_payload.amount` is an integer in **paise** because the checkout widget needs it. Owner role only
(`403` for customer, staff, super admin; `403` for an owner without an active salon). Admin manual/test
activation under `/v1/admin/...` is admin-only and must never be called by a frontend.
Errors use the standard `{"error": {"code", "message", "details"}}` envelope.

### `GET /v1/subscriptions/config` (no auth, always 200)

```json
{"enabled": false, "provider": null, "mode": "one_time", "renewal": "manual",
 "native_purchase_allowed": false, "public_key": null, "currency": "INR"}
```
Enabled: `"enabled": true, "provider": "razorpay", "public_key": "rzp_test_..."` (the public key id only).

### `GET /v1/subscription-plans` (owner)

```json
[{"id": "uuid", "code": "growth_1m", "name": "Growth - 1 month", "description": null, "tier": 1,
  "price_amount": "349.00", "currency": "INR", "billing_interval": "monthly",
  "features": {"unlimited_bookings": true, "split_bill": true, "daily_ledger": true},
  "tax_inclusive": null}]
```
`billing_interval` is `monthly | quarterly | semiannual | yearly`. `tax_inclusive` null = GST treatment undecided.
Premium plans add `rank_boost`, `smart_slot_filler`, `sms_alerts` and `monthly_alert_cap: 300`.

### `GET /v1/salons/me/subscription` (owner)

```json
{"provider_enabled": true, "status": "active",
 "plan": {"id": "uuid", "code": "growth_1m", "name": "Growth - 1 month", "tier": 1},
 "entitlement_active": true, "entitlement_state": "active",
 "features": {"split_bill": true}, "paid_through": "2026-11-12T18:42:26Z",
 "grace_ends_at": null, "in_grace": false, "renewal": "manual",
 "cancelled": false, "cancelled_at": null,
 "latest_payment": {"id": "uuid", "plan_code": "growth_1m", "status": "paid", "amount": "349.00",
   "currency": "INR", "billing_interval": "monthly", "tax_amount": null, "tax_inclusive": null,
   "refunded_amount": "0.00", "order_ref": "order_...", "receipt": "sub_...", "period_start": "...",
   "period_end": "...", "expires_at": "...", "paid_at": "...", "applied_at": "...",
   "payment_verified": true, "entitlement_applied": true, "created_at": "..."},
 "open_checkout": null, "verification": null}
```
`entitlement_state`: `none | active | cancelled_paid_through | grace | expired | suspended`. `status` is null
when the salon never subscribed (`entitlement_active` false, `plan` null). `features` is `{}` unless entitled.
`payment_verified` (the provider confirmed the payment) and `entitlement_applied` (the backend granted access) are
different facts. `grace_ends_at` is non-null only while `in_grace`. Viewing this never requires an active plan.

### `POST /v1/salons/me/subscription/checkout` (owner, approved salon)

Header `Idempotency-Key: <8-200 chars>` is **required** (`400 idempotency_key_required`). Same key + same body
replays the stored response; same key + different `plan_id` is `409 idempotency_key_reuse`.

```json
{"plan_id": "uuid"}
```
200:
```json
{"billing_id": "uuid", "provider": "razorpay", "order_ref": "order_Nabc123", "receipt": "sub_1f3c...",
 "plan_id": "uuid", "plan_code": "growth_1m", "amount": "349.00", "currency": "INR",
 "billing_interval": "monthly", "expires_at": "2026-10-13T10:00:00+00:00",
 "client_payload": {"key_id": "rzp_test_...", "order_id": "order_Nabc123", "amount": 34900, "currency": "INR"}}
```
The amount is the plan price **at this moment**, snapshotted server side (a later price change never alters this
purchase). The purchase row is committed before the provider is called. Errors: `404` plan missing/inactive/free;
`409 conflict` suspended subscription, a different plan while a paid period runs, or a different plan already open;
`503` billing off; `502 payment_provider_error` (definitive refusal: nothing was created; retry);
`502 payment_outcome_unknown` (timeout): **retry with the SAME key**, the open purchase is resumed by its receipt and
no second order is created. A second checkout of the same plan while one is open returns the same order.

### `POST /v1/salons/me/subscription/verify` (owner)

```json
{"order_ref": "order_Nabc123", "payment_ref": "pay_...", "signature": "<hex>"}
```
`payment_ref`/`signature` are optional and only a **hint** of which payment to fetch; they never grant access.
The backend fetches the provider's payments for the order and activates only for a captured payment with the
snapshot's amount and currency. Response: the subscription state above plus `"verification"`:
`started | renewed | already_applied | pending | no_order | mismatch | duplicate_payment | blocked_suspended |
blocked_closed`. Safe to call repeatedly (activation happens at most once). `404` for another salon's order.
`pending` = not paid at the provider yet. The webhook and the worker apply the same result without this call.

### `POST /v1/salons/me/subscription/cancel` (owner)

No body, no key needed (idempotent), works even when billing is off. Sets status `cancelled`/`cancelled_at`;
paid-through access remains (`entitlement_state: "cancelled_paid_through"`). Buying again before the period ends
renews the same subscription. `404` when the salon never subscribed. Returns the subscription state.

### `GET /v1/salons/me/subscription/payments?limit=50&offset=0` (owner)

Array of the `latest_payment` shape, newest first (`limit` 1-200). Available after expiry and when billing is off.

### `GET /v1/salons/me/access-state` (owner, thin stub)

```json
{"access_state": "subscribed_growth", "entitlement_active": true, "entitlement_state": "active",
 "features": {"split_bill": true}, "paid_through": "2026-11-12T18:42:26Z", "grace_ends_at": null,
 "source": "subscription"}
```
`access_state`: `not_subscribed | subscribed | subscribed_growth | subscribed_premium` (tier 1 / >= 2 / other). It
reflects the subscription alone; trial and soft-lock states are added later by extending `derive_entitlement`.

### Webhook (provider to backend, not an app route)

`POST /v1/webhooks/razorpay`, signed with `SUBSCRIPTION_RAZORPAY_WEBHOOK_SECRET`; see `backend/docs/SUBSCRIPTIONS.md`.
Status: BUILT (backend); DORMANT; NOT sandbox-tested; NOT BUILT: website screens, owner-app screens (by decision).
