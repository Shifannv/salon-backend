# Frontend Integration Guide

This guide explains how frontend apps connect to the Salon Shared API backend.

Use this for:

- Customer App: React Native with Expo
- Barber/Owner App: React Native with Expo
- Future admin or walk-in web apps

## Backend Base URL

Frontend apps should not hard-code backend URLs inside screens.

Use an environment variable:

```txt
EXPO_PUBLIC_API_BASE_URL=http://YOUR_BACKEND_HOST:8000
```

Local development examples:

```txt
http://localhost:8000          iOS simulator
http://10.0.2.2:8000           Android emulator
http://192.168.1.20:8000       Real phone on same Wi-Fi as backend machine
```

After deployment:

```txt
https://api.yourdomain.com
```

## Start The Backend Locally

From this backend repo:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Check that the backend is running:

```txt
GET http://localhost:8000/health
GET http://localhost:8000/docs
```

## Configure Expo

In the frontend repo, create or update `.env`:

```txt
EXPO_PUBLIC_API_BASE_URL=http://YOUR_MAC_IP:8000
```

Restart Expo after changing `.env`:

```bash
npx expo start --clear
```

## Currently Available APIs

The following backend APIs are currently active:

```txt
GET  /health
GET  /health/db
POST /v1/auth/refresh
GET  /v1/auth/me

GET   /v1/customer/profile
PATCH /v1/customer/profile

GET /v1/salons
GET /v1/salons/nearby
GET /v1/salons/{salon_id}
GET /v1/salons/{salon_id}/services

GET    /v1/salons/me
PATCH  /v1/salons/me
POST   /v1/salons/me/complete-profile
PATCH  /v1/salons/me/settings
GET    /v1/salons/me/images
POST   /v1/salons/me/images
PATCH  /v1/salons/me/images/{image_id}
GET    /v1/salons/me/holidays
POST   /v1/salons/me/holidays
GET    /v1/salons/me/services
POST   /v1/salons/me/services
PATCH  /v1/salons/me/services/{service_id}
DELETE /v1/salons/me/services/{service_id}
GET    /v1/salons/me/staff
POST   /v1/salons/me/staff
PATCH  /v1/salons/me/staff/{staff_id}
DELETE /v1/salons/me/staff/{staff_id}
POST   /v1/salons/me/staff/{staff_id}/services

GET  /v1/availability
POST /v1/bookings
GET  /v1/bookings
GET  /v1/bookings/{booking_id}
POST /v1/bookings/{booking_id}/approve
POST /v1/bookings/{booking_id}/reject
POST /v1/bookings/{booking_id}/complete
POST /v1/bookings/{booking_id}/cancel
POST /v1/bookings/{booking_id}/payment

GET    /v1/notifications
POST   /v1/notifications/{notification_id}/read
POST   /v1/devices
DELETE /v1/devices/{token}
```

Image and holiday delete endpoints are intentionally not available as true deletes until
the schema supports soft delete for those tables.

## API Client Helper

Create a frontend helper such as `src/services/api/client.ts`:

```ts
const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  if (!API_BASE_URL) {
    throw new Error("Missing EXPO_PUBLIC_API_BASE_URL");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(data?.error?.message || "Request failed");
  }

  return data as T;
}
```

## Auth Types

Create types such as `src/services/api/auth.ts`:

```ts
import { apiRequest } from "./client";

export type TokenResponse = {
  access_token: string;
  refresh_token?: string | null;
  token_type: string;
  expires_in?: number | null;
};

export type ProfileResponse = {
  id: string;
  role: "super_admin" | "owner" | "staff" | "customer";
  full_name: string | null;
  email: string | null;
  phone: string | null;
  phone_verified: boolean;
  avatar_url: string | null;
  is_active: boolean;
};

export function signInWithGoogle() {
  return supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: process.env.EXPO_PUBLIC_GOOGLE_AUTH_REDIRECT_URL,
    },
  });
}

export function refreshSession(refreshToken: string) {
  return apiRequest<TokenResponse>("/v1/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export function getMe(accessToken: string) {
  return apiRequest<ProfileResponse>("/v1/auth/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}
```

## Store Tokens Securely

For Expo apps, use Secure Store:

```bash
npx expo install expo-secure-store
```

Example:

```ts
import * as SecureStore from "expo-secure-store";

export async function saveTokens(tokens: {
  access_token: string;
  refresh_token?: string | null;
}) {
  await SecureStore.setItemAsync("access_token", tokens.access_token);

  if (tokens.refresh_token) {
    await SecureStore.setItemAsync("refresh_token", tokens.refresh_token);
  }
}

export async function getAccessToken() {
  return SecureStore.getItemAsync("access_token");
}

export async function getRefreshToken() {
  return SecureStore.getItemAsync("refresh_token");
}

export async function clearTokens() {
  await SecureStore.deleteItemAsync("access_token");
  await SecureStore.deleteItemAsync("refresh_token");
}
```

## Login Flow

Recommended frontend flow:

1. User taps "Continue with Google".
2. Frontend calls Supabase `signInWithOAuth({ provider: "google" })`.
3. Supabase completes Google OAuth and returns a session.
4. Frontend stores or reads `session.access_token` and `session.refresh_token`.
5. Frontend calls `GET /v1/auth/me` with `Authorization: Bearer <access_token>`.
6. Frontend routes the user based on `profile.role`.

Example:

```ts
await signInWithGoogle();

const { data } = await supabase.auth.getSession();
const session = data.session;

if (!session) {
  throw new Error("Google sign-in did not return a Supabase session");
}

const profile = await getMe(session.access_token);

if (profile.role === "customer") {
  // Navigate to customer app home.
}

if (profile.role === "owner" || profile.role === "staff") {
  // Navigate to barber/owner app home.
}
```

## Token Refresh Flow

When an authenticated request fails with `401`:

1. Read `refresh_token` from Secure Store.
2. Call `POST /v1/auth/refresh`.
3. Save the new tokens.
4. Retry the original request once.
5. If refresh also fails, clear tokens and send the user to login.

## Important Supabase Requirement

The backend uses Supabase Auth.

That means:

- Google OAuth must be enabled in the Supabase project.
- The frontend signs in with Supabase `signInWithOAuth({ provider: "google" })`.
- The Supabase Auth user id must have a matching row in the `profiles` table.
- The frontend should not send or trust a role manually.
- The backend resolves the role from `profiles`.

## CORS Requirement

The backend `.env` must allow the frontend origin.

Backend example:

```txt
BACKEND_CORS_ORIGINS=["http://localhost:19006","http://localhost:3000"]
```

For Expo on a real device, CORS is usually less visible than in browsers, but keep the
allowed origins correct for web builds and admin portals.

## Common Problems

### Network request failed

Usually the phone cannot reach the backend.

Check:

- Backend is running with `--host 0.0.0.0`.
- Frontend uses the computer LAN IP, not `localhost`, on a real phone.
- Phone and computer are on the same Wi-Fi.
- Firewall allows port `8000`.

### Login returns invalid credentials

Check:

- User exists in Supabase Auth.
- Password is correct.
- Backend `SUPABASE_URL` and `SUPABASE_ANON_KEY` are correct.

### `/v1/auth/me` returns unauthorized

Check:

- `Authorization` header is exactly `Bearer <access_token>`.
- Backend `SUPABASE_JWKS_URL` is correct.
- The Supabase Auth user id exists in the `profiles` table.
- The profile has `is_active = true`.

### Other screens have no data

Expected for now.

Only health and auth APIs are complete in the active backend. Salon, service, booking,
appointment, and notification APIs will be connected after their backend phases are
implemented.
