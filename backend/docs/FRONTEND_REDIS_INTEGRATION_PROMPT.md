# Frontend Integration Prompt — Redis Feature Changes

> **Context:** The backend has been updated on branch `thameem/redis-integration` to add
> Redis-backed caching, idempotent booking creation, and OTP rate limiting.
> Most changes are **transparent** (server-side cache) but three features require
> frontend code changes:
>
> 1. `Idempotency-Key` header on booking creation (customer app + walk-in flow)
> 2. HTTP 429 handling for OTP verification (walk-in flow)
> 3. Optional `/health/redis` check (internal / diagnostics)
>
> Backend base URL is configured via the app's environment variable — do **not**
> hard-code URLs in source.

---

## Prompt — Customer App

```
You are working on the customer-facing salon mobile/web app.
The backend API has been updated with Redis caching and idempotent booking
creation. Apply the following changes to the customer app.

────────────────────────────────────────────────────────────────────────────
CHANGE 1 — Idempotency-Key header on POST /v1/bookings
────────────────────────────────────────────────────────────────────────────

Endpoint:  POST /v1/bookings
Auth:      Bearer <Supabase JWT>
New header: Idempotency-Key: <client-generated UUID v4>

WHY: If the user taps "Book" and the network drops, the app may retry the
request. With an idempotency key the server returns the original response
instead of creating a duplicate booking. The key is valid for 60 seconds
server-side; generate a fresh UUID per booking attempt (not per session).

WHAT TO DO:
- Wherever the app calls POST /v1/bookings, generate a UUID v4 before the
  request and attach it as the Idempotency-Key header.
- Store the key in component/page state for the current booking attempt.
- On retry (e.g. network error), reuse the SAME key so the server deduplicates.
- On success or navigation away, discard the key (next booking gets a new one).

EXAMPLE (TypeScript / fetch):
  import { randomUUID } from 'crypto'; // or use the `uuid` npm package

  const idempotencyKey = randomUUID();

  const response = await fetch(`${API_BASE_URL}/v1/bookings`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({
      salon_id: '...',
      staff_id: '...',
      service_ids: ['...'],
      slot_start: '2026-10-15T10:00:00',
      customer_name: 'Jane Doe',   // required field
      notes: '',
    }),
  });

RESPONSE CONTRACT (unchanged):
  201 Created  → BookingResponse object (new booking)
  200 OK       → BookingResponse object (deduplicated — same as original)
  409 Conflict → booking slot taken
  4xx/5xx      → standard error envelope { "error": { "code": "...", "message": "..." } }

No UI change is needed for the 200 deduplication case — treat it the same as
201; show the booking confirmation screen.

────────────────────────────────────────────────────────────────────────────
CHANGE 2 — Catalog & salon data are now server-side cached (no frontend work)
────────────────────────────────────────────────────────────────────────────

The following GET endpoints are now cached server-side for 3–5 minutes:
  GET /v1/catalog/categories
  GET /v1/catalog/categories/{id}/subcategories
  GET /v1/salons/{salon_id}
  GET /v1/salons/{salon_id}/services
  GET /v1/salons/{salon_id}/staff

No frontend changes are required. The server returns the same shape as before.
You may remove any client-side in-memory caching (e.g. useState caching between
screens) for these endpoints if it was added as a workaround for slow responses,
since the server now handles it. Alternatively, keep it — it does no harm.

────────────────────────────────────────────────────────────────────────────
ACCEPTANCE CHECKLIST
────────────────────────────────────────────────────────────────────────────
[ ] POST /v1/bookings always includes the Idempotency-Key header
[ ] The key is a fresh UUID v4 per booking attempt, not per session
[ ] On network-level retry the same key is reused
[ ] 200 and 201 responses from POST /v1/bookings are both treated as success
[ ] No hard-coded API URLs; base URL comes from environment config
```

---

## Prompt — Owner App

```
You are working on the barber/owner salon management app.
The backend API has been updated with Redis caching, cache invalidation, and
idempotent booking creation for the walk-in QR flow. Apply the following
changes to the owner app.

────────────────────────────────────────────────────────────────────────────
CHANGE 1 — Walk-in QR flow: OTP rate limiting (HTTP 429)
────────────────────────────────────────────────────────────────────────────

Endpoint:  POST /v1/walkin/{qr_token}/verify-phone
Auth:      None (public endpoint)

The server now enforces a limit of 5 OTP requests per phone number per minute.
If a customer exceeds this limit the server returns:

  HTTP 429 Too Many Requests
  {
    "error": {
      "code": "too_many_requests",
      "message": "Too many OTP requests. Please wait a minute before trying again."
    }
  }

WHAT TO DO:
- In the walk-in QR phone-verification screen, handle HTTP 429 explicitly.
- Show a user-friendly message: e.g. "Too many attempts. Please wait a minute
  and try again." — do NOT show the raw backend message directly.
- Disable the "Send OTP" / "Resend" button for 60 seconds after a 429 response
  (a countdown timer works well UX-wise).
- Do NOT retry automatically on 429; wait for the user to trigger manually.

EXAMPLE (TypeScript / fetch):
  const res = await fetch(`${API_BASE_URL}/v1/walkin/${qrToken}/verify-phone`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone: '+919876543210' }),
  });

  if (res.status === 429) {
    showError('Too many attempts. Please wait a minute and try again.');
    startResendCooldown(60); // disable button for 60 seconds
    return;
  }
  if (!res.ok) {
    const { error } = await res.json();
    showError(error.message);
    return;
  }
  // OTP sent — show OTP input field

────────────────────────────────────────────────────────────────────────────
CHANGE 2 — Walk-in QR flow: Idempotency-Key header on booking creation
────────────────────────────────────────────────────────────────────────────

Endpoint:  POST /v1/walkin/{qr_token}/bookings
Auth:      Bearer <JWT obtained from verify-phone step>
New header: Idempotency-Key: <client-generated UUID v4>

WHY: Same as the customer app — prevents duplicate walk-in bookings if the
customer's device retries on a flaky connection during the QR scan flow.

WHAT TO DO:
- Generate a UUID v4 when the customer reaches the final "Confirm Booking" step
  of the walk-in QR flow.
- Attach it as the Idempotency-Key header on POST /v1/walkin/{qr_token}/bookings.
- On retry (network error), reuse the same key.
- Treat both 200 and 201 responses as success — show the booking confirmation.

EXAMPLE (TypeScript / fetch):
  import { randomUUID } from 'crypto'; // or use the `uuid` npm package

  const idempotencyKey = randomUUID();

  const response = await fetch(
    `${API_BASE_URL}/v1/walkin/${qrToken}/bookings`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${walkinAccessToken}`,
        'Content-Type': 'application/json',
        'Idempotency-Key': idempotencyKey,
      },
      body: JSON.stringify({
        salon_id: '...',
        staff_id: '...',
        service_ids: ['...'],
        slot_start: '2026-10-15T10:00:00',
        customer_name: 'Jane Doe',   // required field
        notes: '',
      }),
    }
  );

RESPONSE CONTRACT (unchanged):
  201 Created  → BookingResponse object (new booking)
  200 OK       → BookingResponse object (deduplicated — same as original)
  4xx/5xx      → standard error envelope

────────────────────────────────────────────────────────────────────────────
CHANGE 3 — Service / Staff / Salon mutations: cache is auto-invalidated
            (no frontend work required)
────────────────────────────────────────────────────────────────────────────

When the owner creates, updates, or deactivates a service, staff member, or
salon profile, the backend automatically clears the relevant server-side cache.
The next GET call from any client will return fresh data.

No frontend changes needed. You may remove any manual "force refresh" workarounds
that were added because stale data was a problem — the server now handles it.

Affected write endpoints that trigger cache invalidation:
  PATCH  /v1/owner/salon
  POST   /v1/owner/services
  PATCH  /v1/owner/services/{id}
  POST   /v1/owner/services/{id}/deactivate
  POST   /v1/owner/staff
  PATCH  /v1/owner/staff/{id}
  POST   /v1/owner/staff/{id}/deactivate

────────────────────────────────────────────────────────────────────────────
ACCEPTANCE CHECKLIST
────────────────────────────────────────────────────────────────────────────
[ ] POST /v1/walkin/{token}/verify-phone handles HTTP 429 with a friendly UI message
[ ] The OTP "Send/Resend" button is disabled for ~60 s after a 429 response
[ ] POST /v1/walkin/{token}/bookings always includes the Idempotency-Key header
[ ] The key is a fresh UUID v4 per booking attempt
[ ] On network-level retry the same key is reused
[ ] 200 and 201 responses from walk-in booking creation are both treated as success
[ ] No hard-coded API URLs; base URL comes from environment config
```

---

## Error Envelope Reference

All API errors follow a single shape regardless of status code:

```json
{
  "error": {
    "code": "too_many_requests",
    "message": "Human-readable description."
  }
}
```

| HTTP Status | `error.code` | When |
|---|---|---|
| `400` | `bad_request` | Malformed input |
| `401` | `unauthorized` | Missing or invalid JWT |
| `403` | `forbidden` | Authenticated but not allowed |
| `404` | `not_found` | Resource not found |
| `409` | `conflict` | Slot already taken / duplicate |
| `422` | `validation_error` | Request body fails schema validation |
| `429` | `too_many_requests` | Rate limit exceeded |
| `500` | `internal_server_error` | Unexpected server error |

---

## UUID Generation — Language Quick Reference

| Environment | How to generate UUID v4 |
|---|---|
| React Native (JS) | `import 'react-native-get-random-values'; import { v4 as uuidv4 } from 'uuid';` |
| Next.js / Node | `import { randomUUID } from 'crypto'; randomUUID();` |
| Browser (modern) | `crypto.randomUUID()` |
| Swift | `UUID().uuidString` |
| Kotlin/Android | `java.util.UUID.randomUUID().toString()` |

---

_Generated: 2026-10-01 | Backend branch: `thameem/redis-integration` | Commit: `bba6ca6`_
