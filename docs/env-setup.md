# Environment Setup

Do not commit real `.env` files. Values marked `YOUR_...` are secrets or app-specific
values that must be filled locally/deployment-side.

## Backend

File:

```txt
backend/.env
```

```env
APP_NAME="Salon Platform API"
ENVIRONMENT=local
DATABASE_URL=YOUR_BACKEND_DATABASE_URL

SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
SUPABASE_JWKS_URL=https://YOUR_PROJECT_REF.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
FIREBASE_CREDENTIALS_JSON=YOUR_FIREBASE_SERVICE_ACCOUNT_JSON_SINGLE_LINE

BACKEND_CORS_ORIGINS=["http://localhost:19006","http://localhost:19000","http://localhost:3000","http://localhost:3001","http://localhost:8081","http://127.0.0.1:8081","http://localhost:8082"]
WALKIN_BASE_URL=https://salon-customer-qr-webpage.vercel.app/s

DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
DB_POOL_TIMEOUT_SECONDS=10

# Choose r2 (default) or imagekit
STORAGE_PROVIDER=imagekit
PUBLIC_API_BASE_URL=https://apiv1.mudassirmhd.in

# ImageKit
IMAGEKIT_PUBLIC_KEY=YOUR_IMAGEKIT_PUBLIC_KEY
IMAGEKIT_PRIVATE_KEY=YOUR_IMAGEKIT_PRIVATE_KEY
IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/YOUR_IMAGEKIT_ID

# Cloudflare R2 — use these instead when STORAGE_PROVIDER=r2
# Get from Cloudflare Dashboard > R2 > Manage R2 API Tokens.
R2_ACCOUNT_ID=YOUR_CLOUDFLARE_ACCOUNT_ID
R2_ACCESS_KEY_ID=YOUR_R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY=YOUR_R2_SECRET_ACCESS_KEY
R2_BUCKET=salon-images
R2_PUBLIC_URL=https://pub-xxxxxxxxxxxxxxxxxxxx.r2.dev
```

For production, keep the same Supabase values and change:

```env
ENVIRONMENT=production
PORT=8000
DATABASE_URL=YOUR_PRODUCTION_DATABASE_URL
FIREBASE_CREDENTIALS_JSON=YOUR_FIREBASE_SERVICE_ACCOUNT_JSON_SINGLE_LINE
BACKEND_CORS_ORIGINS=["https://YOUR_CUSTOMER_WEB_ORIGIN","https://YOUR_OWNER_WEB_ORIGIN","https://salon-customer-qr-webpage.vercel.app","http://35.254.254.227"]
WALKIN_BASE_URL=https://salon-customer-qr-webpage.vercel.app/s
STORAGE_PROVIDER=imagekit
PUBLIC_API_BASE_URL=https://apiv1.mudassirmhd.in
IMAGEKIT_PUBLIC_KEY=YOUR_IMAGEKIT_PUBLIC_KEY
IMAGEKIT_PRIVATE_KEY=YOUR_IMAGEKIT_PRIVATE_KEY
IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/YOUR_IMAGEKIT_ID
R2_ACCOUNT_ID=YOUR_CLOUDFLARE_ACCOUNT_ID
R2_ACCESS_KEY_ID=YOUR_R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY=YOUR_R2_SECRET_ACCESS_KEY
R2_BUCKET=salon-images
R2_PUBLIC_URL=https://pub-xxxxxxxxxxxxxxxxxxxx.r2.dev
```

## Customer App

File:

```txt
salon-customer-app/customer-app/.env
```

```env
EXPO_PUBLIC_API_URL=https://apiv1.mudassirmhd.in
EXPO_PUBLIC_API_BASE_URL=https://apiv1.mudassirmhd.in

EXPO_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
EXPO_PUBLIC_GOOGLE_AUTH_REDIRECT_URL=salonapp://auth/callback

EXPO_PUBLIC_FIREBASE_API_KEY=YOUR_FIREBASE_WEB_API_KEY
EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN=YOUR_FIREBASE_AUTH_DOMAIN
EXPO_PUBLIC_FIREBASE_PROJECT_ID=YOUR_FIREBASE_PROJECT_ID
EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET=YOUR_FIREBASE_STORAGE_BUCKET
EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=YOUR_FIREBASE_MESSAGING_SENDER_ID
EXPO_PUBLIC_FIREBASE_APP_ID=YOUR_FIREBASE_APP_ID
EXPO_PUBLIC_FIREBASE_MEASUREMENT_ID=YOUR_FIREBASE_MEASUREMENT_ID
```

For local backend on the same laptop, change:

```env
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_API_BASE_URL=http://localhost:8000
```

For a physical phone on the same Wi-Fi, change:

```env
EXPO_PUBLIC_API_URL=http://YOUR_MAC_IP:8000
EXPO_PUBLIC_API_BASE_URL=http://YOUR_MAC_IP:8000
```

## Owner App

File:

```txt
owner-app/.env
```

```env
EXPO_PUBLIC_API_URL=https://apiv1.mudassirmhd.in
EXPO_PUBLIC_API_BASE_URL=https://apiv1.mudassirmhd.in

EXPO_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
```

The owner app Expo scheme must match the redirect:

```txt
salonowner
```

The owner app generates this Google OAuth redirect URI from the Expo scheme:

```txt
salonowner://auth/callback
```

Add that exact URI to Supabase Dashboard -> Authentication -> URL Configuration ->
Redirect URLs. Google OAuth client credentials stay in Supabase, not in the Expo env file.

## Walk-In Web

File:

```txt
walkin-web/.env
```

```env
NEXT_PUBLIC_API_BASE_URL=http://35.254.254.227
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
NEXT_PUBLIC_GOOGLE_AUTH_REDIRECT_URL=https://salon-customer-qr-webpage.vercel.app/auth/callback
```

For local walk-in web, change:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_AUTH_REDIRECT_URL=http://localhost:3000/auth/callback
```

If walk-in web uses phone OTP only, omit:

```env
NEXT_PUBLIC_GOOGLE_AUTH_REDIRECT_URL
```
