# Changelog — Owner App & Backend (2026-08-21)

## Overview

Three major integration areas were wired up in this session:

1. **API URL fix** — the frontend was hitting the wrong base path
2. **QR code** — wired to the real backend endpoint, generated once and cached permanently in Cloudflare R2
3. **Push Notifications** — full Expo + FCM device registration and notification handling

---

## 1. API URL Fix

**Problem**: Every API call returned 404 because the frontend's `EXPO_PUBLIC_API_URL` pointed to `https://apiv1.mudassirmhd.in/` but the backend mounts all routes under `/v1`.

**Fix** — `salon-owner-app/.env`:
```diff
- EXPO_PUBLIC_API_URL=https://apiv1.mudassirmhd.in/
+ EXPO_PUBLIC_API_URL=https://apiv1.mudassirmhd.in/v1
- EXPO_PUBLIC_API_BASE_URL=https://apiv1.mudassirmhd.in/
+ EXPO_PUBLIC_API_BASE_URL=https://apiv1.mudassirmhd.in/v1
```

---

## 2. QR Code — Write-Once Cloudflare R2 Cache

### Architecture

The walk-in QR code encodes:
```
https://salon-customer-qr-webpage.vercel.app/s/<qr_token>
```

`qr_token` is stable — it never changes after salon creation. So the QR PNG only needs to be generated **once** and can be cached permanently.

### Flow

```
GET /v1/salons/me/qr (owner app)
  → check salons.qr_image_url in DB
  ├── if set  → return { url, cached: true }  (instant, no generation)
  └── if null → generate PNG via segno
               → PUT to Cloudflare R2 (qr/<salon_id>/walkin_qr.png)
               → store CDN URL in salons.qr_image_url
               → return { url, cached: false }
```

If R2 is not configured (local dev), falls back to streaming the PNG directly.

### Backend Changes

| File | Change |
|---|---|
| `backend/migrations/versions/0007_salon_qr_image_url.py` | **[NEW]** Adds `qr_image_url TEXT` column to `salons` |
| `backend/app/application/ports/storage_gateway.py` | Added `upload_bytes()` abstract method |
| `backend/app/infrastructure/r2/storage.py` | Implemented `upload_bytes()` via boto3 `put_object` |
| `backend/app/infrastructure/supabase/storage.py` | Implemented `upload_bytes()` + `delete_object()` stubs |
| `backend/app/infrastructure/db/repositories/platform_repository.py` | Added `get_qr_image_url()` and `set_qr_image_url()` |
| `backend/app/api/v1/routes/owner.py` | Rewrote `GET /salons/me/qr` — returns `{ url, cached }` JSON; uploads to R2 on first call |

### Frontend Changes

| File | Change |
|---|---|
| `salon-owner-app/src/api/queryKeys.ts` | Added `salon.qr(salonId)` cache key |
| `salon-owner-app/src/api/repositories/salon.repository.ts` | `fetchQrCode()` — handles new JSON `{ url }` response; falls back to base64 for binary PNG (local dev) |
| `salon-owner-app/src/hooks/useQrCode.ts` | **[NEW]** React Query hook, 24h stale time (qr_token never changes) |
| `salon-owner-app/src/features/dashboard/screens/DashboardScreen.tsx` | `QrCodeModal` now shows real backend QR image; loading/error/retry states; download saves actual PNG |

### Deploy Step Required

Run the migration on the production database:
```bash
cd backend
.venv/bin/alembic upgrade 0007_salon_qr_image_url
```

### Environment Variables

`WALKIN_BASE_URL` must be set in `backend/.env` on the VM:
```
WALKIN_BASE_URL=https://salon-customer-qr-webpage.vercel.app/s
```
This is already documented in `backend/.env.example` and `backend/.env.gcp.example`.

---

## 3. In-App Notifications — FCM/Expo Push

### Problem — 500 on `GET /v1/notifications`

The backend SQL query selects `read_at` (added in migration 0002) but the column doesn't exist on the production database because **migration 0002 has not been applied**.

**Fix — run the migration:**
```bash
cd backend
.venv/bin/alembic upgrade head
```

**Frontend resilience fix** — `salon-owner-app/src/lib/validation/salon-ops.schema.ts`:
```typescript
// Before — hard required, crashes if column missing
read_at: z.string().nullable(),

// After — optional, survives both old and new DB schema
read_at: z.string().nullable().optional(),
```

### Push Delivery Architecture — Two Paths

The backend `FCMGateway` supports two token formats and routes accordingly:

| Token format | Delivery path | Firebase creds needed? |
|---|---|---|
| `ExponentPushToken[...]` | Expo push API (`exp.host`) → APNs/FCM | ❌ No |
| Raw native FCM token | `firebase-admin` SDK → FCM directly | ✅ Yes |

The owner app uses `expo-notifications` which produces `ExponentPushToken[...]` — so **Expo push works today with no Firebase credentials on the server**.

### Device Registration + Push Delivery Flow

```
Sign-in → (tabs)/_layout.tsx mounts usePushNotifications()
  → requestPermissionsAsync()       (iOS prompt / Android 13+)
  → getExpoPushTokenAsync()         → "ExponentPushToken[...]"
  → POST /v1/devices                → upsert into device_tokens table

Owner approves/rejects/cancels/completes booking
  → BookingUseCases._notify_customer()  (BackgroundTask, never blocks HTTP)
      → create row in notifications table
      → FCMGateway.fan_out(notification_id, customer_id)
          → get_active_tokens(customer_id) from device_tokens
          → ExponentPushToken  → POST exp.host/--/api/v2/push/send  ✅
          → raw FCM token      → firebase-admin.send()              ⚠️ needs creds

Foreground notification received → banner shown automatically
Notification tapped with booking_id → router.push('/(tabs)/bookings')
```

### FCM Wiring Status

| Layer | Status | Notes |
|---|---|---|
| `POST /v1/devices` endpoint | ✅ Done | Idempotent upsert on `device_tokens` |
| `expo-notifications` installed | ✅ Done | `npm install expo-notifications` |
| `usePushNotifications` hook | ✅ Done | Mounts in `(tabs)/_layout.tsx` |
| Booking events trigger notifications | ✅ Done | approve / reject / cancel / complete |
| Expo push delivery (ExponentPushToken) | ✅ Works now | No Firebase creds needed |
| Raw FCM delivery | ⚠️ Needs env var | Set `FIREBASE_CREDENTIALS_JSON` on VM |
| Migration 0002 applied | ❌ **Required** | `alembic upgrade head` — fixes 500 on `/notifications` |

### Frontend Changes

| File | Change |
|---|---|
| `salon-owner-app/src/lib/validation/salon-ops.schema.ts` | `read_at` → `.optional()` (survives pre/post migration 0002) |
| `salon-owner-app/src/api/contract.ts` | `ApiNotification.read_at` → `string \| null \| undefined` |
| `salon-owner-app/src/hooks/usePushNotifications.ts` | **[NEW]** Permissions, Expo token, device registration, foreground handler, tap deep-link |
| `salon-owner-app/app/(tabs)/_layout.tsx` | Mounts `usePushNotifications()` once in the authenticated layout |

### Package Added

```bash
npm install expo-notifications --legacy-peer-deps
```

---

## Deploy Checklist

```bash
# 1. SSH into the GCP VM

# 2. Set any missing env vars in backend/.env (see table below)
#    At minimum add FIREBASE_CREDENTIALS_JSON if you want raw FCM delivery.

# 3. Run pending migrations
cd /path/to/backend
.venv/bin/alembic upgrade head   # applies 0002, 0007 (and any others pending)

# 4. Rebuild and restart the API container
bash scripts/gcp-vm-deploy.sh
```

> **Migrations to apply:**
> - `0002_notifications_read_at` — adds `notifications.read_at` column (**fixes 500 on `/notifications`**)
> - `0007_salon_qr_image_url` — adds `salons.qr_image_url` column (enables R2 write-once QR cache)

> **Note:** Expo push (`ExponentPushToken`) works immediately after deploy — no Firebase config needed.
> Raw FCM delivery requires `FIREBASE_CREDENTIALS_JSON` (see table below).

---

## Environment Variables Summary

### Frontend — `salon-owner-app/.env`

| Variable | Value |
|---|---|
| `EXPO_PUBLIC_API_URL` | `https://apiv1.mudassirmhd.in/v1` |
| `EXPO_PUBLIC_API_BASE_URL` | `https://apiv1.mudassirmhd.in/v1` |

### Backend — `backend/.env` on VM

| Variable | Value | Required? |
|---|---|---|
| `WALKIN_BASE_URL` | `https://salon-customer-qr-webpage.vercel.app/s` | ✅ Yes |
| `R2_ACCOUNT_ID` | Cloudflare account ID | ✅ For QR cache |
| `R2_ACCESS_KEY_ID` | R2 API token access key | ✅ For QR cache |
| `R2_SECRET_ACCESS_KEY` | R2 API token secret | ✅ For QR cache |
| `R2_BUCKET` | `salon-images` (or your bucket name) | ✅ For QR cache |
| `R2_PUBLIC_URL` | `https://pub-xxx.r2.dev` | ✅ For QR cache |
| `FIREBASE_CREDENTIALS_JSON` | Service account JSON string from Firebase Console | ⚠️ For raw FCM only |

> **Getting `FIREBASE_CREDENTIALS_JSON`:**
> Firebase Console → Project Settings → Service Accounts → **Generate new private key**
> Copy the downloaded JSON, minify it, and set as a single-line env var:
> ```bash
> FIREBASE_CREDENTIALS_JSON='{"type":"service_account","project_id":"...","private_key":"...","client_email":"..."}'
> ```
> Skip this entirely if all your apps use Expo push tokens — Expo handles FCM/APNs routing for you.
