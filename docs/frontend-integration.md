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

Only Phase 1 backend APIs are currently active:

```txt
GET  /health
GET  /health/db
POST /v1/auth/login
POST /v1/auth/refresh
GET  /v1/auth/me
```

Salon listing, services, bookings, appointments, notifications, and device-token APIs are
not ready yet in the new backend architecture.

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

export function login(email: string, password: string) {
  return apiRequest<TokenResponse>("/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
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

1. User submits email and password.
2. Frontend calls `POST /v1/auth/login`.
3. Frontend stores `access_token` and `refresh_token`.
4. Frontend calls `GET /v1/auth/me` with `Authorization: Bearer <access_token>`.
5. Frontend routes the user based on `profile.role`.

Example:

```ts
const tokens = await login(email, password);
await saveTokens(tokens);

const profile = await getMe(tokens.access_token);

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

- The login email/password must exist in Supabase Auth.
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
