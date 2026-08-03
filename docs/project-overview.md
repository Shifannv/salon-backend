# Project Overview

## Project Name

Salon Shared API

## Purpose

This project is the shared FastAPI backend for the salon booking platform.

The backend sits between multiple client applications and Supabase. It owns the shared
business rules that must behave the same way across every app: authentication
verification, application-layer authorization, salon management, service catalog access,
availability, booking workflows, appointment state changes, notifications, and audit
context.

Supabase remains the database, identity provider, storage provider, and source of
database integrity. FastAPI is the shared API layer that all clients call.

```txt
Customer App       ┐
Barber/Owner App   ├─> FastAPI Shared API ─> Supabase Postgres/Auth/Storage
Admin Portal       │
Walk-in QR Web     ┘
```

## Repository Boundary

This repository is backend-only.

Frontend apps live in separate repositories and connect to this API by environment
variable, for example:

```txt
EXPO_PUBLIC_API_BASE_URL=http://YOUR_MAC_IP:8000
EXPO_PUBLIC_API_BASE_URL=https://api.yourdomain.com
```

Do not add frontend app source code to this repository unless the team formally changes
to a monorepo.

## Client Applications

- Customer App: React Native with Expo
- Barber/Owner App: React Native with Expo
- Super Admin Portal: future web app
- Walk-in QR Web: future web app

## Current Backend Status

The active backend currently exposes Phase 1 foundation APIs:

- `GET /health`
- `GET /health/db`
- `POST /v1/auth/login`
- `POST /v1/auth/refresh`
- `GET /v1/auth/me`

Legacy local-password routes and Python booking/slot services still exist in old files
for reference, but they are not mounted by the active FastAPI app.

## Team

| Person | Role |
| --- | --- |
| Shifan | Frontend developer |
| Thameem | Backend developer |

## Main Responsibilities

### Shifan

- Customer and barber frontend app integration
- React Native screens and navigation
- Frontend API client setup
- Frontend loading, empty, error, and success states
- Frontend location and notification permission flows

### Thameem

- FastAPI shared API layer
- Supabase Auth JWT verification
- Application-layer authorization that mirrors RLS policies
- Supabase/Postgres database integration
- Booking and appointment use cases
- Firebase device token storage and notification fan-out support
- Location-based salon query endpoints

## Architecture Principles

The backend follows clean architecture layering:

```txt
api -> application -> domain
infrastructure -> domain/application ports
```

- `api/` handles HTTP schemas, routers, authentication extraction, and dependency wiring.
- `application/` contains use cases and gateway ports.
- `domain/` contains pure Python entities, repository ports, and business rules.
- `infrastructure/` contains SQLAlchemy, Supabase, Firebase, and external adapters.

Authorization belongs in application use cases. Routers should authenticate and delegate.
Repositories should only perform data access.

## Database And Authorization Model

The database schema in `backend/migrations/001_supabase_schema.sql` is the baseline
source of truth.

The schema was designed with Supabase Row Level Security. Because the FastAPI backend
connects with a privileged database role, every RLS policy must be mirrored as an
application-layer authorization check.

Important rules:

- Keep RLS enabled in Supabase.
- Resolve roles from the `profiles` table, not JWT role claims.
- Do not expose raw database errors in HTTP responses.
- Set the Postgres actor context for authenticated requests so audit triggers can stamp
  `created_by` and `updated_by`.

## Booking And Availability Rules

Booking and availability are database-owned workflows.

- Availability must call the Postgres `get_available_slots` function.
- Booking creation must call the Postgres `create_booking` function.
- Python must not compute slots.
- Python must not insert directly into `bookings` or `booking_services`.
- Historical booking service rows are immutable price and duration snapshots.

## MVP Scope

The backend MVP should include:

- Health and database health checks
- Supabase Auth login, refresh, and current profile APIs
- Super admin salon-owner management
- Salon owner profile, staff, service, image, holiday, and settings APIs
- Availability API using the database `get_available_slots` function
- Booking APIs using the database `create_booking` function
- Appointment status and payment APIs
- Walk-in QR APIs
- Notification and device-token APIs
- Backend tests, migrations, deployment, and runbook

## Build Phases

Work should be built one phase at a time:

1. Foundation: health, database health, auth login, refresh, current profile.
2. Super admin: salon-owner creation, salon management, catalog management.
3. Salon owner: profile, images, holidays, services, staff, settings.
4. Booking engine: availability, create booking, list bookings, status changes, payment.
5. Walk-in QR: public QR resolve, phone verification, QR booking.
6. Notifications: devices, notifications, push fan-out.

## Out of Scope for First Version

These can be added later:

- Online payments
- Coupons/offers
- Reviews and ratings submission
- Chat with salon
- Loyalty points
- Multi-language support
