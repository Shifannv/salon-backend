# Frontend Integration Guide

This is the canonical connection guide for every frontend that consumes the Salon
Platform FastAPI backend. Frontend source code stays in its own repository.

## 1. API URLs

| Environment | Base URL |
| --- | --- |
| Production | `https://apiv1.mudassirmhd.in` |
| Same computer / iOS simulator | `http://localhost:8000` |
| Android emulator | `http://10.0.2.2:8000` |
| Physical phone | `http://YOUR_COMPUTER_LAN_IP:8000` |

The backend must run with `--host 0.0.0.0` for a physical phone. Never hard-code a
base URL in a screen or service.

Expo configuration:

```env
EXPO_PUBLIC_API_URL=https://apiv1.mudassirmhd.in
EXPO_PUBLIC_API_BASE_URL=https://apiv1.mudassirmhd.in
EXPO_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
```

`EXPO_PUBLIC_API_URL` is the preferred name. `EXPO_PUBLIC_API_BASE_URL` remains a
supported frontend alias. Restart Expo with `npx expo start --clear` after changing
environment variables.

Walk-in Next.js configuration:

```env
NEXT_PUBLIC_API_BASE_URL=https://apiv1.mudassirmhd.in
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
```

Only the Supabase anonymous key belongs in a frontend. Database URLs, Supabase service
role keys, R2 credentials, and Firebase service-account JSON are
server secrets.

## 2. Backend Deployment Requirements

Before connecting a frontend, the deployed backend must have:

```env
DATABASE_URL=postgresql+asyncpg://...
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
SUPABASE_JWKS_URL=https://YOUR_PROJECT_REF.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
BACKEND_CORS_ORIGINS=["https://YOUR_WEB_APP","http://localhost:8081"]
WALKIN_BASE_URL=https://salon-customer-qr-webpage.vercel.app/s
PUBLIC_API_BASE_URL=https://apiv1.mudassirmhd.in
```

Cloudflare R2 configuration:

```env
R2_ACCOUNT_ID=YOUR_ACCOUNT_ID
R2_ACCESS_KEY_ID=YOUR_ACCESS_KEY
R2_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
R2_BUCKET=salon-images
R2_PUBLIC_URL=https://YOUR_PUBLIC_MEDIA_DOMAIN
```

Run the reviewed migrations before deploying the new API:

```bash
cd backend
alembic upgrade head
```

Migration `0010_salon_reports` creates the table required by `POST /v1/reports`.

## 3. Health Checks

`GET /health` returns:

```json
{ "status": "ok" }
```

`GET /health/db` returns HTTP `200` when ready:

```json
{ "status": "ok", "database": "reachable" }
```

An unavailable database returns HTTP `503`:

```json
{ "error": { "code": "service_unavailable", "message": "Database is unavailable" } }
```

Use `/health` for liveness checks and `/health/db` when database readiness is required.

## 4. Authentication

Supabase Auth owns Google OAuth, phone OTP, session persistence, and refresh tokens.
The frontend signs in through the Supabase SDK. The backend verifies the returned JWT
and resolves the user role from `profiles`; the frontend must never send or trust its own
role value.

Send the Supabase access token on every protected API call:

```http
Authorization: Bearer <supabase_access_token>
```

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/v1/auth/refresh` | Refresh a Supabase session |
| `GET` | `/v1/auth/me` | Get the authenticated profile and database role |
| `POST` | `/v1/auth/owner-access` | Idempotently create/confirm owner access after owner-app sign-in |

The owner app calls `/v1/auth/owner-access` once after successful Supabase sign-in and
before requesting `/v1/salons/me`. A new customer profile becomes an owner; existing
owner, staff, and super-admin roles remain unchanged.

On a `401`, ask Supabase to refresh the session, retry the request once, and return to
login if refresh fails.

## 5. Shared API Client

The client must handle JSON, multipart forms, raw upload bodies, and `204 No Content`.
Do not manually set `Content-Type` for `FormData`; React Native supplies the multipart
boundary.

```ts
const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ??
  process.env.EXPO_PUBLIC_API_BASE_URL;

type ApiErrorBody = {
  error?: { code?: string; message?: string };
  detail?: unknown;
};

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  if (!API_BASE_URL) throw new Error("Missing backend API URL");

  const { data } = await supabase.auth.getSession();
  const isForm = options.body instanceof FormData;
  const headers = new Headers(options.headers);

  if (!isForm && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (data.session?.access_token) {
    headers.set("Authorization", `Bearer ${data.session.access_token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (response.status === 204) return undefined as T;

  const body = (await response.json().catch(() => null)) as ApiErrorBody | T | null;
  if (!response.ok) {
    const error = body as ApiErrorBody | null;
    throw new Error(error?.error?.message ?? `Request failed (${response.status})`);
  }
  return body as T;
}
```

Public endpoints work without a token. Supplying a valid token to a public endpoint is
optional.

## 6. Frontend API Map

For a screen-by-screen fetch plan and mutation/refetch rules, give the frontend teams
the dedicated [customer app guide](./customer-app-integration.md) and
[salon owner app guide](./owner-app-integration.md).

### Customer app

| Area | Endpoints |
| --- | --- |
| Profile | `GET/PATCH /v1/customer/profile`, `POST /v1/customer/profile/avatar` |
| Discovery | `GET /v1/salons`, `/nearby`, `/{salon_id}`, `/{salon_id}/services`, `/{salon_id}/staff` |
| Catalog | `GET /v1/catalog/categories`, `/categories/{category_id}/subcategories` |
| Booking | `GET /v1/availability`, `POST/GET /v1/bookings`, booking detail and cancel |
| Reports | `POST /v1/reports` |
| Notifications | `GET /v1/notifications`, `POST /v1/notifications/{id}/read` |
| Push devices | `POST /v1/devices`, `DELETE /v1/devices/{token}` |

### Owner/barber app

| Area | Endpoints |
| --- | --- |
| Owner access | `POST /v1/auth/owner-access` |
| Salon | `GET/PATCH /v1/salons/me`, complete-profile and settings |
| QR | `GET /v1/salons/me/qr` |
| Gallery | list, upload URL, create, update and soft-delete under `/v1/salons/me/images` |
| Staff | list/create/update/deactivate, photo upload URL, service assignments and languages |
| Services | list/create/update/deactivate under `/v1/salons/me/services` |
| Schedule | holidays and blocked slots under `/v1/salons/me/holidays` and `/blocks` |
| Appointments | list/detail, approve, reject, complete, owner cancel and payment routes |

### Walk-in web

| Method | Path | Auth |
| --- | --- | --- |
| `GET` | `/v1/walkin/{qr_token}` | Public |
| `GET` | `/v1/walkin/{qr_token}/qr?format=png|svg` | Public |
| `POST` | `/v1/walkin/{qr_token}/verify-phone` | Public |
| `GET` | `/v1/availability` | Public |
| `POST` | `/v1/walkin/{qr_token}/bookings` | OTP Supabase JWT |

Swagger at `/docs` and OpenAPI at `/openapi.json` are the complete endpoint and schema
references.

## 7. Customer Avatar Upload

The avatar endpoint accepts `multipart/form-data`, validates the file, uploads it through
the configured provider, updates `profiles.avatar_url`, and returns the public URL.
Accepted formats are JPEG, PNG, and WebP. The maximum size is 5 MB.

```ts
export async function uploadAvatar(uri: string, mime = "image/jpeg") {
  const form = new FormData();
  form.append("image", {
    uri,
    type: mime,
    name: mime === "image/png" ? "avatar.png" : "avatar.jpg",
  } as any);

  return apiRequest<{ avatar_url: string }>("/v1/customer/profile/avatar", {
    method: "POST",
    body: form,
  });
}
```

Do not call `PATCH /v1/customer/profile` again after this succeeds; the avatar URL is
already persisted.

## 8. Owner Gallery and Staff Photo Uploads

Salon gallery images and staff photos upload directly to Cloudflare R2 through a
short-lived presigned URL.

1. Request an upload URL:

```http
POST /v1/salons/me/images/upload-url
Authorization: Bearer <token>
Content-Type: application/json

{ "filename": "cover.jpg", "content_type": "image/jpeg" }
```

For staff photos use `POST /v1/salons/me/staff/{staff_id}/photo-upload-url`.

2. Upload the raw bytes to the returned `upload_url` with the exact same MIME type:

```ts
await fetch(uploadUrl, {
  method: "PUT",
  headers: { "Content-Type": contentType },
  body: imageBlob,
});
```

3. Persist the returned `public_url`:

```http
POST /v1/salons/me/images

{ "url": "<public_url>", "caption": "Front view", "is_main": true, "sort_order": 0 }
```

For staff photos, send `PATCH /v1/salons/me/staff/{staff_id}` with
`{ "photo_url": "<public_url>" }`.

Upload URLs expire after 300 seconds and use R2's S3-compatible API.

## 9. Owner QR Flow

The backend creates the salon's unique `qr_token` once with the salon database row. It
does not generate a new token when the owner app requests the QR. The PNG and SVG can be
rendered repeatedly, but they encode the same permanent `<WALKIN_BASE_URL>/<qr_token>`
identity. Keep `WALKIN_BASE_URL` stable after physical QR codes have been printed.

```http
GET /v1/salons/me/qr
Authorization: Bearer <token>
```

```json
{
  "url": "https://apiv1.mudassirmhd.in/v1/walkin/TOKEN/qr?format=png&scale=12",
  "cached": false
}
```

Display `url` directly in React Native's `Image` component. It is public and does not
need an Authorization header. The generated code opens `WALKIN_BASE_URL/{qr_token}`.
For SVG, request `/v1/salons/me/qr?format=svg`; that response is an SVG document rather
than JSON.

## 10. Availability and Booking

```http
GET /v1/availability?staff_id=STAFF_UUID&date=2026-09-20&service_ids=SERVICE_UUID
```

Repeat `service_ids` for multiple services. Use the returned `slot_start` when creating
the booking. Never calculate availability in the frontend.

```http
POST /v1/bookings
Authorization: Bearer <token>
Content-Type: application/json

{
  "salon_id": "SALON_UUID",
  "staff_id": "STAFF_UUID",
  "service_ids": ["SERVICE_UUID"],
  "start_datetime": "2026-09-20T09:00:00+05:30",
  "customer_name": "Customer Name",
  "customer_phone": "+919876543210",
  "source": "app",
  "notes": null
}
```

HTTP `409` with error code `slot_unavailable` means another request took the slot.
Refresh availability and ask the customer to choose another slot.

Customer cancellation uses `/v1/bookings/{booking_id}/cancel` with optional
`reason_code` and `reason_text`. Owner cancellation uses
`/v1/bookings/{booking_id}/cancel/barber` and requires an owner reason code.

## 11. Salon Reports

```http
POST /v1/reports
Authorization: Bearer <token>
Content-Type: application/json

{
  "salon_id": "SALON_UUID",
  "salon_name": "Optional compatibility value",
  "reason": "Incorrect information",
  "details": "The displayed address is outdated.",
  "created_at": "2026-09-18T10:00:00Z"
}
```

```json
{ "id": "REPORT_UUID", "status": "received" }
```

`salon_name` and `created_at` are accepted for compatibility. The backend validates the
salon, derives the reporter from the JWT, and owns the stored creation time.

## 12. Notifications and Device Tokens

Register an Expo or FCM token after login and whenever it changes:

```http
POST /v1/devices

{ "token": "ExponentPushToken[...]", "platform": "android", "device_name": "Pixel" }
```

Deactivate it on logout with `DELETE /v1/devices/{url_encoded_token}`. Notification
records remain available through `GET /v1/notifications` even if push delivery fails.

## 13. Errors and UI Behavior

Application errors use:

```json
{ "error": { "code": "not_found", "message": "Resource not found" } }
```

| Status | Frontend behavior |
| --- | --- |
| `400` / `422` | Show field or request validation feedback |
| `401` | Refresh once, then return to login |
| `403` | Hide the action or show an access message |
| `404` | Show a resource-not-found state |
| `409 slot_unavailable` | Refresh available slots |
| `503 service_unavailable` | Show a temporary service message and allow retry |

Do not display raw response bodies or database/provider details to users.

## 14. Connection Checklist

- Backend `/health` returns `200`.
- Backend `/health/db` returns `200` before testing data screens.
- `alembic upgrade head` has run on the target database.
- Frontend base URL has no trailing `/v1`; request paths already include `/v1`.
- Supabase frontend and backend settings point to the same project.
- Google OAuth callback URLs match the Expo app schemes.
- Every protected request includes the current Supabase access token.
- Owner app calls `/v1/auth/owner-access` after sign-in.
- `BACKEND_CORS_ORIGINS` includes each deployed web origin exactly.
- `PUBLIC_API_BASE_URL` is the externally reachable API origin.
- `WALKIN_BASE_URL` includes the walk-in route prefix, normally `/s`.
- Cloudflare R2 account, S3 access-key pair, bucket, and public URL are configured.
- Multipart requests do not manually set a boundary.
- Upload `PUT` requests preserve the requested MIME type.

## 15. Future Work

Favorites sync, reviews and ratings, style-photo publishing, coupons, chat, loyalty
points, and analytics are future features. Frontends should keep local behavior or hide
those server-dependent actions until corresponding endpoints and migrations are added.
