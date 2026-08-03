# Backend Features

This file tracks backend feature areas for the shared API. Jira remains the source of
truth for task status, assignee, priority, and acceptance criteria.

## Currently Implemented

### Foundation

- `GET /health`
- `GET /health/db`
- `POST /v1/auth/login`
- `POST /v1/auth/refresh`
- `GET /v1/auth/me`
- Supabase JWT verification through JWKS
- Actor profile resolution from `profiles`
- Async SQLAlchemy database session setup
- Alembic baseline migration wrapper for the v3 SQL schema

## MVP Backend Features

### 1. Authentication And Actor Resolution

- Login through Supabase Auth
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
