# Salon Platform API Reference

A concise integration guide for the shared FastAPI backend.

For frontend setup, authentication, uploads, QR rendering, reports, and deployment
checklists, use the canonical [Frontend Integration Guide](../../docs/frontend-integration.md).

> **API prefix:** `/v1`  
> **Interactive API documentation:** `http://localhost:8000/docs`

## Contents

- [Configuration](#configuration)
- [Authentication and conventions](#authentication-and-conventions)
- [Endpoint index](#endpoint-index)
- [Core integration flows](#core-integration-flows)
- [Important implementation notes](#important-implementation-notes)

---

## Configuration

| Environment | Base URL |
| --- | --- |
| Local development | `http://localhost:8000` |
| Mobile device on the same network | `http://YOUR_MAC_IP:8000` |
| Production | `https://api.yourdomain.com` |

### Frontend environment variables

```bash
# Expo / React Native
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_SUPABASE_URL=https://[PROJECT_REF].supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=eyJ...

# Next.js
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Keep `DATABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `FIREBASE_CREDENTIALS_JSON` on the server. Never expose them in a frontend bundle.

---

## Authentication and conventions

### Authentication

Protected endpoints require a Supabase access token:

```http
Authorization: Bearer <supabase_access_token>
Content-Type: application/json
```

Use Supabase Auth in the client for Google sign-in and session persistence. Native Expo builds should call Supabase `signInWithOAuth` with `skipBrowserRedirect: true`, open the returned URL with Expo `WebBrowser.openAuthSessionAsync`, and exchange the returned PKCE code with `supabase.auth.exchangeCodeForSession`. The backend validates the resulting Supabase JWT and determines the role from `profiles.role`.

The owner app scheme is `salonowner`; add this exact native redirect URL to Supabase Dashboard -> Authentication -> URL Configuration -> Redirect URLs:

```txt
salonowner://auth/callback
```

| Role | Primary access |
| --- | --- |
| `customer` | Profile, salon discovery, bookings, notifications |
| `owner` | Salon, services, staff, schedules, booking operations |
| `staff` | Authorized operational booking actions |
| `super_admin` | Salon provisioning and catalog management |

### Data conventions

| Value | Format / handling |
| --- | --- |
| IDs | UUID strings |
| Dates | `YYYY-MM-DD` |
| Date-times | ISO 8601, for example `2026-08-10T09:00:00Z` |
| Money | Returned as strings; send a number or string when the request allows it |
| Pagination | `limit` and `offset` query parameters |
| Error body | `{ "error": { "code": "...", "message": "..." } }` |

Common application error codes: `unauthorized`, `forbidden`, `not_found`, `conflict`, `slot_unavailable`, `validation_error`, `service_unavailable`, and `internal_error`. FastAPI validation failures can use the default Pydantic/FastAPI validation response.

---

## Endpoint index

### Health and authentication

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | No | Check API process health |
| `GET` | `/health/db` | No | Check database connectivity |
| `POST` | `/v1/auth/refresh` | No | Exchange a refresh token for a new session |
| `GET` | `/v1/auth/me` | Yes | Return the current user profile |
| `POST` | `/v1/auth/owner-access` | Yes | Claim or confirm owner-app access after sign-in |

**Refresh a session**

```http
POST /v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "supabase-refresh-token"
}
```

Returns `access_token`, `refresh_token`, `token_type`, and `expires_in`.

### Customer profile

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/v1/customer/profile` | Customer | Get the current profile |
| `PATCH` | `/v1/customer/profile` | Customer | Update profile fields |
| `POST` | `/v1/customer/profile/avatar` | Customer / Owner | Upload and persist a validated avatar image |
| `POST` | `/v1/reports` | Customer / Owner | Submit a report about a salon |

```json
{
  "full_name": "Thanseef",
  "phone": "+919876543210",
  "avatar_url": "https://example.com/avatar.jpg"
}
```

### Public salon discovery

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/v1/salons` | No | Search customer-visible salons |
| `GET` | `/v1/salons/nearby` | No | Find salons near coordinates |
| `GET` | `/v1/salons/{salon_id}` | No | Get salon details, images, and services |
| `GET` | `/v1/salons/{salon_id}/services` | No | List active salon services |
| `GET` | `/v1/salons/{salon_id}/staff` | No | List publicly visible staff |

**Salon list parameters**

| Endpoint | Supported query parameters |
| --- | --- |
| `/v1/salons` | `search`, `city`, `lat`, `lng`, `limit`, `offset` |
| `/v1/salons/nearby` | `lat`, `lng`, `latitude`, `longitude`, `search`, `city`, `limit`, `offset` |

A salon summary includes its identity, description, category, address, coordinates, timezone, approval mode, main image, starting price, and optional `distance_km`.

### Owner salon management

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/v1/salons/me` | Owner | Get the owner’s salon |
| `PATCH` | `/v1/salons/me` | Owner | Update salon profile details |
| `POST` | `/v1/salons/me/complete-profile` | Owner | Mark the profile complete |
| `PATCH` | `/v1/salons/me/settings` | Owner | Update approval mode and working hours |

Use `working_hours` as a JSON object keyed by day:

```json
{
  "name": "Fresh Cut Salon",
  "timezone": "Asia/Kolkata",
  "working_hours": {
    "mon": { "open": "09:00", "close": "18:00" }
  },
  "approval_mode": "manual"
}
```

### Owner images and holidays

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/v1/salons/me/images` | Owner | List salon images |
| `POST` | `/v1/salons/me/images/upload-url` | Owner | Get a presigned Cloudflare R2 upload URL |
| `POST` | `/v1/salons/me/images` | Owner | Add a salon image |
| `PATCH` | `/v1/salons/me/images/{image_id}` | Owner | Update image metadata |
| `DELETE` | `/v1/salons/me/images/{image_id}` | Owner | Soft-delete a salon image |
| `GET` | `/v1/salons/me/qr` | Owner | Return the public QR image URL or SVG |
| `GET` | `/v1/salons/me/holidays` | Owner | List holidays |
| `POST` | `/v1/salons/me/holidays` | Owner | Add a holiday |
| `DELETE` | `/v1/salons/me/holidays/{holiday_id}` | Owner | Reserved; currently rejects deletion |

**Create an image**

```json
{
  "url": "https://example.com/salon.jpg",
  "caption": "Front view",
  "is_main": true,
  "sort_order": 0
}
```

**Create a holiday**

```json
{
  "holiday_date": "2026-08-15",
  "title": "Independence Day",
  "is_recurring": true
}
```

### Owner services and staff

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/v1/salons/me/services` | Owner | List salon services |
| `POST` | `/v1/salons/me/services` | Owner | Create a service |
| `PATCH` | `/v1/salons/me/services/{service_id}` | Owner | Update a service |
| `DELETE` | `/v1/salons/me/services/{service_id}` | Owner | Delete a service |
| `GET` | `/v1/salons/me/staff` | Owner | List staff |
| `POST` | `/v1/salons/me/staff` | Owner | Create a staff member |
| `PATCH` | `/v1/salons/me/staff/{staff_id}` | Owner | Update staff details |
| `DELETE` | `/v1/salons/me/staff/{staff_id}` | Owner | Delete staff |
| `POST` | `/v1/salons/me/staff/{staff_id}/photo-upload-url` | Owner | Get a signed staff-photo upload URL |
| `POST` | `/v1/salons/me/staff/{staff_id}/services` | Owner | Assign a service to staff |
| `GET` | `/v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages` | Owner | List languages for a staff service |
| `PUT` | `/v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages` | Owner | Replace languages for a staff service |
| `GET` | `/v1/salons/me/blocks` | Owner | List blocked schedule slots |
| `POST` | `/v1/salons/me/blocks` | Owner | Create a blocked slot |
| `DELETE` | `/v1/salons/me/blocks/{block_id}` | Owner | Remove a blocked slot |

**Create a service**

```json
{
  "subcategory_id": "44444444-4444-4444-8444-444444444444",
  "name": "Haircut",
  "description": "Basic haircut",
  "duration_minutes": 30,
  "price": "250.00"
}
```

**Create staff**

```json
{
  "profile_id": null,
  "name": "Ameen",
  "photo_url": "https://example.com/staff.jpg",
  "specialization": "Fade specialist",
  "working_hours": {
    "mon": { "open": "09:00", "close": "18:00" }
  }
}
```

**Assign a service to staff**

```json
{
  "service_id": "33333333-3333-4333-8333-333333333333",
  "duration_minutes": 30,
  "price_override": "275.00",
  "specialization": "Fade specialist"
}
```

**Set staff-service languages**

```json
{
  "language_codes": ["en", "ml"]
}
```

**Block a staff member’s time**

```json
{
  "staff_id": "77777777-7777-4777-8777-777777777777",
  "start_datetime": "2026-08-10T12:00:00Z",
  "end_datetime": "2026-08-10T13:00:00Z",
  "block_type": "lunch",
  "reason": "Lunch break",
  "is_full_day": false,
  "is_recurring": false,
  "recurrence_rule": null,
  "recurrence_end": null
}
```

### Availability and bookings

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/v1/availability` | No | Return bookable slots for a staff member and services |
| `POST` | `/v1/bookings` | Customer | Create a booking |
| `GET` | `/v1/bookings` | Yes | List bookings visible to the caller |
| `GET` | `/v1/bookings/{booking_id}` | Yes | Get a booking |
| `POST` | `/v1/bookings/{booking_id}/approve` | Owner / Staff | Approve a booking |
| `POST` | `/v1/bookings/{booking_id}/complete` | Owner / Staff | Mark a booking complete |
| `POST` | `/v1/bookings/{booking_id}/reject` | Owner / Staff | Reject a booking |
| `POST` | `/v1/bookings/{booking_id}/cancel` | Authorized user | Cancel a booking |
| `POST` | `/v1/bookings/{booking_id}/payment` | Owner / Staff | Record payment |

**Get availability**

```http
GET /v1/availability?staff_id=77777777-7777-4777-8777-777777777777&date=2026-08-10&service_ids=33333333-3333-4333-8333-333333333333
```

The API returns slots with `slot_start`, `slot_end`, `id`, `time`, and `barberName`. Do not calculate availability in the client.

**Create a booking**

```json
{
  "salon_id": "11111111-1111-4111-8111-111111111111",
  "staff_id": "77777777-7777-4777-8777-777777777777",
  "service_ids": ["33333333-3333-4333-8333-333333333333"],
  "start_datetime": "2026-08-10T09:00:00Z",
  "customer_name": "Thanseef",
  "customer_phone": "+919876543210",
  "source": "app",
  "notes": "Please keep the side short"
}
```

**Reject a booking**

```json
{ "rejection_reason": "Staff unavailable" }
```

**Cancel a booking**

```json
{
  "reason_code": "schedule_conflict",
  "reason_text": "Need to reschedule"
}
```

**Record payment**

```json
{ "payment_method": "online" }
```

Payment recording is for salon owner/staff workflows. The customer app should not call it after demo checkout; bookings remain unpaid until the salon records `cash` or `online` payment.

### Notifications and devices

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/v1/notifications` | Yes | List the caller’s notifications |
| `POST` | `/v1/notifications/{notification_id}/read` | Yes | Mark one notification as read |
| `POST` | `/v1/devices` | Yes | Register or refresh a device token |
| `DELETE` | `/v1/devices/{token}` | Yes | Deactivate a device token |

```json
{
  "token": "fcm-device-token",
  "platform": "ios",
  "device_name": "Thanseef iPhone"
}
```

### Walk-in QR booking

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/v1/walkin/{qr_token}` | No | Resolve a salon QR token |
| `GET` | `/v1/walkin/{qr_token}/qr` | No | Return the QR image as PNG or SVG |
| `POST` | `/v1/walkin/{qr_token}/verify-phone` | No | Send or verify a phone OTP |
| `POST` | `/v1/walkin/{qr_token}/bookings` | Yes | Create a booking from a verified QR flow |

**Send OTP**

```json
{ "phone": "+919876543210" }
```

**Verify OTP**

```json
{
  "phone": "+919876543210",
  "otp": "123456"
}
```

A successful verification returns `verified`, `access_token`, and `refresh_token`. Use the returned access token to create the QR walk-in booking, with `source` set to `qr_walkin`.

### Super-admin operations

All routes in this section require a `super_admin` Supabase access token.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/v1/admin/salons` | Provision a salon owner and salon |
| `GET` | `/v1/admin/salons` | List salons; supports `search`, `limit`, `offset` |
| `PATCH` | `/v1/admin/salons/{salon_id}` | Update a salon |
| `POST` | `/v1/admin/salons/{salon_id}/deactivate` | Deactivate a salon |
| `GET` | `/v1/admin/catalog/categories` | List categories |
| `POST` | `/v1/admin/catalog/categories` | Create a category |
| `PATCH` | `/v1/admin/catalog/categories/{category_id}` | Update a category |
| `POST` | `/v1/admin/catalog/categories/{category_id}/deactivate` | Deactivate a category |
| `GET` | `/v1/admin/catalog/categories/{category_id}/subcategories` | List category subcategories |
| `POST` | `/v1/admin/catalog/subcategories` | Create a subcategory |
| `PATCH` | `/v1/admin/catalog/subcategories/{subcategory_id}` | Update a subcategory |
| `POST` | `/v1/admin/catalog/subcategories/{subcategory_id}/deactivate` | Deactivate a subcategory |
| `GET` | `/v1/admin/catalog/languages` | List supported languages |

**Provision an owner and salon**

```json
{
  "email": "owner@example.com",
  "password": "StrongPass123",
  "full_name": "Salon Owner",
  "salon_name": "Fresh Cut Salon",
  "timezone": "Asia/Kolkata"
}
```

**Create a category**

```json
{
  "name": "Hair",
  "slug": "hair",
  "image_url": "https://example.com/hair.jpg",
  "description": "Hair services",
  "sort_order": 1
}
```

**Create a subcategory**

```json
{
  "category_id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
  "name": "Haircut",
  "slug": "haircut",
  "image_url": "https://example.com/haircut.jpg",
  "description": "Haircut services",
  "sort_order": 1
}
```

---

## Core integration flows

### Customer booking flow

1. Authenticate with Supabase and attach the access token to protected API calls.
2. Discover a salon with `GET /v1/salons` or `GET /v1/salons/nearby`.
3. Fetch salon details, services, and staff.
4. Request available slots through `GET /v1/availability`.
5. Create the booking through `POST /v1/bookings`.
6. Use `GET /v1/bookings` and `GET /v1/notifications` to render booking state and updates.

### QR walk-in flow

1. Resolve the scanned QR token using `GET /v1/walkin/{qr_token}`.
2. Send and verify the customer phone OTP.
3. Persist the returned Supabase tokens.
4. Query availability and create the booking through `/v1/walkin/{qr_token}/bookings` using `source: "qr_walkin"`.

### Owner setup flow

1. Call `POST /v1/auth/owner-access`, then retrieve the salon with `GET /v1/salons/me`.
2. Update salon details and working hours.
3. Add images, services, and staff.
4. Assign services and languages to staff.
5. Add holidays or blocked time before accepting bookings.
6. Use booking status and payment endpoints from the owner/staff app.

---

## Important implementation notes

- Send the Supabase access token only in the `Authorization` header unless an endpoint explicitly asks for a token in its body.
- Do not write bookings directly to Supabase; use the booking endpoints so availability, authorization, and status rules are enforced.
- Treat all response money values as strings to avoid floating-point precision issues.
- The holiday delete route exists but intentionally rejects requests until its table supports soft deletion. Do not expose this action in the frontend yet. Image deletion is fully supported.
- Standard booking responses include status, payment state, salon/staff display information, ordered services, timestamps, and `can_cancel`.
