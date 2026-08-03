# Salon Platform Backend Guide

This guide explains how the FastAPI backend works, what each code area does, and how the customer app and barber app should use it.

## 1. Backend Purpose

This backend supports two apps:

- Customer app: customers search salons, view services, check available slots, create bookings, cancel appointments, and receive notifications.
- Barber/owner app: owners manage salon profile, services, staff, blocked slots, walk-ins, booking approvals, and payment status.

The important rule is:

```txt
Both apps use the same booking and slot logic.
```

That means customer app bookings, barber app walk-ins, and owner-managed appointments all go through the same backend rules, so double booking is prevented in one shared place.

## 2. How To Run Locally

From the backend folder:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open the API documentation:

```txt
http://127.0.0.1:8000/docs
```

Health check:

```txt
GET /health
```

Expected response:

```json
{
  "status": "ok"
}
```

## 3. Seed Data

Seed data creates demo users, a salon, a category, a service, and a staff member.

```bash
python -m app.db.seed
```

Demo logins:

```txt
owner@example.com / password123
customer@example.com / password123
```

The seed script prints IDs for:

- Salon
- Staff
- Service

Use those IDs when testing slot and booking APIs in Swagger.

## 4. Folder Structure

```txt
backend/
  app/
    api/
      deps.py
      router.py
      routes/
        auth.py
        customer.py
        salons.py
        bookings.py
        notifications.py
        barber.py

    core/
      config.py
      security.py

    db/
      base.py
      session.py
      seed.py

    models/
      domain.py
      enums.py

    schemas/
      auth.py
      salon.py
      booking.py
      barber.py
      notification.py
      common.py

    services/
      bookings.py
      slots.py
      permissions.py

    main.py

  tests/
```

## 5. Request Flow

A normal API request flows like this:

```txt
Mobile app
  -> FastAPI route
  -> Auth dependency, if protected
  -> Pydantic schema validation
  -> Service/business logic
  -> SQLAlchemy models/database
  -> Pydantic response
  -> Mobile app
```

Example booking request:

```txt
POST /api/v1/bookings
  -> checks logged-in user
  -> validates request body with BookingCreate
  -> calls services/bookings.py
  -> checks staff, services, slot availability, conflicts
  -> creates booking and booking service snapshots
  -> creates notification
  -> returns BookingOut
```

## 6. Main App Entry

File:

```txt
app/main.py
```

This creates the FastAPI app.

It does four main things:

- Creates the `FastAPI` object.
- Adds CORS middleware.
- Creates database tables locally with `Base.metadata.create_all`.
- Registers all API routes under `/api/v1`.

Important route prefixes:

```txt
/api/v1/auth
/api/v1/customer
/api/v1/salons
/api/v1/bookings
/api/v1/notifications
/api/v1/barber
```

## 7. Config

File:

```txt
app/core/config.py
```

Settings are loaded from environment variables or `.env`.

Important values:

```txt
DATABASE_URL
SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES
BACKEND_CORS_ORIGINS
```

Local default database:

```txt
sqlite:///./salon_platform.db
```

For production, replace this with a PostgreSQL URL.

## 8. Authentication

Files:

```txt
app/api/routes/auth.py
app/core/security.py
app/api/deps.py
```

Current auth uses:

- Email and password login.
- Salted password hashing with Passlib PBKDF2-SHA256.
- JWT access tokens.
- Role-based access checks.

Supported roles:

```txt
super_admin
owner
staff
customer
```

Public auth endpoints:

```txt
POST /api/v1/auth/register
POST /api/v1/auth/login
```

Protected auth endpoint:

```txt
GET /api/v1/auth/me
```

When the frontend logs in, it receives:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

The frontend must send the token on protected requests:

```txt
Authorization: Bearer ACCESS_TOKEN
```

## 9. Database Models

Main file:

```txt
app/models/domain.py
```

Enums:

```txt
app/models/enums.py
```

Important tables:

- `profiles`: all users and roles.
- `salons`: salon profile and working hours.
- `salon_images`: salon image gallery.
- `salon_holidays`: dates when a salon is closed.
- `service_categories`: global service category.
- `service_subcategories`: global service subcategory.
- `services`: salon service list.
- `staff`: barbers/staff under a salon.
- `staff_services`: which staff member can perform which service.
- `blocked_slots`: staff or salon unavailable time.
- `bookings`: appointment records.
- `booking_services`: service snapshot for each booking.
- `notifications`: in-app notifications.
- `device_tokens`: FCM/device tokens.

## 10. Schemas

Files:

```txt
app/schemas/
```

Schemas define request and response shapes.

Example:

```txt
BookingCreate
```

is the request body for creating a booking.

```txt
BookingOut
```

is the response returned to the app.

This keeps API inputs and outputs clear and prevents the app from sending random fields.

## 11. Customer App API Flow

### Signup

```txt
POST /api/v1/auth/register
```

Use role:

```json
{
  "role": "customer"
}
```

### Login

```txt
POST /api/v1/auth/login
```

Store the returned JWT token in the mobile app.

### View Or Update Profile

```txt
GET /api/v1/customer/profile
PATCH /api/v1/customer/profile
```

### Salon Discovery

```txt
GET /api/v1/salons
```

Optional query params:

```txt
q
city
lat
lng
radius_km
```

Nearby search example:

```txt
GET /api/v1/salons?lat=9.9816&lng=76.2999&radius_km=10
```

### Salon Details

```txt
GET /api/v1/salons/{salon_id}
```

### Salon Services

```txt
GET /api/v1/salons/{salon_id}/services
```

### Available Slots

```txt
POST /api/v1/bookings/slots
```

Request:

```json
{
  "staff_id": "STAFF_ID",
  "service_ids": ["SERVICE_ID"],
  "booking_date": "2026-08-01"
}
```

The backend calculates the required duration from the selected services.

### Create Booking

```txt
POST /api/v1/bookings
```

Request:

```json
{
  "salon_id": "SALON_ID",
  "staff_id": "STAFF_ID",
  "service_ids": ["SERVICE_ID"],
  "start_datetime": "2026-08-01T10:00:00+05:30",
  "customer_name": "Demo Customer",
  "customer_phone": "+919999999002",
  "source": "app",
  "notes": "Please be on time"
}
```

If the salon approval mode is:

- `auto`: booking becomes `confirmed`.
- `manual`: booking becomes `pending`.

### List My Bookings

```txt
GET /api/v1/bookings
```

Optional:

```txt
GET /api/v1/bookings?status=pending
```

### Booking Details

```txt
GET /api/v1/bookings/{booking_id}
```

### Cancel Booking

```txt
POST /api/v1/bookings/{booking_id}/cancel
```

Customers can cancel their own bookings unless the booking is already completed, rejected, or cancelled.

### Notifications

```txt
GET /api/v1/notifications
POST /api/v1/notifications/{notification_id}/read
```

### Device Token

```txt
POST /api/v1/notifications/devices
DELETE /api/v1/notifications/devices/{token}
```

Used for Firebase/FCM push token registration.

## 12. Barber/Owner App API Flow

Barber app routes are under:

```txt
/api/v1/barber
```

These routes require an owner, staff, or super admin token. Most write operations require the user to own the salon.

### Create Salon

```txt
POST /api/v1/barber/salons
```

Request includes:

- name
- address
- city
- latitude/longitude
- working hours
- approval mode
- slot interval

### List My Salons

```txt
GET /api/v1/barber/salons
```

Owners see their own salons.

Super admin sees all salons.

### Update Salon

```txt
PATCH /api/v1/barber/salons/{salon_id}
```

### Add Salon Image

```txt
POST /api/v1/barber/salons/{salon_id}/images
```

If `is_main` is true, the backend demotes existing main images for that salon.

### Add Holiday

```txt
POST /api/v1/barber/salons/{salon_id}/holidays
```

Bookings and slots will not be available on holiday dates.

### Create Service Category

```txt
POST /api/v1/barber/categories
```

Only super admin can create global categories.

### Create Service Subcategory

```txt
POST /api/v1/barber/subcategories
```

Only super admin can create global subcategories.

### Create Salon Service

```txt
POST /api/v1/barber/services
```

Creates a service offered by a salon.

### Update Salon Service

```txt
PATCH /api/v1/barber/services/{service_id}
```

### Create Staff

```txt
POST /api/v1/barber/staff
```

Staff means a barber or employee working under a salon.

### List Salon Staff

```txt
GET /api/v1/barber/salons/{salon_id}/staff
```

### Assign Service To Staff

```txt
POST /api/v1/barber/staff-services
```

This tells the backend that a staff member can perform a service.

It can also override:

- duration
- price
- specialization
- languages

### Create Blocked Slot

```txt
POST /api/v1/barber/blocked-slots
```

Blocked slots can be:

- staff-specific
- salon-wide

Examples:

- lunch break
- leave
- training
- full-day holiday
- temporary unavailable time

Blocked slots are used by the slot engine.

### Create Walk-In Booking

```txt
POST /api/v1/barber/walk-ins
```

This uses the same booking engine as the customer app.

Walk-ins should usually use:

```json
{
  "source": "manual_walkin"
}
```

Manual walk-ins are automatically confirmed.

### List Salon Bookings

```txt
GET /api/v1/barber/bookings?salon_id=SALON_ID
```

Optional:

```txt
GET /api/v1/barber/bookings?salon_id=SALON_ID&status=pending
```

### Update Booking Status

```txt
PATCH /api/v1/barber/bookings/{booking_id}/status
```

Allowed statuses:

```txt
pending
confirmed
rejected
completed
cancelled
```

Reject request must include `rejection_reason`.

### Update Payment

```txt
PATCH /api/v1/barber/bookings/{booking_id}/payment
```

Payment statuses:

```txt
unpaid
paid
```

Payment methods:

```txt
cash
online
```

## 13. Slot Engine

Main file:

```txt
app/services/slots.py
```

Function:

```txt
get_available_slots()
```

The slot engine checks:

- Salon is active.
- Salon profile is completed.
- Staff is active.
- Salon is not closed for holiday.
- Salon or staff working hours.
- Existing pending or confirmed bookings.
- Staff blocked slots.
- Salon-wide blocked slots.
- Slot is not in the past.

It returns available start and end times.

Important statuses that block slots:

```txt
pending
confirmed
```

Cancelled, rejected, and completed bookings do not block new bookings.

## 14. Booking Engine

Main file:

```txt
app/services/bookings.py
```

Main function:

```txt
create_booking()
```

It handles:

- Staff exists and belongs to salon.
- Salon is active and completed.
- Booking is not in the past.
- Staff offers every selected service.
- Total duration calculation.
- Total price calculation.
- Staff-specific duration or price override.
- Slot availability check.
- Conflict validation.
- Booking status decision.
- Booking service snapshots.
- Customer notification creation.

Booking service snapshots are important.

If the salon later changes service price or duration, old bookings still keep the original booked price and duration.

## 15. Working Hours Shape

Salon and staff working hours use JSON.

Example:

```json
{
  "mon": { "open": "09:00", "close": "21:00" },
  "tue": { "open": "09:00", "close": "21:00" },
  "wed": { "open": "09:00", "close": "21:00" },
  "thu": { "open": "09:00", "close": "21:00" },
  "fri": { "open": "09:00", "close": "21:00" },
  "sat": { "open": "09:00", "close": "21:00" },
  "sun": null
}
```

If staff working hours are null, the staff inherits salon working hours.

## 16. Booking Status Meaning

```txt
pending
```

Booking was created and is waiting for owner approval.

```txt
confirmed
```

Booking is approved and blocks the staff slot.

```txt
rejected
```

Owner rejected the booking. Requires rejection reason.

```txt
completed
```

Service is finished.

```txt
cancelled
```

Customer or owner cancelled the booking.

## 17. Payment Status Meaning

```txt
unpaid
```

Payment has not been recorded.

```txt
paid
```

Payment has been recorded by owner/barber.

The current backend stores payment state only. It does not integrate an online payment gateway yet.

## 18. Notifications

Notifications are stored in:

```txt
notifications
```

They are created for important booking events.

Current examples:

- booking created
- booking confirmed
- booking rejected
- booking completed
- booking cancelled

Push notification delivery is not implemented yet. Device tokens are stored so Firebase/FCM delivery can be added later.

## 19. Local Database Notes

The local backend uses SQLite by default:

```txt
backend/salon_platform.db
```

This is useful for development.

For production, use PostgreSQL.

Supabase can be used as the production PostgreSQL database. See:

```txt
SUPABASE_CONNECTION_GUIDE.md
```

When moving to PostgreSQL, add Alembic migrations and a database-level overlap constraint for bookings. The service already checks conflicts, but PostgreSQL can enforce it even more strongly.

## 20. Tests

Run:

```bash
pytest -q
```

Current tests:

- Health endpoint works.
- Customer registration and login works.

Important future tests to add:

- Slot generation.
- Booking conflict prevention.
- Customer cancellation.
- Owner booking approval.
- Blocked slot behavior.
- Holiday behavior.

## 21. Common Testing Order In Swagger

Use this order when testing manually:

1. Run seed:

```bash
python -m app.db.seed
```

2. Login as customer:

```txt
POST /api/v1/auth/login
```

3. Click `Authorize` in Swagger and paste:

```txt
Bearer CUSTOMER_TOKEN
```

4. List salons:

```txt
GET /api/v1/salons
```

5. List salon services:

```txt
GET /api/v1/salons/{salon_id}/services
```

6. Get slots:

```txt
POST /api/v1/bookings/slots
```

7. Create booking:

```txt
POST /api/v1/bookings
```

8. Login as owner.

9. Authorize with owner token.

10. List salon bookings:

```txt
GET /api/v1/barber/bookings?salon_id=SALON_ID
```

11. Confirm or reject booking:

```txt
PATCH /api/v1/barber/bookings/{booking_id}/status
```

## 22. Frontend Integration Notes

The customer frontend should store the JWT after login.

Every protected request should send:

```txt
Authorization: Bearer TOKEN
```

Recommended frontend service files:

```txt
authApi.ts
salonApi.ts
bookingApi.ts
notificationApi.ts
profileApi.ts
```

Expected base URL in local development:

```txt
http://127.0.0.1:8000/api/v1
```

For Android emulator, localhost may need:

```txt
http://10.0.2.2:8000/api/v1
```

For a physical phone, use your computer LAN IP.

## 23. What Is Not Done Yet

This backend is a strong working foundation, but these production tasks are still important:

- PostgreSQL migration setup with Alembic.
- Production `.env` setup.
- Refresh tokens.
- Forgot password flow.
- Firebase push sending.
- Admin/super admin panel endpoints.
- Payment gateway integration.
- More tests for bookings and slots.
- Rate limiting.
- Deployment config.
- Real image upload/storage.

## 24. Most Important Files To Understand First

Read in this order:

1. `app/main.py`
2. `app/api/router.py`
3. `app/models/enums.py`
4. `app/models/domain.py`
5. `app/schemas/booking.py`
6. `app/services/slots.py`
7. `app/services/bookings.py`
8. `app/api/routes/bookings.py`
9. `app/api/routes/barber.py`

If you understand these files, you understand the core backend.
