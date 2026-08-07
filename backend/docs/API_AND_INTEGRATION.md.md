# API Keys, API Reference, And Frontend Integration Guide

This document is the frontend integration reference for the shared FastAPI backend.
It covers environment variables, authentication, every mounted API route, request
formats, response formats, and common error handling.

The backend owns all application data access and business rules. Frontend apps may use
Supabase directly for authentication token management only; all salon, catalog, booking,
notification, and device data must go through this API.

---

## 1. Base URLs

Local development:

```txt
http://localhost:8000
```

Real mobile device on the same Wi-Fi:

```txt
http://YOUR_MAC_IP:8000
```

Production:

```txt
https://api.yourdomain.com
```

All versioned API routes are under:

```txt
/v1
```

OpenAPI docs are available locally at:

```txt
http://localhost:8000/docs
```

---

## 2. Authentication

Authenticated routes require a Supabase access token:

```http
Authorization: Bearer <supabase_access_token>
Content-Type: application/json
```

Roles are resolved by the backend from the `profiles` table. Clients must not rely on
role claims inside JWT bodies for authorization decisions.

Supported roles:

```txt
super_admin
owner
staff
customer
```

---

## 3. Error Format

Application errors use this JSON shape:

```json
{
  "error": {
    "code": "not_found",
    "message": "Resource not found"
  }
}
```

Common codes:

```txt
unauthorized
forbidden
not_found
conflict
slot_unavailable
validation_error
internal_error
```

FastAPI/Pydantic request validation errors may use FastAPI's default validation format.

---

## 4. Environment Variables

Every backend variable lives in `backend/.env` locally or in the hosting platform's
secret manager in production.

| Variable | Required | Purpose |
|---|---:|---|
| `APP_NAME` | No | Display name shown in FastAPI docs |
| `ENVIRONMENT` | Yes | `local`, `test`, or `production` |
| `DATABASE_URL` | Yes | Async SQLAlchemy Postgres URL |
| `DB_POOL_SIZE` | No | Persistent DB connection count, default `5` |
| `DB_MAX_OVERFLOW` | No | Burst connections above pool size, default `5` |
| `DB_POOL_TIMEOUT_SECONDS` | No | Seconds to wait for a free DB connection, default `10` |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | Public anon key, safe for clients |
| `SUPABASE_JWKS_URL` | Yes | JWT signing key URL |
| `SUPABASE_JWT_AUDIENCE` | Yes | Usually `authenticated` |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes in production | Server-only admin key, never expose to clients |
| `FIREBASE_CREDENTIALS_JSON` | No | Firebase service account JSON for FCM |
| `BACKEND_CORS_ORIGINS` | Yes | JSON array of allowed frontend origins |

Example backend `.env`:

```bash
APP_NAME="Salon Platform API"
ENVIRONMENT=local

DATABASE_URL=postgresql+asyncpg://postgres.[PROJECT_REF]:[DB_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
DB_POOL_TIMEOUT_SECONDS=10

SUPABASE_URL=https://[PROJECT_REF].supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_JWKS_URL=https://[PROJECT_REF].supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_SERVICE_ROLE_KEY=eyJ...

FIREBASE_CREDENTIALS_JSON='{"type":"service_account","project_id":"..."}'
BACKEND_CORS_ORIGINS=["http://localhost:19006","http://localhost:3000","http://localhost:3001","http://localhost:8081","http://127.0.0.1:8081"]
```

Frontend environment examples:

```bash
# Expo customer / owner apps
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_SUPABASE_URL=https://[PROJECT_REF].supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=eyJ...

# Next.js walk-in web app
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## 5. Shared Response Models

### TokenResponse

```json
{
  "access_token": "jwt",
  "refresh_token": "refresh-token-or-null",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### ProfileResponse

```json
{
  "id": "profile-uuid",
  "role": "customer",
  "full_name": "Customer Name",
  "email": "customer@example.com",
  "phone": "+919876543210",
  "phone_verified": true,
  "avatar_url": "https://...",
  "is_active": true
}
```

### SalonSummaryResponse

```json
{
  "id": "salon-uuid",
  "name": "Salon Name",
  "description": "Short description",
  "category": "Unisex",
  "address": "Street address",
  "city": "Kochi",
  "lat": 9.9312,
  "lng": 76.2673,
  "timezone": "Asia/Kolkata",
  "approval_mode": "auto",
  "profile_completed": true,
  "is_active": true,
  "image_url": "https://...",
  "starting_price": "250.00",
  "distance_km": 2.4
}
```

### SalonDetailResponse

```json
{
  "id": "salon-uuid",
  "name": "Salon Name",
  "description": "Short description",
  "category": "Unisex",
  "address": "Street address",
  "city": "Kochi",
  "lat": 9.9312,
  "lng": 76.2673,
  "timezone": "Asia/Kolkata",
  "working_hours": {"monday": {"open": "09:00", "close": "18:00"}},
  "approval_mode": "auto",
  "slot_interval_minutes": 30,
  "profile_completed": true,
  "is_active": true,
  "images": [],
  "services": []
}
```

### OwnerSalonResponse

```json
{
  "id": "salon-uuid",
  "owner_id": "owner-profile-uuid",
  "name": "Salon Name",
  "description": "Short description",
  "category": "Unisex",
  "address": "Street address",
  "city": "Kochi",
  "lat": 9.9312,
  "lng": 76.2673,
  "timezone": "Asia/Kolkata",
  "working_hours": {},
  "approval_mode": "manual",
  "slot_interval_minutes": 30,
  "qr_token": "public-qr-token",
  "profile_completed": true,
  "is_active": true,
  "created_at": "2026-08-07T09:00:00Z",
  "updated_at": "2026-08-07T09:00:00Z"
}
```

### ServiceResponse

```json
{
  "id": "service-uuid",
  "salon_id": "salon-uuid",
  "subcategory_id": "subcategory-uuid",
  "name": "Haircut",
  "description": "Basic haircut",
  "duration_minutes": 30,
  "price": "250.00",
  "is_active": true,
  "category_name": "Hair",
  "subcategory_name": "Haircut",
  "created_at": "2026-08-07T09:00:00Z",
  "updated_at": "2026-08-07T09:00:00Z"
}
```

### StaffResponse

```json
{
  "id": "staff-uuid",
  "salon_id": "salon-uuid",
  "profile_id": "profile-uuid-or-null",
  "name": "Staff Name",
  "photo_url": "https://...",
  "specialization": "Hair stylist",
  "working_hours": {},
  "is_active": true,
  "created_at": "2026-08-07T09:00:00Z",
  "updated_at": "2026-08-07T09:00:00Z"
}
```

### PublicStaffResponse

```json
{
  "id": "staff-uuid",
  "name": "Staff Name",
  "photo_url": "https://...",
  "specialization": "Hair stylist"
}
```

### BookingResponse

```json
{
  "id": "booking-uuid",
  "salon_id": "salon-uuid",
  "staff_id": "staff-uuid",
  "customer_id": "customer-profile-uuid",
  "customer_name": "Customer Name",
  "customer_phone": "+919876543210",
  "phone_verified": true,
  "source": "app",
  "status": "confirmed",
  "start_datetime": "2026-08-07T10:00:00Z",
  "end_datetime": "2026-08-07T10:30:00Z",
  "total_duration_minutes": 30,
  "total_price": "250.00",
  "payment_status": "unpaid",
  "payment_method": null,
  "rejection_reason": null,
  "notes": "Optional note",
  "services": [
    {
      "service_id": "service-uuid",
      "service_name": "Haircut",
      "duration_minutes": 30,
      "price": "250.00"
    }
  ],
  "salon_name": "Salon Name",
  "salon_address": "Street address",
  "salon_image": "https://...",
  "staff_name": "Staff Name",
  "staff_photo_url": "https://...",
  "created_at": "2026-08-07T09:00:00Z",
  "updated_at": "2026-08-07T09:00:00Z",
  "can_cancel": true
}
```

Booking sources:

```txt
app
manual_walkin
qr_walkin
```

Payment methods:

```txt
cash
upi
card
wallet
```

---

## 6. Health APIs

### GET /health

Auth: public

Response `200`:

```json
{
  "status": "ok"
}
```

### GET /health/db

Auth: public

Response `200`:

```json
{
  "status": "ok",
  "database": "reachable"
}
```

---

## 7. Auth APIs

### POST /v1/auth/login

Auth: public

Request:

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

Response `200`: `TokenResponse`

### POST /v1/auth/refresh

Auth: public

Request:

```json
{
  "refresh_token": "refresh-token"
}
```

Response `200`: `TokenResponse`

### GET /v1/auth/me

Auth: any active authenticated user

Response `200`: `ProfileResponse`

---

## 8. Customer Profile APIs

### GET /v1/customer/profile

Auth: any active authenticated user

Response `200`: `ProfileResponse`

### PATCH /v1/customer/profile

Auth: any active authenticated user

Request, all fields optional:

```json
{
  "full_name": "Customer Name",
  "phone": "+919876543210",
  "avatar_url": "https://..."
}
```

Response `200`: `ProfileResponse`

---

## 9. Public Salon APIs

### GET /v1/salons

Auth: public

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `search` | string | No | Search term |
| `city` | string | No | City filter |
| `lat` | number | No | Latitude for distance |
| `lng` | number | No | Longitude for distance |
| `limit` | integer | No | Default `50`, min `1`, max `100` |
| `offset` | integer | No | Default `0`, min `0` |

Response `200`: array of `SalonSummaryResponse`

### GET /v1/salons/nearby

Auth: public

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `lat` or `latitude` | number | No | Latitude |
| `lng` or `longitude` | number | No | Longitude |
| `search` | string | No | Search term |
| `city` | string | No | City filter |
| `limit` | integer | No | Default `50`, min `1`, max `100` |
| `offset` | integer | No | Default `0`, min `0` |

Response `200`: array of `SalonSummaryResponse`

### GET /v1/salons/{salon_id}

Auth: public

Response `200`: `SalonDetailResponse`

### GET /v1/salons/{salon_id}/services

Auth: public

Response `200`: array of `ServiceResponse`

### GET /v1/salons/{salon_id}/staff

Auth: public

Response `200`: array of `PublicStaffResponse`

---

## 10. Super Admin APIs

All routes in this section require an authenticated `super_admin`.

### POST /v1/admin/salons

Creates a Supabase Auth owner user and a salon.

Request:

```json
{
  "email": "owner@example.com",
  "password": "minimum-8-chars",
  "full_name": "Owner Name",
  "salon_name": "Salon Name",
  "timezone": "Asia/Kolkata"
}
```

Response `201`:

```json
{
  "id": "salon-uuid",
  "owner_id": "owner-profile-uuid",
  "owner_email": "owner@example.com",
  "owner_name": "Owner Name",
  "name": "Salon Name",
  "description": null,
  "category": null,
  "address": null,
  "city": null,
  "timezone": "Asia/Kolkata",
  "approval_mode": "manual",
  "profile_completed": false,
  "is_active": true,
  "created_at": "2026-08-07T09:00:00Z",
  "updated_at": "2026-08-07T09:00:00Z"
}
```

### GET /v1/admin/salons

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `search` | string | No | Search by salon or owner details |
| `limit` | integer | No | Default `50`, min `1`, max `200` |
| `offset` | integer | No | Default `0`, min `0` |

Response `200`: array of `AdminSalonResponse`

### PATCH /v1/admin/salons/{salon_id}

Request, all fields optional:

```json
{
  "name": "Updated Salon Name",
  "timezone": "Asia/Kolkata"
}
```

Response `200`: `AdminSalonResponse`

### POST /v1/admin/salons/{salon_id}/deactivate

Request: no body

Response `200`:

```json
{
  "id": "salon-uuid",
  "owner_id": "owner-profile-uuid"
}
```

### GET /v1/admin/catalog/categories

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `include_inactive` | boolean | No | Default `false` |

Response `200`: array of `CategoryResponse`

### POST /v1/admin/catalog/categories

Request:

```json
{
  "name": "Hair",
  "slug": "hair",
  "image_url": "https://...",
  "description": "Hair services",
  "sort_order": 0
}
```

Response `201`: `CategoryResponse`

### PATCH /v1/admin/catalog/categories/{category_id}

Request, all fields optional:

```json
{
  "name": "Hair",
  "slug": "hair",
  "image_url": "https://...",
  "description": "Hair services",
  "sort_order": 1,
  "is_active": true
}
```

Response `200`: `CategoryResponse`

### POST /v1/admin/catalog/categories/{category_id}/deactivate

Request: no body

Response `200`: `CategoryResponse`

### GET /v1/admin/catalog/categories/{category_id}/subcategories

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `include_inactive` | boolean | No | Default `false` |

Response `200`: array of `SubcategoryResponse`

### POST /v1/admin/catalog/subcategories

Request:

```json
{
  "category_id": "category-uuid",
  "name": "Haircut",
  "slug": "haircut",
  "image_url": "https://...",
  "description": "Haircut services",
  "sort_order": 0
}
```

Response `201`: `SubcategoryResponse`

### PATCH /v1/admin/catalog/subcategories/{subcategory_id}

Request, all fields optional:

```json
{
  "name": "Haircut",
  "slug": "haircut",
  "image_url": "https://...",
  "description": "Haircut services",
  "sort_order": 1,
  "is_active": true
}
```

Response `200`: `SubcategoryResponse`

### POST /v1/admin/catalog/subcategories/{subcategory_id}/deactivate

Request: no body

Response `200`: `SubcategoryResponse`

### GET /v1/admin/catalog/languages

Auth: any active authenticated user

Response `200`:

```json
[
  {
    "code": "en",
    "name": "English"
  }
]
```

### CategoryResponse

```json
{
  "id": "category-uuid",
  "name": "Hair",
  "slug": "hair",
  "image_url": "https://...",
  "description": "Hair services",
  "sort_order": 0,
  "is_active": true,
  "created_at": "2026-08-07T09:00:00Z",
  "updated_at": "2026-08-07T09:00:00Z"
}
```

### SubcategoryResponse

```json
{
  "id": "subcategory-uuid",
  "category_id": "category-uuid",
  "name": "Haircut",
  "slug": "haircut",
  "image_url": "https://...",
  "description": "Haircut services",
  "sort_order": 0,
  "is_active": true,
  "created_at": "2026-08-07T09:00:00Z",
  "updated_at": "2026-08-07T09:00:00Z"
}
```

---

## 11. Owner Salon APIs

All routes in this section require an authenticated salon owner or authorized salon staff,
as enforced by the application use cases.

### GET /v1/salons/me

Response `200`: `OwnerSalonResponse`

### PATCH /v1/salons/me

Request, all fields optional:

```json
{
  "name": "Salon Name",
  "description": "Short description",
  "category": "Unisex",
  "address": "Street address",
  "city": "Kochi",
  "lat": 9.9312,
  "lng": 76.2673,
  "timezone": "Asia/Kolkata",
  "working_hours": {"monday": {"open": "09:00", "close": "18:00"}},
  "approval_mode": "auto",
  "slot_interval_minutes": 30
}
```

Response `200`: `OwnerSalonResponse`

### POST /v1/salons/me/complete-profile

Request: no body

Response `200`: `OwnerSalonResponse`

### PATCH /v1/salons/me/settings

Request, all fields optional:

```json
{
  "approval_mode": "manual",
  "slot_interval_minutes": 30,
  "working_hours": {"monday": {"open": "09:00", "close": "18:00"}}
}
```

Response `200`: `OwnerSalonResponse`

---

## 12. Owner Image APIs

### GET /v1/salons/me/images

Auth: owner/staff

Response `200`: array of `SalonImageResponse`

### POST /v1/salons/me/images

Auth: owner/staff

Request:

```json
{
  "url": "https://...",
  "caption": "Front view",
  "is_main": true,
  "sort_order": 0
}
```

Response `201`: `SalonImageResponse`

### PATCH /v1/salons/me/images/{image_id}

Auth: owner/staff

Request, all fields optional:

```json
{
  "url": "https://...",
  "caption": "Updated caption",
  "is_main": false,
  "sort_order": 1
}
```

Response `200`: `SalonImageResponse`

### DELETE /v1/salons/me/images/{image_id}

Auth: owner/staff

Response: route is mounted as `204`, but current use case intentionally rejects deletion
because `salon_images` has no `is_active` column for soft delete.

### SalonImageResponse

```json
{
  "id": "image-uuid",
  "salon_id": "salon-uuid",
  "url": "https://...",
  "caption": "Front view",
  "is_main": true,
  "sort_order": 0,
  "created_at": "2026-08-07T09:00:00Z",
  "updated_at": "2026-08-07T09:00:00Z"
}
```

---

## 13. Owner Holiday APIs

### GET /v1/salons/me/holidays

Auth: owner/staff

Response `200`: array of `HolidayResponse`

### POST /v1/salons/me/holidays

Auth: owner/staff

Request:

```json
{
  "holiday_date": "2026-08-15",
  "title": "Independence Day",
  "is_recurring": false
}
```

Response `201`: `HolidayResponse`

### DELETE /v1/salons/me/holidays/{holiday_id}

Auth: owner/staff

Response: route is mounted as `204`, but current use case intentionally rejects deletion
because `salon_holidays` has no `is_active` column for soft delete.

### HolidayResponse

```json
{
  "id": "holiday-uuid",
  "salon_id": "salon-uuid",
  "holiday_date": "2026-08-15",
  "title": "Independence Day",
  "is_recurring": false,
  "created_at": "2026-08-07T09:00:00Z",
  "updated_at": "2026-08-07T09:00:00Z"
}
```

---

## 14. Owner Service APIs

### GET /v1/salons/me/services

Auth: owner/staff

Response `200`: array of `ServiceResponse`

### POST /v1/salons/me/services

Auth: owner/staff

Request:

```json
{
  "subcategory_id": "subcategory-uuid",
  "name": "Haircut",
  "description": "Basic haircut",
  "duration_minutes": 30,
  "price": "250.00"
}
```

Response `201`: `ServiceResponse`

### PATCH /v1/salons/me/services/{service_id}

Auth: owner/staff

Request, all fields optional:

```json
{
  "subcategory_id": "subcategory-uuid",
  "name": "Haircut",
  "description": "Updated description",
  "duration_minutes": 45,
  "price": "300.00",
  "is_active": true
}
```

Response `200`: `ServiceResponse`

### DELETE /v1/salons/me/services/{service_id}

Auth: owner/staff

Soft-deactivates by setting `is_active = false`.

Response `200`: `ServiceResponse`

---

## 15. Owner Staff APIs

### GET /v1/salons/me/staff

Auth: owner/staff

Response `200`: array of `StaffResponse`

### POST /v1/salons/me/staff

Auth: owner/staff

Request:

```json
{
  "profile_id": null,
  "name": "Staff Name",
  "photo_url": "https://...",
  "specialization": "Hair stylist",
  "working_hours": {"monday": {"open": "09:00", "close": "18:00"}}
}
```

Response `201`: `StaffResponse`

### PATCH /v1/salons/me/staff/{staff_id}

Auth: owner/staff

Request, all fields optional:

```json
{
  "profile_id": null,
  "name": "Updated Staff Name",
  "photo_url": "https://...",
  "specialization": "Senior stylist",
  "working_hours": {},
  "is_active": true
}
```

Response `200`: `StaffResponse`

### DELETE /v1/salons/me/staff/{staff_id}

Auth: owner/staff

Soft-deactivates by setting `is_active = false`.

Response `200`: `StaffResponse`

### POST /v1/salons/me/staff/{staff_id}/services

Auth: owner/staff

Assigns a service to a staff member with optional overrides.

Request:

```json
{
  "service_id": "service-uuid",
  "duration_minutes": 30,
  "price_override": "275.00",
  "specialization": "Fade specialist"
}
```

Response `200`:

```json
{
  "id": "staff-service-uuid",
  "staff_id": "staff-uuid",
  "service_id": "service-uuid",
  "duration_minutes": 30,
  "price_override": "275.00",
  "specialization": "Fade specialist",
  "is_active": true,
  "created_at": "2026-08-07T09:00:00Z",
  "updated_at": "2026-08-07T09:00:00Z"
}
```

### GET /v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages

Auth: owner/staff

Response `200`:

```json
[
  {
    "code": "en",
    "name": "English"
  }
]
```

### PUT /v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages

Auth: owner/staff

Idempotent. Replaces the full language list. Send an empty list to remove all languages.

Request:

```json
{
  "language_codes": ["en", "ml"]
}
```

Response `200`:

```json
[
  {
    "code": "en",
    "name": "English"
  },
  {
    "code": "ml",
    "name": "Malayalam"
  }
]
```

---

## 16. Owner Blocked Slot APIs

### GET /v1/salons/me/blocks

Auth: owner/staff

Response `200`: array of `BlockedSlotResponse`

### POST /v1/salons/me/blocks

Auth: owner/staff

Set `staff_id` for a staff-specific block. Leave `staff_id` as `null` for a salon-wide
block.

Request:

```json
{
  "staff_id": "staff-uuid",
  "start_datetime": "2026-08-07T13:00:00Z",
  "end_datetime": "2026-08-07T14:00:00Z",
  "block_type": "lunch",
  "reason": "Lunch break",
  "is_full_day": false,
  "is_recurring": false,
  "recurrence_rule": null,
  "recurrence_end": null
}
```

`block_type` values:

```txt
leave
break
lunch
training
holiday
other
```

Response `201`: `BlockedSlotResponse`

### DELETE /v1/salons/me/blocks/{block_id}

Auth: owner/staff

Hard-deletes a blocked slot because `blocked_slots` has no `is_active` column.

Response `204`: no body

### BlockedSlotResponse

```json
{
  "id": "block-uuid",
  "staff_id": "staff-uuid",
  "salon_id": "salon-uuid",
  "start_datetime": "2026-08-07T13:00:00Z",
  "end_datetime": "2026-08-07T14:00:00Z",
  "block_type": "lunch",
  "reason": "Lunch break",
  "is_full_day": false,
  "is_recurring": false,
  "recurrence_rule": null,
  "recurrence_end": null,
  "created_at": "2026-08-07T09:00:00Z",
  "updated_at": "2026-08-07T09:00:00Z"
}
```

---

## 17. Availability And Booking APIs

### GET /v1/availability

Auth: public

Availability is always fetched from the Postgres `get_available_slots` function. The
backend must not compute slots in Python.

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `staff_id` | string | Yes | Staff UUID |
| `date` | date | Yes | Booking date, `YYYY-MM-DD` |
| `service_ids` | string[] | Yes | Repeat query param for each service |

Example:

```txt
/v1/availability?staff_id=staff-uuid&date=2026-08-07&service_ids=service-1&service_ids=service-2
```

Response `200`:

```json
[
  {
    "slot_start": "2026-08-07T10:00:00Z",
    "slot_end": "2026-08-07T10:30:00Z",
    "id": "10:00 AM",
    "time": "10:00 AM",
    "barberName": "Staff Name"
  }
]
```

### POST /v1/bookings

Auth: any active authenticated user

Booking creation always calls the Postgres `create_booking` function. Slot conflicts
return `409` with `error.code = "slot_unavailable"`.

Request:

```json
{
  "salon_id": "salon-uuid",
  "staff_id": "staff-uuid",
  "service_ids": ["service-uuid"],
  "start_datetime": "2026-08-07T10:00:00Z",
  "customer_name": "Customer Name",
  "customer_phone": "+919876543210",
  "source": "app",
  "notes": "Optional note"
}
```

Response `201`: `BookingResponse`

### GET /v1/bookings

Auth: any active authenticated user

Owners see bookings for their salon. Customers see only their own bookings.

Response `200`: array of `BookingResponse`

### GET /v1/bookings/{booking_id}

Auth: any active authenticated user with access to the booking

Response `200`: `BookingResponse`

### POST /v1/bookings/{booking_id}/approve

Auth: owner/staff

Request: no body

Response `200`: `BookingResponse`

### POST /v1/bookings/{booking_id}/reject

Auth: owner/staff

Request:

```json
{
  "rejection_reason": "Staff unavailable"
}
```

Response `200`: `BookingResponse`

### POST /v1/bookings/{booking_id}/complete

Auth: owner/staff

Request: no body

Response `200`: `BookingResponse`

### POST /v1/bookings/{booking_id}/cancel

Auth: customer owner of booking, owner, or staff

Request body is optional:

```json
{
  "reason_code": "schedule_conflict",
  "reason_text": "Need to reschedule"
}
```

`reason_code` values:

```txt
schedule_conflict
found_better
personal_emergency
booked_by_mistake
service_not_needed
barber_unavailable
other
```

Response `200`: `BookingResponse`

### POST /v1/bookings/{booking_id}/payment

Auth: owner/staff

Request:

```json
{
  "payment_method": "upi"
}
```

Response `200`: `BookingResponse`

---

## 18. Notification And Device APIs

### GET /v1/notifications

Auth: any active authenticated user

Response `200`:

```json
[
  {
    "id": "notification-uuid",
    "user_id": "profile-uuid",
    "booking_id": "booking-uuid",
    "type": "booking_confirmed",
    "title": "Booking confirmed",
    "body": "Your booking was confirmed",
    "read": false,
    "read_at": null,
    "created_at": "2026-08-07T09:00:00Z"
  }
]
```

### POST /v1/notifications/{notification_id}/read

Auth: notification owner

Request: no body

Response `200`: `NotificationResponse`

### POST /v1/devices

Auth: any active authenticated user

Registers or reactivates an FCM device token.

Request:

```json
{
  "token": "fcm-device-token",
  "platform": "ios",
  "device_name": "iPhone 15"
}
```

Response `200`:

```json
{
  "id": "device-token-row-uuid",
  "token": "fcm-device-token",
  "platform": "ios"
}
```

### DELETE /v1/devices/{token}

Auth: owner of the device token

Response `204`: no body

---

## 19. Walk-in QR APIs

### GET /v1/walkin/{qr_token}

Auth: public

Resolves a public QR token into the salon page data.

Response `200`:

```json
{
  "id": "salon-uuid",
  "name": "Salon Name",
  "description": "Short description",
  "city": "Kochi",
  "address": "Street address",
  "image_url": "https://...",
  "timezone": "Asia/Kolkata",
  "approval_mode": "auto",
  "services": [
    {
      "id": "service-uuid",
      "salon_id": "salon-uuid",
      "subcategory_id": "subcategory-uuid",
      "name": "Haircut",
      "description": "Basic haircut",
      "duration_minutes": 30,
      "price": "250.00",
      "is_active": true,
      "category_name": "Hair",
      "subcategory_name": "Haircut"
    }
  ],
  "staff": [
    {
      "id": "staff-uuid",
      "name": "Staff Name",
      "photo_url": "https://...",
      "specialization": "Hair stylist"
    }
  ]
}
```

### POST /v1/walkin/{qr_token}/verify-phone

Auth: public

Send OTP request:

```json
{
  "phone": "+919876543210"
}
```

Send OTP response `200`:

```json
{
  "verified": false,
  "access_token": null,
  "refresh_token": null
}
```

Verify OTP request:

```json
{
  "phone": "+919876543210",
  "otp": "123456"
}
```

Verify OTP response `200`:

```json
{
  "verified": true,
  "access_token": "jwt",
  "refresh_token": "refresh-token"
}
```

### POST /v1/walkin/{qr_token}/bookings

Auth: customer JWT returned by phone verification

Creates a booking with `source = "qr_walkin"` through the same database booking function.

Request:

```json
{
  "salon_id": "salon-uuid",
  "staff_id": "staff-uuid",
  "service_ids": ["service-uuid"],
  "start_datetime": "2026-08-07T10:00:00Z",
  "customer_name": "Customer Name",
  "customer_phone": "+919876543210",
  "source": "qr_walkin",
  "notes": null
}
```

Response `201`: `BookingResponse`

---

## 20. Frontend Fetch Helpers

Expo apps can call the backend with the Supabase access token:

```typescript
const BASE_URL = process.env.EXPO_PUBLIC_API_URL;

export async function apiFetch(path: string, options?: RequestInit) {
  const token = await getSupabaseAccessToken();
  return fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  });
}
```

Walk-in web only needs the API base URL for public QR and OTP calls. It passes the OTP
JWT only when creating the QR booking:

```typescript
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

export const api = {
  get: (path: string) => fetch(`${BASE}${path}`).then((r) => r.json()),
  post: (path: string, body: unknown, token?: string) =>
    fetch(`${BASE}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    }).then((r) => r.json()),
};
```

---

## 21. Security Rules

| Rule | Reason |
|---|---|
| Never expose `SUPABASE_SERVICE_ROLE_KEY` to any client | It bypasses RLS and has admin power |
| Never expose `FIREBASE_CREDENTIALS_JSON` to any client | It can send push notifications |
| Clients may use `SUPABASE_ANON_KEY` for Auth only | Business data goes through FastAPI |
| Add frontend domains to `BACKEND_CORS_ORIGINS` | Browsers need explicit CORS permission |
| Set `ENVIRONMENT=production` in production | Enables startup validation for required secrets |

---

## 22. Local Startup

```bash
cd backend
./.venv/bin/pip install -e ".[dev]"
./.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verification:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```
