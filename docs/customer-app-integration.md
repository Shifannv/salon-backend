# Customer App API Fetch Guide

Use this document in the separate Expo customer-app repository. The app must fetch all
shared salon, booking, profile, and notification data from the FastAPI API; it must not
query the platform Postgres tables directly.

For base URLs, the shared API client, authentication recovery, uploads, errors, and
environment setup, see [frontend-integration.md](./frontend-integration.md).

## Authentication

Supabase Auth owns sign-in and session persistence. After sign-in, send the current
Supabase access token as `Authorization: Bearer <token>` on every protected request.
Fetch `GET /v1/auth/me` once when restoring a session to obtain the database profile and
role. Do not derive or send a role from frontend state.

## What Each Screen Fetches

| Screen or feature | Fetch from the API | When to fetch |
| --- | --- | --- |
| Session bootstrap | `GET /v1/auth/me` | Once after sign-in or session restore |
| Profile | `GET /v1/customer/profile` | On screen entry; refetch after profile/avatar changes |
| Home/discovery | `GET /v1/salons?search=&city=&category=&limit=&offset=` | On first load and when search/filter/page changes |
| Nearby salons | `GET /v1/salons/nearby?latitude=&longitude=&category=&limit=&offset=` | After location permission and coordinates are available |
| Category filters | `GET /v1/catalog/categories` | Cache for the session; refetch on manual refresh |
| Salon detail | `GET /v1/salons/{salon_id}` | On detail-screen entry; response includes gallery images |
| Salon services | `GET /v1/salons/{salon_id}/services` | With salon detail; services are not embedded in salon data |
| Salon staff | `GET /v1/salons/{salon_id}/staff` | Before barber selection; staff are not embedded in salon data |
| Available times | `GET /v1/availability?staff_id=&date=&service_ids=` | Whenever barber, date, or selected services change |
| My bookings | `GET /v1/bookings` | On screen focus and after create/cancel; returns only this customer's bookings |
| Booking detail | `GET /v1/bookings/{booking_id}` | On detail-screen entry or after an appointment notification |
| Notifications | `GET /v1/notifications` | On screen focus and app foreground if a refresh is needed |

Repeat the `service_ids` query parameter for multiple services. Never calculate free
times in the app: render only the slots returned by `/v1/availability`. Salon list
responses do not contain services, and salon detail responses do not contain services
or staff, so the dedicated requests above are required.

## Customer Mutations

| User action | Request | Refresh afterward |
| --- | --- | --- |
| Edit profile | `PATCH /v1/customer/profile` | Replace cached profile with response |
| Upload avatar | `POST /v1/customer/profile/avatar` as multipart form data | Replace cached avatar/profile data; do not send a second profile patch |
| Create booking | `POST /v1/bookings` | Refresh booking list and availability |
| Cancel booking | `POST /v1/bookings/{booking_id}/cancel` | Refresh booking list/detail |
| Report salon | `POST /v1/reports` | Show success state; no salon refetch required |
| Mark notification read | `POST /v1/notifications/{notification_id}/read` | Replace that notification with response |
| Register push token | `POST /v1/devices` | No refetch required |
| Log out/remove push token | `DELETE /v1/devices/{url_encoded_token}` | Clear local session data after the `204` response |

When booking creation returns `409 slot_unavailable`, refetch availability and ask the
customer to choose another returned slot. Use the response's `can_cancel` value to show
or hide cancellation controls.

## Recommended Fetch Order for Booking

1. Fetch salon detail, services, and staff (these may run in parallel).
2. Let the customer select one or more services and a staff member.
3. Fetch availability after the selection and date are known.
4. Submit the exact returned `slot_start` in `POST /v1/bookings`.
5. Refresh bookings and availability after success.

Public salon, catalog, staff, service, and availability reads do not require a token.
Profile, bookings, reports, notifications, and device-token operations do.

