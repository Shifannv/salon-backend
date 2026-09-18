# Salon Owner App API Fetch Guide

Use this document in the separate Expo salon owner/barber app repository. The app must
fetch and mutate salon operations through the FastAPI API; it must not query platform
Postgres tables directly.

For base URLs, the shared API client, authentication recovery, R2 uploads, errors, and
environment setup, see [frontend-integration.md](./frontend-integration.md).

## Authentication and Startup

Supabase Auth owns sign-in. After a successful sign-in or restored session:

1. Send the Supabase access token as `Authorization: Bearer <token>`.
2. Call `POST /v1/auth/owner-access` once. This idempotently confirms owner access.
3. Call `GET /v1/salons/me` to load the owner's salon and onboarding state.
4. Route to onboarding when `profile_completed` is false; otherwise open the owner app.

Do not trust a role stored by the frontend. `GET /v1/auth/me` or the owner-access
response provides the backend-resolved database role.

## What Each Screen Fetches

| Screen or feature | Fetch from the API | When to fetch |
| --- | --- | --- |
| App bootstrap/onboarding | `GET /v1/salons/me` | After owner access and on app refresh |
| Salon profile/settings | `GET /v1/salons/me` | On screen entry; the response includes current images and settings |
| Gallery manager | `GET /v1/salons/me/images` | On screen entry and after upload/update/delete |
| Walk-in QR | `GET /v1/salons/me/qr` | On screen entry; display the returned PNG URL |
| Service manager | `GET /v1/salons/me/services` | On screen entry and after service changes |
| Category picker | `GET /v1/catalog/categories` | Cache for the session |
| Subcategory picker | `GET /v1/catalog/categories/{category_id}/subcategories` | When the selected category changes |
| Staff manager | `GET /v1/salons/me/staff` | On screen entry and after staff changes |
| Staff assignments | `GET /v1/salons/me/staff/{staff_id}/services` | When opening a staff member |
| Assignment languages | `GET /v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages` | When editing an assignment |
| Holidays | `GET /v1/salons/me/holidays` | On schedule-screen entry and after adding a holiday |
| Blocked time | `GET /v1/salons/me/blocks` | On schedule-screen entry and after create/delete |
| Appointments | `GET /v1/bookings` | On screen focus and after every appointment action; returns this salon's bookings |
| Appointment detail | `GET /v1/bookings/{booking_id}` | On detail-screen entry or after a notification |
| Notifications | `GET /v1/notifications` | On screen focus and app foreground if refresh is needed |

## Owner Mutations

| User action | Request | Refresh afterward |
| --- | --- | --- |
| Complete onboarding | `POST /v1/salons/me/complete-profile` | Replace cached salon with response |
| Edit salon | `PATCH /v1/salons/me` | Replace cached salon with response |
| Change approval/hours | `PATCH /v1/salons/me/settings` | Replace cached salon with response |
| Add/edit/remove gallery image | `POST/PATCH/DELETE /v1/salons/me/images...` | Refresh gallery and salon profile |
| Add/edit/deactivate service | `POST/PATCH/DELETE /v1/salons/me/services...` | Refresh services |
| Add/edit/deactivate staff | `POST/PATCH/DELETE /v1/salons/me/staff...` | Refresh staff |
| Assign service to staff | `POST /v1/salons/me/staff/{staff_id}/services` | Refresh that staff member's assignments |
| Replace assignment languages | `PUT /v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages` | Replace cached languages with response |
| Add holiday | `POST /v1/salons/me/holidays` | Refresh holidays |
| Create/remove blocked time | `POST/DELETE /v1/salons/me/blocks...` | Refresh blocks and any visible availability |
| Approve/reject/complete booking | `POST /v1/bookings/{id}/approve`, `/reject`, or `/complete` | Refresh appointment list/detail |
| Cancel as salon | `POST /v1/bookings/{id}/cancel/barber` | Refresh appointment list/detail |
| Record payment | `POST /v1/bookings/{id}/payment` | Refresh appointment list/detail |

Deleting services and staff deactivates them; it does not remove historical platform
data. Holiday deletion currently returns `501 Not Implemented`, so do not expose a
working delete-holiday control until a backend migration and endpoint support it.

## Image Uploads

For gallery images, request `POST /v1/salons/me/images/upload-url`. For staff photos,
request `POST /v1/salons/me/staff/{staff_id}/photo-upload-url`. Then:

1. `PUT` the raw image bytes to `upload_url` using the exact requested content type.
2. Save `public_url` with `POST /v1/salons/me/images` or
   `PATCH /v1/salons/me/staff/{staff_id}`.
3. Refetch the affected gallery or staff record.

## Appointment Rules

The backend scopes `GET /v1/bookings` by the authenticated owner and salon. Do not send
a salon ID to broaden this query. Manual-approval salons may approve or reject pending
bookings. Owner cancellation must use `/cancel/barber` and requires a valid
`reason_code`; customer cancellation uses a different route and reason set.

