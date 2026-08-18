# Backend Features

This file tracks backend feature areas for the shared API. Jira remains the source of
truth for task status, assignee, priority, and acceptance criteria.

## Currently Implemented

### Foundation

- `GET /health`
- `GET /health/db`
- `POST /v1/auth/refresh`
- `GET /v1/auth/me`
- Supabase Google OAuth sign-in support through frontend-managed Supabase sessions
- Supabase JWT verification through JWKS
- Actor profile resolution from `profiles`
- Async SQLAlchemy database session setup
- Alembic baseline migration wrapper for the v3 SQL schema

### Customer App APIs

- `GET /v1/customer/profile`
- `PATCH /v1/customer/profile`
- `GET /v1/salons`
- `GET /v1/salons/nearby`
- `GET /v1/salons/{salon_id}`
- `GET /v1/salons/{salon_id}/services`

### Barber/Owner App APIs

- `GET /v1/salons/me`
- `PATCH /v1/salons/me`
- `POST /v1/salons/me/complete-profile`
- `PATCH /v1/salons/me/settings`
- `GET /v1/salons/me/images`
- `POST /v1/salons/me/images`
- `PATCH /v1/salons/me/images/{image_id}`
- `GET /v1/salons/me/holidays`
- `POST /v1/salons/me/holidays`
- `GET /v1/salons/me/services`
- `POST /v1/salons/me/services`
- `PATCH /v1/salons/me/services/{service_id}`
- `DELETE /v1/salons/me/services/{service_id}` soft-deactivates through `is_active`
- `GET /v1/salons/me/staff`
- `POST /v1/salons/me/staff`
- `PATCH /v1/salons/me/staff/{staff_id}`
- `DELETE /v1/salons/me/staff/{staff_id}` soft-deactivates through `is_active`
- `POST /v1/salons/me/staff/{staff_id}/services`

### Booking, Notifications, And Devices

- `GET /v1/availability`
- `POST /v1/bookings`
- `GET /v1/bookings`
- `GET /v1/bookings/{booking_id}`
- `POST /v1/bookings/{booking_id}/approve`
- `POST /v1/bookings/{booking_id}/reject`
- `POST /v1/bookings/{booking_id}/complete`
- `POST /v1/bookings/{booking_id}/cancel`
- `POST /v1/bookings/{booking_id}/payment`
- `GET /v1/notifications`
- `POST /v1/notifications/{notification_id}/read`
- `POST /v1/devices`
- `DELETE /v1/devices/{token}`

### Current Schema Limitations

- `DELETE /v1/salons/me/images/{image_id}` is intentionally rejected because
  `salon_images` has no `is_active` column for soft delete.
- `DELETE /v1/salons/me/holidays/{holiday_id}` is intentionally rejected because
  `salon_holidays` has no `is_active` column for soft delete.

## MVP Backend Features

### 1. Authentication And Actor Resolution

- Google sign-in through Supabase Auth
- Refresh Supabase Auth sessions
- Resolve current authenticated profile
- Reject inactive profiles
- Resolve roles from `profiles`, not JWT role claims

### 2. Super Admin

- Create salon owner auth user and salon record
- List/search salons
- Update salon owner/salon basics
- Deactivate salons and owner access
- Manage global service categories and subcategories

### 3. Salon Owner

- View and complete salon profile
- Manage salon images
- Manage holidays
- Manage working hours and settings
- Manage services
- Manage staff
- Assign services to staff
- Manage staff/service language and override data
- Manage blocked slots

### 4. Booking Engine

- Get availability through the database `get_available_slots` function
- Create bookings through the database `create_booking` function
- List bookings with role-scoped authorization
- Approve, reject, complete, and cancel bookings
- Record payment status

### 5. Walk-in QR

- Resolve public QR token
- Return public salon/services/staff data for QR booking
- Support phone OTP verification through Supabase
- Create QR walk-in bookings

### 6. Notifications

- Register device tokens
- Deactivate device tokens
- List notifications
- Mark notifications as read
- Fan out push notifications through Firebase Cloud Messaging

## Future Backend Features

- Online payment provider integration
- Coupons and offers
- Reviews and ratings
- Chat support
- Loyalty points
- Multi-language content
- Analytics/reporting APIs
