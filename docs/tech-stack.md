# Tech Stack

## Confirmed Stack

| Area | Technology |
| --- | --- |
| Shared API | Python, FastAPI, Pydantic v2 |
| Database access | SQLAlchemy 2.x async, asyncpg |
| Backend/database | Supabase Postgres |
| Authentication provider | Supabase Auth JWTs |
| Migrations | Alembic with raw SQL baseline |
| Media storage | ImageKit or Cloudflare R2, selected by environment |
| Push notifications | Firebase / FCM |
| Project management | Jira |
| Source control | GitHub |

## FastAPI Shared API

Used as the backend for all salon platform clients.

Responsibilities:

- Verify Supabase Auth JWTs
- Resolve actors from `profiles`
- Enforce application-layer authorization
- Expose versioned HTTP APIs
- Call database functions for booking and availability
- Return consistent response and error models

## Supabase

Used for Postgres, Auth, and database-side booking integrity.

Responsibilities:

- Authentication
- Customer profiles
- Salon data
- Service data
- Booking data
- Appointment data
- Notification records
- Device token storage
- Row-level security policies
- Location-based queries
- Database functions such as `create_booking` and `get_available_slots`
- Triggers, audit columns, constraints, and RLS as a second line of defence

## Media Storage

ImageKit and Cloudflare R2 implement the same backend storage gateway. Frontends request
a signed upload URL, upload with `PUT`, and persist the returned public URL. Customer
avatar uploads can also use the authenticated multipart endpoint. Provider secrets stay
in the backend environment.

## Firebase / FCM

Used for push notifications through backend fan-out.

Responsibilities:

- Device push token storage
- Notification permission handling
- Push notification delivery
- Booking confirmation notifications
- Booking cancellation notifications
- Appointment reminder notifications

## GPS / Location Services

Handled by frontend apps, then coordinates are sent to backend APIs.

Responsibilities:

- Ask for location permission
- Get current latitude and longitude
- Handle permission denied state
- Handle unavailable GPS state
- Pass coordinates to salon discovery
- Support nearby salon search

## Frontend Apps

Frontend applications live in separate repositories and consume this shared API.

Examples:

```txt
EXPO_PUBLIC_API_BASE_URL=http://192.168.1.20:8000
EXPO_PUBLIC_API_BASE_URL=https://api.yourdomain.com
```

## GitHub

Used for source control and pull requests.

Main rules:

- Work in feature branches
- Do not commit directly to stable `main`
- Create pull requests for review
- Keep commits focused on one Jira task
