# API Keys & Frontend Integration Guide

This document covers every environment variable the backend uses, what each one does,
where to get it, and the exact steps to wire all three frontends to the backend.

---

## 1. All Backend Environment Variables

Every variable lives in `backend/.env` (local) or your hosting platform's secret manager (production).

### Core

| Variable | What it does |
|---|---|
| `APP_NAME` | Display name shown in FastAPI `/docs` — cosmetic only |
| `ENVIRONMENT` | `local` skips production validation; set to `production` on the server |

### Database

| Variable | What it does |
|---|---|
| `DATABASE_URL` | Postgres connection string used by SQLAlchemy for all DB reads/writes |
| `DB_POOL_SIZE` | Number of persistent DB connections to keep open (default `5`) |
| `DB_MAX_OVERFLOW` | Extra connections allowed above `DB_POOL_SIZE` under burst load (default `5`) |
| `DB_POOL_TIMEOUT_SECONDS` | Seconds to wait for a free connection before raising an error (default `10`) |

### Supabase Auth (verify JWTs from clients)

| Variable | What it does |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL — used to build OTP and auth REST endpoints |
| `SUPABASE_ANON_KEY` | Public key — sent to Supabase Auth for OTP flows; safe to use server-side |
| `SUPABASE_JWKS_URL` | URL the backend fetches to get Supabase's public signing keys for JWT verification |
| `SUPABASE_JWT_AUDIENCE` | Claim that must be in the JWT — always `authenticated` for Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Admin key — used by super-admin routes to create/ban Supabase Auth users; **never expose to clients** |

### Firebase (push notifications)

| Variable | What it does |
|---|---|
| `FIREBASE_CREDENTIALS_JSON` | Full service account JSON (as a single-line string) — used by FCM to push booking status alerts |

### CORS (who can call the API)

| Variable | What it does |
|---|---|
| `BACKEND_CORS_ORIGINS` | JSON array of allowed origins — any frontend domain not listed here is blocked |

---

## 2. Where to Get Each Key

### Supabase Keys

1. Open [supabase.com](https://supabase.com) → your project
2. Go to **Project Settings** → **API**
3. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon / public** → `SUPABASE_ANON_KEY`
   - **service_role** → `SUPABASE_SERVICE_ROLE_KEY`
4. Build `SUPABASE_JWKS_URL` by appending `/auth/v1/.well-known/jwks.json` to your project URL:
   ```
   https://xxxxxxxxxxxxx.supabase.co/auth/v1/.well-known/jwks.json
   ```
5. Build `DATABASE_URL` from **Project Settings → Database → Connection string → URI** (use the **pooler** URL for production):
   ```
   postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```

### Firebase Key

1. Open [console.firebase.google.com](https://console.firebase.google.com) → your project
2. **Project Settings** → **Service Accounts** → **Generate new private key**
3. Download the `.json` file
4. Convert to a single-line string and paste as `FIREBASE_CREDENTIALS_JSON`:
   ```bash
   # One-liner to flatten the JSON file:
   cat firebase-key.json | tr -d '\n'
   ```

---

## 3. Complete `.env` Template

```bash
# ── Core ─────────────────────────────────────────────────────────────
APP_NAME="Salon Platform API"
ENVIRONMENT=local                      # change to production on the server

# ── Database ─────────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres.[PROJECT_REF]:[DB_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
DB_POOL_TIMEOUT_SECONDS=10

# ── Supabase Auth ─────────────────────────────────────────────────────
SUPABASE_URL=https://[PROJECT_REF].supabase.co
SUPABASE_ANON_KEY=eyJ...              # Project Settings → API → anon key
SUPABASE_JWKS_URL=https://[PROJECT_REF].supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_SERVICE_ROLE_KEY=eyJ...      # Project Settings → API → service_role key

# ── Firebase FCM ─────────────────────────────────────────────────────
FIREBASE_CREDENTIALS_JSON='{"type":"service_account","project_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"firebase-adminsdk-xxx@[project].iam.gserviceaccount.com",...}'

# ── CORS ─────────────────────────────────────────────────────────────
# Local dev:
BACKEND_CORS_ORIGINS=["http://localhost:19006","http://localhost:19000","http://localhost:3000","http://localhost:3001","http://localhost:8081","http://127.0.0.1:8081"]
# Production (replace with real URLs):
# BACKEND_CORS_ORIGINS=["https://walkin.yourdomain.com","https://app.yourdomain.com"]
```

---

## 4. Frontend Connection — Step by Step

### What each frontend needs to connect to the backend

| Frontend | What it needs |
|---|---|
| Customer App (React Native/Expo) | `EXPO_PUBLIC_API_URL` + `EXPO_PUBLIC_SUPABASE_URL` + `EXPO_PUBLIC_SUPABASE_ANON_KEY` |
| Barber/Owner App (React Native/Expo) | Same as Customer App |
| Walk-in Web App (Next.js) | `NEXT_PUBLIC_API_BASE_URL` only — never needs Supabase keys directly |

---

### 4A. Customer App & Barber App (React Native / Expo)

**Step 1** — Create `.env` in the Expo app root (`customer-app/.env` / `barber-app/.env`):

```bash
# The FastAPI backend base URL (no trailing slash)
EXPO_PUBLIC_API_URL=http://localhost:8000

# Supabase — used by the Expo app for Auth client (login, OTP, token refresh)
EXPO_PUBLIC_SUPABASE_URL=https://[PROJECT_REF].supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=eyJ...   # same anon key as backend .env
```

**Step 2** — In the Expo app, use these in your API client:

```typescript
// src/lib/api.ts
const BASE_URL = process.env.EXPO_PUBLIC_API_URL;

export async function apiFetch(path: string, options?: RequestInit) {
  const token = await getSupabaseAccessToken(); // from your Supabase client
  return fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  });
}
```

**Step 3** — Initialize the Supabase client (for Auth only — token management):

```typescript
// src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js';

export const supabase = createClient(
  process.env.EXPO_PUBLIC_SUPABASE_URL!,
  process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY!,
);
```

**Step 4** — For physical device / staging, replace `localhost` with your machine's local IP or the deployed backend URL:

```bash
# Local device testing (replace with your machine's IP)
EXPO_PUBLIC_API_URL=http://192.168.1.XXX:8000

# Staging / production
EXPO_PUBLIC_API_URL=https://api.yourdomain.com
```

---

### 4B. Walk-in Web App (Next.js)

**Step 1** — Create `.env.local` in the Next.js app root:

```bash
# The FastAPI backend base URL (no trailing slash)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Production:
# NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
```

> The walk-in web app **never** uses Supabase keys directly. Phone OTP goes through
> `POST /v1/walkin/{token}/verify-phone` on the backend, which calls Supabase internally.

**Step 2** — Use in your API module:

```typescript
// lib/api.ts
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

// Public (no auth) — QR resolve + OTP
export const api = {
  get: (path: string) => fetch(`${BASE}${path}`).then(r => r.json()),
  post: (path: string, body: unknown, token?: string) =>
    fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    }).then(r => r.json()),
};
```

**Step 3** — Add the Next.js domain to `BACKEND_CORS_ORIGINS` in `backend/.env`:

```bash
BACKEND_CORS_ORIGINS=[..., "http://localhost:3001"]
# Production:
BACKEND_CORS_ORIGINS=[..., "https://walkin.yourdomain.com"]
```

---

## 5. Starting Everything Together (Local Dev)

```bash
# Terminal 1 — Backend
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000

# Terminal 2 — Customer App
cd frontend/salon-customer-app/customer-app
npx expo start

# Terminal 3 — Walk-in Web (when built)
cd walkin-web
npm run dev -- --port 3001
```

Backend API docs available at: `http://localhost:8000/docs`

---

## 6. Integration Prompt

Copy this prompt when asking an AI assistant to connect a new frontend to this backend:

```
I am building a frontend for the Salon Platform API.

The backend is a FastAPI app running at [BACKEND_URL].
Auth is handled by Supabase (project URL: [SUPABASE_URL]).
Clients authenticate by obtaining a JWT from Supabase Auth and sending it as:
  Authorization: Bearer <access_token>

The backend returns errors in this shape:
  { "error": { "code": "not_found" | "unauthorized" | "forbidden" | "conflict" | "validation_error", "message": "..." } }

Key API routes:
  POST   /v1/auth/login                        — email + password login
  POST   /v1/auth/refresh                       — refresh access token
  GET    /v1/auth/me                            — get current user profile

  GET    /v1/salons                             — list public salons (no auth)
  GET    /v1/salons/{id}                        — salon detail (no auth)
  GET    /v1/salons/{id}/services               — salon services (no auth)
  GET    /v1/salons/{id}/staff                  — salon staff (no auth)
  GET    /v1/availability                       — available slots (no auth)

  GET    /v1/bookings                           — list my bookings (auth required)
  POST   /v1/bookings                           — create booking (auth required)
  POST   /v1/bookings/{id}/cancel               — cancel booking (auth required)

  GET    /v1/salons/me                          — owner: get my salon (owner auth)
  PATCH  /v1/salons/me                          — owner: update my salon (owner auth)
  GET    /v1/salons/me/services                 — owner: list services
  POST   /v1/salons/me/services                 — owner: create service
  GET    /v1/salons/me/staff                    — owner: list staff
  POST   /v1/salons/me/staff                    — owner: create staff member

  GET    /v1/walkin/{qr_token}                  — walk-in: resolve QR (public)
  POST   /v1/walkin/{qr_token}/verify-phone     — walk-in: send/verify OTP
  POST   /v1/walkin/{qr_token}/bookings         — walk-in: create booking (phone JWT)

  GET    /v1/notifications                      — list notifications (auth)
  POST   /v1/notifications/{id}/read            — mark read (auth)
  POST   /v1/devices                            — register FCM device token (auth)

All responses are JSON. All authenticated requests require:
  Authorization: Bearer <supabase_access_token>

The Supabase client (for token management only) uses:
  URL:      [SUPABASE_URL]
  anon key: [SUPABASE_ANON_KEY]

Database and all business logic live in the FastAPI backend — never call Supabase directly for data.
```

---

## 7. Security Rules — Do Not Violate

| Rule | Reason |
|---|---|
| `SUPABASE_SERVICE_ROLE_KEY` must **never** reach any client | It bypasses all RLS — full database access |
| `FIREBASE_CREDENTIALS_JSON` must **never** reach any client | Full FCM access — can send push to anyone |
| Clients use `SUPABASE_ANON_KEY` only for Auth token refresh | All data goes through the FastAPI backend |
| Add production domains to `BACKEND_CORS_ORIGINS` before deploy | Prevents unauthorized origins from calling the API |
| Set `ENVIRONMENT=production` on the server | Enables startup validation — catches missing secrets before the first request |
