# Salon Platform API And Integration Guide

This is the Postman-style markdown reference for the shared FastAPI backend.

The actual mounted API prefix is:

```bash
/v1
```

## Base URLs

Local development:

```bash
http://localhost:8000
```

Real mobile device on the same Wi-Fi:

```bash
http://YOUR_MAC_IP:8000
```

Production:

```bash
https://api.yourdomain.com
```

OpenAPI UI:

```bash
http://localhost:8000/docs
```

## Authentication

Protected routes use the Supabase access token in the HTTP header.

```http
Authorization: Bearer <supabase_access_token>
Content-Type: application/json
```

Do not send `access_token` in the JSON body unless a specific endpoint explicitly
documents it. Google sign-in is started by the frontend through Supabase Auth. This
backend verifies the returned Supabase JWT and resolves the user role from
`profiles.role`.

Supported roles:

```txt
super_admin
owner
staff
customer
```

## Shared Datatypes

| Type | JSON datatype | Example |
| --- | --- | --- |
| UUID | string | `"8efc2d51-9d4c-4f1d-8e2e-0f6f0d624aa1"` |
| Date | string, `YYYY-MM-DD` | `"2026-08-10"` |
| Datetime | string, ISO-8601 | `"2026-08-10T09:00:00Z"` |
| Decimal money | string in responses, number or string in requests | `"250.00"` |
| Enum | string | `"auto"` |
| JSON object | object | `{"mon": {"open": "09:00", "close": "18:00"}}` |

## Error Response

Application errors use this shape:

```json
{
  "error": {
    "code": "not_found",
    "message": "Resource not found"
  }
}
```

Common error codes:

```txt
unauthorized
forbidden
not_found
conflict
slot_unavailable
validation_error
internal_error
```

FastAPI/Pydantic validation errors may use FastAPI's default validation format.

## Frontend Environment Variables

Frontend apps only need the API base URL and Supabase public client values.
Server-only values such as `DATABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and
`FIREBASE_CREDENTIALS_JSON` must stay in the backend environment and must never be
bundled into frontend apps.

```bash
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_SUPABASE_URL=https://[PROJECT_REF].supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=eyJ...
EXPO_PUBLIC_GOOGLE_AUTH_REDIRECT_URL=salonapp://auth/callback

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Response Examples Used Below

These are representative examples of the actual Pydantic response schemas. Real
values depend on the database row returned by Supabase.

### `ProfileResponse`

```json
{
  "id": "8efc2d51-9d4c-4f1d-8e2e-0f6f0d624aa1",
  "role": "customer",
  "full_name": "Thanseef",
  "email": "thanseef@example.com",
  "phone": "+919876543210",
  "phone_verified": true,
  "avatar_url": "https://example.com/avatar.jpg",
  "is_active": true
}
```

### `SalonSummaryResponse`

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "name": "Fresh Cut Salon",
  "description": "Men's grooming and styling",
  "category": "Men",
  "address": "MG Road, Kochi",
  "city": "Kochi",
  "lat": 9.9312,
  "lng": 76.2673,
  "timezone": "Asia/Kolkata",
  "approval_mode": "auto",
  "profile_completed": true,
  "is_active": true,
  "image_url": "https://example.com/salon.jpg",
  "starting_price": "250.00",
  "distance_km": 2.4
}
```

### `SalonDetailResponse`

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "name": "Fresh Cut Salon",
  "description": "Men's grooming and styling",
  "category": "Men",
  "address": "MG Road, Kochi",
  "city": "Kochi",
  "lat": 9.9312,
  "lng": 76.2673,
  "timezone": "Asia/Kolkata",
  "working_hours": {
    "mon": {"open": "09:00", "close": "18:00"},
    "tue": {"open": "09:00", "close": "18:00"}
  },
  "approval_mode": "auto",
  "profile_completed": true,
  "is_active": true,
  "images": [
    {
      "id": "22222222-2222-4222-8222-222222222222",
      "salon_id": "11111111-1111-4111-8111-111111111111",
      "url": "https://example.com/salon.jpg",
      "caption": "Front view",
      "is_main": true,
      "sort_order": 0,
      "created_at": "2026-08-10T09:00:00Z",
      "updated_at": "2026-08-10T09:00:00Z"
    }
  ],
  "services": [
    {
      "id": "33333333-3333-4333-8333-333333333333",
      "salon_id": "11111111-1111-4111-8111-111111111111",
      "subcategory_id": "44444444-4444-4444-8444-444444444444",
      "name": "Haircut",
      "description": "Basic haircut",
      "duration_minutes": 30,
      "price": "250.00",
      "is_active": true,
      "category_name": "Hair",
      "subcategory_name": "Haircut",
      "created_at": "2026-08-10T09:00:00Z",
      "updated_at": "2026-08-10T09:00:00Z"
    }
  ]
}
```

### `OwnerSalonResponse`

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "owner_id": "55555555-5555-4555-8555-555555555555",
  "name": "Fresh Cut Salon",
  "description": "Men's grooming and styling",
  "category": "Men",
  "address": "MG Road, Kochi",
  "city": "Kochi",
  "lat": 9.9312,
  "lng": 76.2673,
  "timezone": "Asia/Kolkata",
  "working_hours": {
    "mon": {"open": "09:00", "close": "18:00"}
  },
  "approval_mode": "manual",
  "qr_token": "fresh-cut-kochi-qr",
  "profile_completed": true,
  "is_active": true,
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

### `BookingResponse`

```json
{
  "id": "66666666-6666-4666-8666-666666666666",
  "salon_id": "11111111-1111-4111-8111-111111111111",
  "staff_id": "77777777-7777-4777-8777-777777777777",
  "customer_id": "8efc2d51-9d4c-4f1d-8e2e-0f6f0d624aa1",
  "customer_name": "Thanseef",
  "customer_phone": "+919876543210",
  "phone_verified": true,
  "source": "app",
  "status": "confirmed",
  "start_datetime": "2026-08-10T09:00:00Z",
  "end_datetime": "2026-08-10T09:30:00Z",
  "total_duration_minutes": 30,
  "total_price": "250.00",
  "payment_status": "unpaid",
  "payment_method": null,
  "rejection_reason": null,
  "notes": "Please keep the side short",
  "services": [
    {
      "service_id": "33333333-3333-4333-8333-333333333333",
      "service_name": "Haircut",
      "duration_minutes": 30,
      "price": "250.00"
    }
  ],
  "salon_name": "Fresh Cut Salon",
  "salon_address": "MG Road, Kochi",
  "salon_image": "https://example.com/salon.jpg",
  "staff_name": "Ameen",
  "staff_photo_url": "https://example.com/staff.jpg",
  "created_at": "2026-08-10T08:30:00Z",
  "updated_at": "2026-08-10T08:30:00Z",
  "can_cancel": true
}
```

## Health APIs

### Check API process health

endpoint :

```bash
GET /health
```

Pydantic schema:

```txt
Response: HealthResponse
```

Input Request:

```json
{
  "headers": {},
  "query_params": {},
  "body": null
}
```

Output Response:

```json
{
  "status": "ok"
}
```

### Check database health

endpoint :

```bash
GET /health/db
```

Pydantic schema:

```txt
Response: DatabaseHealthResponse
```

Input Request:

```json
{
  "headers": {},
  "query_params": {},
  "body": null
}
```

Output Response:

```json
{
  "status": "ok",
  "database": "ok"
}
```

## Auth APIs

### Refresh Supabase session

endpoint :

```bash
POST /v1/auth/refresh
```

Pydantic schema:

```txt
Request: RefreshRequest
Response: TokenResponse
```

Input Request:

```json
{
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "refresh_token": "supabase-refresh-token"
  }
}
```

Output Response:

```json
{
  "access_token": "supabase-access-jwt",
  "refresh_token": "supabase-refresh-token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Get current profile

endpoint :

```bash
GET /v1/auth/me
```

Pydantic schema:

```txt
Response: ProfileResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt"
  },
  "query_params": {},
  "body": null
}
```

Output Response:

```json
{
  "id": "8efc2d51-9d4c-4f1d-8e2e-0f6f0d624aa1",
  "role": "customer",
  "full_name": "Thanseef",
  "email": "thanseef@example.com",
  "phone": "+919876543210",
  "phone_verified": true,
  "avatar_url": "https://example.com/avatar.jpg",
  "is_active": true
}
```

## Customer APIs

### Get customer profile

endpoint :

```bash
GET /v1/customer/profile
```

Pydantic schema:

```txt
Response: ProfileResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt"
  },
  "body": null
}
```

Output Response:

```json
{
  "id": "8efc2d51-9d4c-4f1d-8e2e-0f6f0d624aa1",
  "role": "customer",
  "full_name": "Thanseef",
  "email": "thanseef@example.com",
  "phone": "+919876543210",
  "phone_verified": true,
  "avatar_url": "https://example.com/avatar.jpg",
  "is_active": true
}
```

### Update customer profile

endpoint :

```bash
PATCH /v1/customer/profile
```

Pydantic schema:

```txt
Request: ProfileUpdateRequest
Response: ProfileResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "body": {
    "full_name": "Thanseef",
    "phone": "+919876543210",
    "avatar_url": "https://example.com/avatar.jpg"
  }
}
```

Output Response:

```json
{
  "id": "8efc2d51-9d4c-4f1d-8e2e-0f6f0d624aa1",
  "role": "customer",
  "full_name": "Thanseef",
  "email": "thanseef@example.com",
  "phone": "+919876543210",
  "phone_verified": true,
  "avatar_url": "https://example.com/avatar.jpg",
  "is_active": true
}
```

## Public Salon APIs

### List customer-visible salons

endpoint :

```bash
GET /v1/salons
```

Pydantic schema:

```txt
Response: list[SalonSummaryResponse]
```

Input Request:

```json
{
  "headers": {},
  "query_params": {
    "search": "fresh",
    "city": "Kochi",
    "lat": 9.9312,
    "lng": 76.2673,
    "limit": 20,
    "offset": 0
  },
  "body": null
}
```

Output Response:

```json
[
  {
    "id": "11111111-1111-4111-8111-111111111111",
    "name": "Fresh Cut Salon",
    "description": "Men's grooming and styling",
    "category": "Men",
    "address": "MG Road, Kochi",
    "city": "Kochi",
    "lat": 9.9312,
    "lng": 76.2673,
    "timezone": "Asia/Kolkata",
    "approval_mode": "auto",
    "profile_completed": true,
    "is_active": true,
    "image_url": "https://example.com/salon.jpg",
    "starting_price": "250.00",
    "distance_km": 2.4
  }
]
```

### List nearby salons

endpoint :

```bash
GET /v1/salons/nearby
```

Pydantic schema:

```txt
Response: list[SalonSummaryResponse]
```

Input Request:

```json
{
  "headers": {},
  "query_params": {
    "lat": 9.9312,
    "lng": 76.2673,
    "latitude": 9.9312,
    "longitude": 76.2673,
    "search": "hair",
    "city": "Kochi",
    "limit": 20,
    "offset": 0
  },
  "body": null
}
```

Output Response:

```json
[
  {
    "id": "11111111-1111-4111-8111-111111111111",
    "name": "Fresh Cut Salon",
    "description": "Men's grooming and styling",
    "category": "Men",
    "address": "MG Road, Kochi",
    "city": "Kochi",
    "lat": 9.9312,
    "lng": 76.2673,
    "timezone": "Asia/Kolkata",
    "approval_mode": "auto",
    "profile_completed": true,
    "is_active": true,
    "image_url": "https://example.com/salon.jpg",
    "starting_price": "250.00",
    "distance_km": 2.4
  }
]
```

### Get salon details

endpoint :

```bash
GET /v1/salons/{salon_id}
```

Pydantic schema:

```txt
Response: SalonDetailResponse
```

Input Request:

```json
{
  "headers": {},
  "path_params": {
    "salon_id": "11111111-1111-4111-8111-111111111111"
  },
  "body": null
}
```

Output Response:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "name": "Fresh Cut Salon",
  "description": "Men's grooming and styling",
  "category": "Men",
  "address": "MG Road, Kochi",
  "city": "Kochi",
  "lat": 9.9312,
  "lng": 76.2673,
  "timezone": "Asia/Kolkata",
  "working_hours": {
    "mon": {"open": "09:00", "close": "18:00"}
  },
  "approval_mode": "auto",
  "profile_completed": true,
  "is_active": true,
  "images": [],
  "services": []
}
```

### List salon services

endpoint :

```bash
GET /v1/salons/{salon_id}/services
```

Pydantic schema:

```txt
Response: list[ServiceResponse]
```

Input Request:

```json
{
  "headers": {},
  "path_params": {
    "salon_id": "11111111-1111-4111-8111-111111111111"
  },
  "body": null
}
```

Output Response:

```json
[
  {
    "id": "33333333-3333-4333-8333-333333333333",
    "salon_id": "11111111-1111-4111-8111-111111111111",
    "subcategory_id": "44444444-4444-4444-8444-444444444444",
    "name": "Haircut",
    "description": "Basic haircut",
    "duration_minutes": 30,
    "price": "250.00",
    "is_active": true,
    "category_name": "Hair",
    "subcategory_name": "Haircut",
    "created_at": "2026-08-10T09:00:00Z",
    "updated_at": "2026-08-10T09:00:00Z"
  }
]
```

### List salon staff

endpoint :

```bash
GET /v1/salons/{salon_id}/staff
```

Pydantic schema:

```txt
Response: list[PublicStaffResponse]
```

Input Request:

```json
{
  "headers": {},
  "path_params": {
    "salon_id": "11111111-1111-4111-8111-111111111111"
  },
  "body": null
}
```

Output Response:

```json
[
  {
    "id": "77777777-7777-4777-8777-777777777777",
    "name": "Ameen",
    "photo_url": "https://example.com/staff.jpg",
    "specialization": "Fade specialist"
  }
]
```

## Owner Salon APIs

### Get owner salon

endpoint :

```bash
GET /v1/salons/me
```

Pydantic schema:

```txt
Response: OwnerSalonResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt"
  },
  "body": null
}
```

Output Response:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "owner_id": "55555555-5555-4555-8555-555555555555",
  "name": "Fresh Cut Salon",
  "description": "Men's grooming and styling",
  "category": "Men",
  "address": "MG Road, Kochi",
  "city": "Kochi",
  "lat": 9.9312,
  "lng": 76.2673,
  "timezone": "Asia/Kolkata",
  "working_hours": {"mon": {"open": "09:00", "close": "18:00"}},
  "approval_mode": "manual",
  "qr_token": "fresh-cut-kochi-qr",
  "profile_completed": true,
  "is_active": true,
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

### Update owner salon

endpoint :

```bash
PATCH /v1/salons/me
```

Pydantic schema:

```txt
Request: OwnerSalonUpdateRequest
Response: OwnerSalonResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "body": {
    "name": "Fresh Cut Salon",
    "description": "Men's grooming and styling",
    "category": "Men",
    "address": "MG Road, Kochi",
    "city": "Kochi",
    "lat": 9.9312,
    "lng": 76.2673,
    "timezone": "Asia/Kolkata",
    "working_hours": {"mon": {"open": "09:00", "close": "18:00"}},
    "approval_mode": "manual"
  }
}
```

Output Response:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "owner_id": "55555555-5555-4555-8555-555555555555",
  "name": "Fresh Cut Salon",
  "description": "Men's grooming and styling",
  "category": "Men",
  "address": "MG Road, Kochi",
  "city": "Kochi",
  "lat": 9.9312,
  "lng": 76.2673,
  "timezone": "Asia/Kolkata",
  "working_hours": {"mon": {"open": "09:00", "close": "18:00"}},
  "approval_mode": "manual",
  "qr_token": "fresh-cut-kochi-qr",
  "profile_completed": true,
  "is_active": true,
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

### Complete owner profile

endpoint :

```bash
POST /v1/salons/me/complete-profile
```

Pydantic schema:

```txt
Response: OwnerSalonResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt"
  },
  "body": null
}
```

Output Response:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "owner_id": "55555555-5555-4555-8555-555555555555",
  "name": "Fresh Cut Salon",
  "description": "Men's grooming and styling",
  "category": "Men",
  "address": "MG Road, Kochi",
  "city": "Kochi",
  "lat": 9.9312,
  "lng": 76.2673,
  "timezone": "Asia/Kolkata",
  "working_hours": {"mon": {"open": "09:00", "close": "18:00"}},
  "approval_mode": "manual",
  "qr_token": "fresh-cut-kochi-qr",
  "profile_completed": true,
  "is_active": true,
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

### Update owner salon settings

endpoint :

```bash
PATCH /v1/salons/me/settings
```

Pydantic schema:

```txt
Request: OwnerSalonSettingsRequest
Response: OwnerSalonResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "body": {
    "approval_mode": "auto",
    "working_hours": {"mon": {"open": "09:00", "close": "18:00"}}
  }
}
```

Output Response:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "owner_id": "55555555-5555-4555-8555-555555555555",
  "name": "Fresh Cut Salon",
  "description": "Men's grooming and styling",
  "category": "Men",
  "address": "MG Road, Kochi",
  "city": "Kochi",
  "lat": 9.9312,
  "lng": 76.2673,
  "timezone": "Asia/Kolkata",
  "working_hours": {"mon": {"open": "09:00", "close": "18:00"}},
  "approval_mode": "auto",
  "qr_token": "fresh-cut-kochi-qr",
  "profile_completed": true,
  "is_active": true,
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

### Owner image endpoints

Do not call the delete endpoint from frontend yet. It exists in the backend route
table, but intentionally rejects deletion until `salon_images` supports soft delete.

endpoint :

```bash
GET /v1/salons/me/images
POST /v1/salons/me/images
PATCH /v1/salons/me/images/{image_id}
DELETE /v1/salons/me/images/{image_id}
```

Pydantic schema:

```txt
Create Request: SalonImageCreateRequest
Update Request: SalonImageUpdateRequest
Response: SalonImageResponse or list[SalonImageResponse]
DELETE Response: 204 No Content
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "path_params": {
    "image_id": "22222222-2222-4222-8222-222222222222"
  },
  "body_for_post": {
    "url": "https://example.com/salon.jpg",
    "caption": "Front view",
    "is_main": true,
    "sort_order": 0
  },
  "body_for_patch": {
    "caption": "Updated caption",
    "is_main": true,
    "sort_order": 1
  }
}
```

Output Response:

```json
{
  "id": "22222222-2222-4222-8222-222222222222",
  "salon_id": "11111111-1111-4111-8111-111111111111",
  "url": "https://example.com/salon.jpg",
  "caption": "Front view",
  "is_main": true,
  "sort_order": 0,
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

### Owner holiday endpoints

Do not call the delete endpoint from frontend yet. It exists in the backend route
table, but intentionally rejects deletion until `salon_holidays` supports soft delete.

endpoint :

```bash
GET /v1/salons/me/holidays
POST /v1/salons/me/holidays
DELETE /v1/salons/me/holidays/{holiday_id}
```

Pydantic schema:

```txt
Create Request: HolidayCreateRequest
Response: HolidayResponse or list[HolidayResponse]
DELETE Response: 204 No Content
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "path_params": {
    "holiday_id": "99999999-9999-4999-8999-999999999999"
  },
  "body_for_post": {
    "holiday_date": "2026-08-15",
    "title": "Independence Day",
    "is_recurring": true
  }
}
```

Output Response:

```json
{
  "id": "99999999-9999-4999-8999-999999999999",
  "salon_id": "11111111-1111-4111-8111-111111111111",
  "holiday_date": "2026-08-15",
  "title": "Independence Day",
  "is_recurring": true,
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

### Owner service endpoints

endpoint :

```bash
GET /v1/salons/me/services
POST /v1/salons/me/services
PATCH /v1/salons/me/services/{service_id}
DELETE /v1/salons/me/services/{service_id}
```

Pydantic schema:

```txt
Create Request: ServiceCreateRequest
Update Request: ServiceUpdateRequest
Response: ServiceResponse or list[ServiceResponse]
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "path_params": {
    "service_id": "33333333-3333-4333-8333-333333333333"
  },
  "body_for_post": {
    "subcategory_id": "44444444-4444-4444-8444-444444444444",
    "name": "Haircut",
    "description": "Basic haircut",
    "duration_minutes": 30,
    "price": "250.00"
  },
  "body_for_patch": {
    "name": "Premium Haircut",
    "duration_minutes": 45,
    "price": "350.00",
    "is_active": true
  }
}
```

Output Response:

```json
{
  "id": "33333333-3333-4333-8333-333333333333",
  "salon_id": "11111111-1111-4111-8111-111111111111",
  "subcategory_id": "44444444-4444-4444-8444-444444444444",
  "name": "Haircut",
  "description": "Basic haircut",
  "duration_minutes": 30,
  "price": "250.00",
  "is_active": true,
  "category_name": "Hair",
  "subcategory_name": "Haircut",
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

### Owner staff endpoints

endpoint :

```bash
GET /v1/salons/me/staff
POST /v1/salons/me/staff
PATCH /v1/salons/me/staff/{staff_id}
DELETE /v1/salons/me/staff/{staff_id}
```

Pydantic schema:

```txt
Create Request: StaffCreateRequest
Update Request: StaffUpdateRequest
Response: StaffResponse or list[StaffResponse]
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "path_params": {
    "staff_id": "77777777-7777-4777-8777-777777777777"
  },
  "body_for_post": {
    "profile_id": null,
    "name": "Ameen",
    "photo_url": "https://example.com/staff.jpg",
    "specialization": "Fade specialist",
    "working_hours": {"mon": {"open": "09:00", "close": "18:00"}}
  },
  "body_for_patch": {
    "name": "Ameen K",
    "is_active": true
  }
}
```

Output Response:

```json
{
  "id": "77777777-7777-4777-8777-777777777777",
  "salon_id": "11111111-1111-4111-8111-111111111111",
  "profile_id": null,
  "name": "Ameen",
  "photo_url": "https://example.com/staff.jpg",
  "specialization": "Fade specialist",
  "working_hours": {"mon": {"open": "09:00", "close": "18:00"}},
  "is_active": true,
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

### Assign service to staff

endpoint :

```bash
POST /v1/salons/me/staff/{staff_id}/services
```

Pydantic schema:

```txt
Request: StaffServiceAssignRequest
Response: StaffServiceResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "path_params": {
    "staff_id": "77777777-7777-4777-8777-777777777777"
  },
  "body": {
    "service_id": "33333333-3333-4333-8333-333333333333",
    "duration_minutes": 30,
    "price_override": "275.00",
    "specialization": "Fade specialist"
  }
}
```

Output Response:

```json
{
  "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "staff_id": "77777777-7777-4777-8777-777777777777",
  "service_id": "33333333-3333-4333-8333-333333333333",
  "duration_minutes": 30,
  "price_override": "275.00",
  "specialization": "Fade specialist",
  "is_active": true,
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

### Staff service languages

endpoint :

```bash
GET /v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages
PUT /v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages
```

Pydantic schema:

```txt
PUT Request: StaffServiceLanguagesRequest
Response: list[LanguageResponse]
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "path_params": {
    "staff_id": "77777777-7777-4777-8777-777777777777",
    "staff_service_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
  },
  "body_for_put": {
    "language_codes": ["en", "ml"]
  }
}
```

Output Response:

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

### Owner blocked slots

endpoint :

```bash
GET /v1/salons/me/blocks
POST /v1/salons/me/blocks
DELETE /v1/salons/me/blocks/{block_id}
```

Pydantic schema:

```txt
Create Request: BlockedSlotCreateRequest
Response: BlockedSlotResponse or list[BlockedSlotResponse]
DELETE Response: 204 No Content
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "path_params": {
    "block_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
  },
  "body_for_post": {
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
}
```

Output Response:

```json
{
  "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  "staff_id": "77777777-7777-4777-8777-777777777777",
  "salon_id": "11111111-1111-4111-8111-111111111111",
  "start_datetime": "2026-08-10T12:00:00Z",
  "end_datetime": "2026-08-10T13:00:00Z",
  "block_type": "lunch",
  "reason": "Lunch break",
  "is_full_day": false,
  "is_recurring": false,
  "recurrence_rule": null,
  "recurrence_end": null,
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

## Booking And Availability APIs

### Get available booking slots

endpoint :

```bash
GET /v1/availability
```

Pydantic schema:

```txt
Response: list[AvailabilityResponse]
```

Input Request:

```json
{
  "headers": {},
  "query_params": {
    "staff_id": "77777777-7777-4777-8777-777777777777",
    "date": "2026-08-10",
    "service_ids": ["33333333-3333-4333-8333-333333333333"]
  },
  "body": null
}
```

Output Response:

```json
[
  {
    "slot_start": "2026-08-10T09:00:00Z",
    "slot_end": "2026-08-10T09:30:00Z",
    "id": "09:00 AM",
    "time": "09:00 AM",
    "barberName": "Ameen"
  }
]
```

### Create booking

endpoint :

```bash
POST /v1/bookings
```

Pydantic schema:

```txt
Request: BookingCreateRequest
Response: BookingResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "body": {
    "salon_id": "11111111-1111-4111-8111-111111111111",
    "staff_id": "77777777-7777-4777-8777-777777777777",
    "service_ids": ["33333333-3333-4333-8333-333333333333"],
    "start_datetime": "2026-08-10T09:00:00Z",
    "customer_name": "Thanseef",
    "customer_phone": "+919876543210",
    "source": "app",
    "notes": "Please keep the side short"
  }
}
```

Output Response:

```json
{
  "id": "66666666-6666-4666-8666-666666666666",
  "salon_id": "11111111-1111-4111-8111-111111111111",
  "staff_id": "77777777-7777-4777-8777-777777777777",
  "customer_id": "8efc2d51-9d4c-4f1d-8e2e-0f6f0d624aa1",
  "customer_name": "Thanseef",
  "customer_phone": "+919876543210",
  "phone_verified": true,
  "source": "app",
  "status": "confirmed",
  "start_datetime": "2026-08-10T09:00:00Z",
  "end_datetime": "2026-08-10T09:30:00Z",
  "total_duration_minutes": 30,
  "total_price": "250.00",
  "payment_status": "unpaid",
  "payment_method": null,
  "rejection_reason": null,
  "notes": "Please keep the side short",
  "services": [
    {
      "service_id": "33333333-3333-4333-8333-333333333333",
      "service_name": "Haircut",
      "duration_minutes": 30,
      "price": "250.00"
    }
  ],
  "salon_name": "Fresh Cut Salon",
  "salon_address": "MG Road, Kochi",
  "salon_image": "https://example.com/salon.jpg",
  "staff_name": "Ameen",
  "staff_photo_url": "https://example.com/staff.jpg",
  "created_at": "2026-08-10T08:30:00Z",
  "updated_at": "2026-08-10T08:30:00Z",
  "can_cancel": true
}
```

### Booking read and status endpoints

endpoint :

```bash
GET /v1/bookings
GET /v1/bookings/{booking_id}
POST /v1/bookings/{booking_id}/approve
POST /v1/bookings/{booking_id}/complete
```

Pydantic schema:

```txt
Response: BookingResponse or list[BookingResponse]
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt"
  },
  "path_params": {
    "booking_id": "66666666-6666-4666-8666-666666666666"
  },
  "body": null
}
```

Output Response:

```json
{
  "id": "66666666-6666-4666-8666-666666666666",
  "salon_id": "11111111-1111-4111-8111-111111111111",
  "staff_id": "77777777-7777-4777-8777-777777777777",
  "customer_id": "8efc2d51-9d4c-4f1d-8e2e-0f6f0d624aa1",
  "customer_name": "Thanseef",
  "customer_phone": "+919876543210",
  "phone_verified": true,
  "source": "app",
  "status": "confirmed",
  "start_datetime": "2026-08-10T09:00:00Z",
  "end_datetime": "2026-08-10T09:30:00Z",
  "total_duration_minutes": 30,
  "total_price": "250.00",
  "payment_status": "unpaid",
  "payment_method": null,
  "rejection_reason": null,
  "notes": "Please keep the side short",
  "services": [],
  "salon_name": "Fresh Cut Salon",
  "salon_address": "MG Road, Kochi",
  "salon_image": "https://example.com/salon.jpg",
  "staff_name": "Ameen",
  "staff_photo_url": "https://example.com/staff.jpg",
  "created_at": "2026-08-10T08:30:00Z",
  "updated_at": "2026-08-10T08:30:00Z",
  "can_cancel": true
}
```

### Reject booking

endpoint :

```bash
POST /v1/bookings/{booking_id}/reject
```

Pydantic schema:

```txt
Request: RejectBookingRequest
Response: BookingResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "path_params": {
    "booking_id": "66666666-6666-4666-8666-666666666666"
  },
  "body": {
    "rejection_reason": "Staff unavailable"
  }
}
```

Output Response:

```json
{
  "id": "66666666-6666-4666-8666-666666666666",
  "salon_id": "11111111-1111-4111-8111-111111111111",
  "staff_id": "77777777-7777-4777-8777-777777777777",
  "customer_id": "8efc2d51-9d4c-4f1d-8e2e-0f6f0d624aa1",
  "customer_name": "Thanseef",
  "customer_phone": "+919876543210",
  "phone_verified": true,
  "source": "app",
  "status": "rejected",
  "start_datetime": "2026-08-10T09:00:00Z",
  "end_datetime": "2026-08-10T09:30:00Z",
  "total_duration_minutes": 30,
  "total_price": "250.00",
  "payment_status": "unpaid",
  "payment_method": null,
  "rejection_reason": "Staff unavailable",
  "notes": null,
  "services": [],
  "salon_name": "Fresh Cut Salon",
  "salon_address": "MG Road, Kochi",
  "salon_image": "https://example.com/salon.jpg",
  "staff_name": "Ameen",
  "staff_photo_url": "https://example.com/staff.jpg",
  "created_at": "2026-08-10T08:30:00Z",
  "updated_at": "2026-08-10T08:45:00Z",
  "can_cancel": false
}
```

### Cancel booking

endpoint :

```bash
POST /v1/bookings/{booking_id}/cancel
```

Pydantic schema:

```txt
Request: CancelBookingRequest
Response: BookingResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "path_params": {
    "booking_id": "66666666-6666-4666-8666-666666666666"
  },
  "body": {
    "reason_code": "schedule_conflict",
    "reason_text": "Need to reschedule"
  }
}
```

Output Response:

```json
{
  "id": "66666666-6666-4666-8666-666666666666",
  "salon_id": "11111111-1111-4111-8111-111111111111",
  "staff_id": "77777777-7777-4777-8777-777777777777",
  "customer_id": "8efc2d51-9d4c-4f1d-8e2e-0f6f0d624aa1",
  "customer_name": "Thanseef",
  "customer_phone": "+919876543210",
  "phone_verified": true,
  "source": "app",
  "status": "cancelled",
  "start_datetime": "2026-08-10T09:00:00Z",
  "end_datetime": "2026-08-10T09:30:00Z",
  "total_duration_minutes": 30,
  "total_price": "250.00",
  "payment_status": "unpaid",
  "payment_method": null,
  "rejection_reason": null,
  "notes": "Cancelled: schedule_conflict - Need to reschedule",
  "services": [],
  "salon_name": "Fresh Cut Salon",
  "salon_address": "MG Road, Kochi",
  "salon_image": "https://example.com/salon.jpg",
  "staff_name": "Ameen",
  "staff_photo_url": "https://example.com/staff.jpg",
  "created_at": "2026-08-10T08:30:00Z",
  "updated_at": "2026-08-10T08:45:00Z",
  "can_cancel": false
}
```

### Record booking payment

endpoint :

```bash
POST /v1/bookings/{booking_id}/payment
```

Pydantic schema:

```txt
Request: PaymentRequest
Response: BookingResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "path_params": {
    "booking_id": "66666666-6666-4666-8666-666666666666"
  },
  "body": {
    "payment_method": "cash"
  }
}
```

Output Response:

```json
{
  "id": "66666666-6666-4666-8666-666666666666",
  "salon_id": "11111111-1111-4111-8111-111111111111",
  "staff_id": "77777777-7777-4777-8777-777777777777",
  "customer_id": "8efc2d51-9d4c-4f1d-8e2e-0f6f0d624aa1",
  "customer_name": "Thanseef",
  "customer_phone": "+919876543210",
  "phone_verified": true,
  "source": "app",
  "status": "completed",
  "start_datetime": "2026-08-10T09:00:00Z",
  "end_datetime": "2026-08-10T09:30:00Z",
  "total_duration_minutes": 30,
  "total_price": "250.00",
  "payment_status": "paid",
  "payment_method": "cash",
  "rejection_reason": null,
  "notes": null,
  "services": [],
  "salon_name": "Fresh Cut Salon",
  "salon_address": "MG Road, Kochi",
  "salon_image": "https://example.com/salon.jpg",
  "staff_name": "Ameen",
  "staff_photo_url": "https://example.com/staff.jpg",
  "created_at": "2026-08-10T08:30:00Z",
  "updated_at": "2026-08-10T09:45:00Z",
  "can_cancel": false
}
```

## Notification And Device APIs

### List notifications

endpoint :

```bash
GET /v1/notifications
```

Pydantic schema:

```txt
Response: list[NotificationResponse]
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt"
  },
  "body": null
}
```

Output Response:

```json
[
  {
    "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    "user_id": "8efc2d51-9d4c-4f1d-8e2e-0f6f0d624aa1",
    "booking_id": "66666666-6666-4666-8666-666666666666",
    "type": "booking_status",
    "title": "Booking confirmed",
    "body": "Your booking has been confirmed.",
    "read": false,
    "read_at": null,
    "created_at": "2026-08-10T09:00:00Z"
  }
]
```

### Mark notification read

endpoint :

```bash
POST /v1/notifications/{notification_id}/read
```

Pydantic schema:

```txt
Response: NotificationResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt"
  },
  "path_params": {
    "notification_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
  },
  "body": null
}
```

Output Response:

```json
{
  "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
  "user_id": "8efc2d51-9d4c-4f1d-8e2e-0f6f0d624aa1",
  "booking_id": "66666666-6666-4666-8666-666666666666",
  "type": "booking_status",
  "title": "Booking confirmed",
  "body": "Your booking has been confirmed.",
  "read": true,
  "read_at": "2026-08-10T09:05:00Z",
  "created_at": "2026-08-10T09:00:00Z"
}
```

### Register device token

endpoint :

```bash
POST /v1/devices
```

Pydantic schema:

```txt
Request: DeviceRegisterRequest
Response: DeviceRegisterResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "body": {
    "token": "fcm-device-token",
    "platform": "ios",
    "device_name": "Thanseef iPhone"
  }
}
```

Output Response:

```json
{
  "id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
  "token": "fcm-device-token",
  "platform": "ios",
  "device_name": "Thanseef iPhone",
  "is_active": true,
  "last_seen_at": "2026-08-10T09:00:00Z"
}
```

### Deactivate device token

endpoint :

```bash
DELETE /v1/devices/{token}
```

Pydantic schema:

```txt
Response: 204 No Content
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt"
  },
  "path_params": {
    "token": "fcm-device-token"
  },
  "body": null
}
```

Output Response:

```json
null
```

## Walk-In QR APIs

### Resolve QR token

endpoint :

```bash
GET /v1/walkin/{qr_token}
```

Pydantic schema:

```txt
Response: WalkInSalonResponse
```

Input Request:

```json
{
  "headers": {},
  "path_params": {
    "qr_token": "fresh-cut-kochi-qr"
  },
  "body": null
}
```

Output Response:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "name": "Fresh Cut Salon",
  "description": "Men's grooming and styling",
  "city": "Kochi",
  "address": "MG Road, Kochi",
  "image_url": "https://example.com/salon.jpg",
  "timezone": "Asia/Kolkata",
  "approval_mode": "auto",
  "services": [
    {
      "id": "33333333-3333-4333-8333-333333333333",
      "salon_id": "11111111-1111-4111-8111-111111111111",
      "subcategory_id": "44444444-4444-4444-8444-444444444444",
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
      "id": "77777777-7777-4777-8777-777777777777",
      "name": "Ameen",
      "photo_url": "https://example.com/staff.jpg",
      "specialization": "Fade specialist"
    }
  ]
}
```

### Send or verify phone OTP

endpoint :

```bash
POST /v1/walkin/{qr_token}/verify-phone
```

Pydantic schema:

```txt
Request: WalkInVerifyPhoneRequest
Response: WalkInVerifyPhoneResponse
```

Input Request:

```json
{
  "headers": {
    "Content-Type": "application/json"
  },
  "path_params": {
    "qr_token": "fresh-cut-kochi-qr"
  },
  "body_to_send_otp": {
    "phone": "+919876543210"
  },
  "body_to_verify_otp": {
    "phone": "+919876543210",
    "otp": "123456"
  }
}
```

Output Response:

```json
{
  "verified": true,
  "access_token": "supabase-access-jwt",
  "refresh_token": "supabase-refresh-token"
}
```

### Create QR walk-in booking

endpoint :

```bash
POST /v1/walkin/{qr_token}/bookings
```

Pydantic schema:

```txt
Request: BookingCreateRequest
Response: BookingResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "path_params": {
    "qr_token": "fresh-cut-kochi-qr"
  },
  "body": {
    "salon_id": "11111111-1111-4111-8111-111111111111",
    "staff_id": "77777777-7777-4777-8777-777777777777",
    "service_ids": ["33333333-3333-4333-8333-333333333333"],
    "start_datetime": "2026-08-10T09:00:00Z",
    "customer_name": "Thanseef",
    "customer_phone": "+919876543210",
    "source": "qr_walkin",
    "notes": null
  }
}
```

Output Response:

```json
{
  "id": "66666666-6666-4666-8666-666666666666",
  "salon_id": "11111111-1111-4111-8111-111111111111",
  "staff_id": "77777777-7777-4777-8777-777777777777",
  "customer_id": "8efc2d51-9d4c-4f1d-8e2e-0f6f0d624aa1",
  "customer_name": "Thanseef",
  "customer_phone": "+919876543210",
  "phone_verified": true,
  "source": "qr_walkin",
  "status": "confirmed",
  "start_datetime": "2026-08-10T09:00:00Z",
  "end_datetime": "2026-08-10T09:30:00Z",
  "total_duration_minutes": 30,
  "total_price": "250.00",
  "payment_status": "unpaid",
  "payment_method": null,
  "rejection_reason": null,
  "notes": null,
  "services": [],
  "salon_name": "Fresh Cut Salon",
  "salon_address": "MG Road, Kochi",
  "salon_image": "https://example.com/salon.jpg",
  "staff_name": "Ameen",
  "staff_photo_url": "https://example.com/staff.jpg",
  "created_at": "2026-08-10T08:30:00Z",
  "updated_at": "2026-08-10T08:30:00Z",
  "can_cancel": true
}
```

## Super Admin APIs

All endpoints in this section require:

```http
Authorization: Bearer <super_admin_supabase_access_token>
```

### Create salon owner and salon

endpoint :

```bash
POST /v1/admin/salons
```

Pydantic schema:

```txt
Request: AdminCreateSalonRequest
Response: AdminSalonResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer super-admin-supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "body": {
    "email": "owner@example.com",
    "password": "StrongPass123",
    "full_name": "Salon Owner",
    "salon_name": "Fresh Cut Salon",
    "timezone": "Asia/Kolkata"
  }
}
```

Output Response:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "owner_id": "55555555-5555-4555-8555-555555555555",
  "owner_email": "owner@example.com",
  "owner_name": "Salon Owner",
  "name": "Fresh Cut Salon",
  "description": null,
  "category": null,
  "address": null,
  "city": null,
  "timezone": "Asia/Kolkata",
  "approval_mode": "manual",
  "profile_completed": false,
  "is_active": true,
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

### Admin salon management

endpoint :

```bash
GET /v1/admin/salons
PATCH /v1/admin/salons/{salon_id}
POST /v1/admin/salons/{salon_id}/deactivate
```

Pydantic schema:

```txt
List Response: list[AdminSalonResponse]
Patch Request: AdminUpdateSalonRequest
Patch Response: AdminSalonResponse
Deactivate Response: AdminDeactivateSalonResponse
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer super-admin-supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "query_params_for_get": {
    "search": "fresh",
    "limit": 50,
    "offset": 0
  },
  "path_params": {
    "salon_id": "11111111-1111-4111-8111-111111111111"
  },
  "body_for_patch": {
    "name": "Fresh Cut Salon",
    "timezone": "Asia/Kolkata"
  }
}
```

Output Response:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "owner_id": "55555555-5555-4555-8555-555555555555",
  "owner_email": "owner@example.com",
  "owner_name": "Salon Owner",
  "name": "Fresh Cut Salon",
  "description": null,
  "category": null,
  "address": null,
  "city": null,
  "timezone": "Asia/Kolkata",
  "approval_mode": "manual",
  "profile_completed": false,
  "is_active": true,
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

### Admin category endpoints

endpoint :

```bash
GET /v1/admin/catalog/categories
POST /v1/admin/catalog/categories
PATCH /v1/admin/catalog/categories/{category_id}
POST /v1/admin/catalog/categories/{category_id}/deactivate
```

Pydantic schema:

```txt
Create Request: CategoryCreateRequest
Update Request: CategoryUpdateRequest
Response: CategoryResponse or list[CategoryResponse]
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer super-admin-supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "query_params_for_get": {
    "include_inactive": false
  },
  "path_params": {
    "category_id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
  },
  "body_for_post": {
    "name": "Hair",
    "slug": "hair",
    "image_url": "https://example.com/hair.jpg",
    "description": "Hair services",
    "sort_order": 1
  },
  "body_for_patch": {
    "name": "Hair Care",
    "slug": "hair-care",
    "is_active": true
  }
}
```

Output Response:

```json
{
  "id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
  "name": "Hair",
  "slug": "hair",
  "image_url": "https://example.com/hair.jpg",
  "description": "Hair services",
  "sort_order": 1,
  "is_active": true,
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

### Admin subcategory endpoints

endpoint :

```bash
GET /v1/admin/catalog/categories/{category_id}/subcategories
POST /v1/admin/catalog/subcategories
PATCH /v1/admin/catalog/subcategories/{subcategory_id}
POST /v1/admin/catalog/subcategories/{subcategory_id}/deactivate
```

Pydantic schema:

```txt
Create Request: SubcategoryCreateRequest
Update Request: SubcategoryUpdateRequest
Response: SubcategoryResponse or list[SubcategoryResponse]
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer super-admin-supabase-access-jwt",
    "Content-Type": "application/json"
  },
  "query_params_for_get": {
    "include_inactive": false
  },
  "path_params": {
    "category_id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
    "subcategory_id": "44444444-4444-4444-8444-444444444444"
  },
  "body_for_post": {
    "category_id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
    "name": "Haircut",
    "slug": "haircut",
    "image_url": "https://example.com/haircut.jpg",
    "description": "Haircut services",
    "sort_order": 1
  },
  "body_for_patch": {
    "name": "Premium Haircut",
    "slug": "premium-haircut",
    "is_active": true
  }
}
```

Output Response:

```json
{
  "id": "44444444-4444-4444-8444-444444444444",
  "category_id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
  "name": "Haircut",
  "slug": "haircut",
  "image_url": "https://example.com/haircut.jpg",
  "description": "Haircut services",
  "sort_order": 1,
  "is_active": true,
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-10T09:00:00Z"
}
```

### List supported languages

endpoint :

```bash
GET /v1/admin/catalog/languages
```

Pydantic schema:

```txt
Response: list[LanguageResponse]
```

Input Request:

```json
{
  "headers": {
    "Authorization": "Bearer supabase-access-jwt"
  },
  "body": null
}
```

Output Response:

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

## Notes For Frontend Integration

1. Use Supabase Auth in the frontend for Google sign-in and token refresh storage.
2. Send the Supabase access token to this API in the `Authorization` header.
3. Do not compute availability in the frontend. Use `GET /v1/availability`.
4. Do not create bookings directly in Supabase. Use `POST /v1/bookings` or
   `POST /v1/walkin/{qr_token}/bookings`.
5. Treat all UUID fields as strings.
6. Treat money values returned by the API as strings to avoid floating point issues.
7. `DELETE /v1/salons/me/images/{image_id}` and
   `DELETE /v1/salons/me/holidays/{holiday_id}` intentionally reject deletion until
   the schema supports soft delete for those tables.
