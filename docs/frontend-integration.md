# Frontend integration

Canonical production API origin: `https://api.salones.in` (27 October 2026).
Website server `API_BASE_URL` and both mobile apps' `EXPO_PUBLIC_API_URL` use this
origin without `/v1`; existing adapters supply the versioned path. Swagger is
`https://api.salones.in/docs`. The old hostname remains available for legacy
installed builds. See the [migration receipt](../backend/docs/verification/API_DOMAIN_MIGRATION_2026-10-27.md)
for deployment identities, verification, rollback and mobile-install boundaries.

The new checkout/support contract is documented in
[PRODUCTION_VERIFICATION.md](../backend/docs/PRODUCTION_VERIFICATION.md). Separate clients must
adopt server quote totals, disabled-online-payment state, Pay at Salon instructions, typed
409 errors, `cash|upi_direct` collection and owner access-wall fields. Collection and completion
accept `Idempotency-Key`; booking creation persists replay in Postgres. Existing bookings remain
accessible after subscription/trial expiry. Native/browser verification has outstanding failures;
see [current evidence](../backend/docs/verification/checkout-results.md).

Frontend applications use an environment-specific API base URL and send JSON unless an
endpoint documents multipart upload.

Protected requests include the Supabase access token:

```http
Authorization: Bearer <access-token>
```

The backend verifies the token signature and resolves its `sub` against `profiles`.
Clients must not rely on role claims embedded in the JWT.

Useful entry points:

- `GET /health` for process health
- `GET /health/db` for database health
- `/docs` for the current OpenAPI/Swagger contract
- `/v1/auth/*` for session and actor operations
- `/v1/salons*` and `/v1/availability` for public discovery
- `/v1/bookings*` for authenticated booking operations
- `/v1/walkin/*` for the QR flow

Clients should handle `401`, `403`, `404`, `409`, and validation errors explicitly.
Service responses include nullable `photo_url` and salon-specific category names;
group service cards by the returned names and use the default service image when
the photo is null. See the [service presentation handover](../backend/docs/SERVICE_PRESENTATION.md)
for PATCH semantics, media rules, and the customer parser/rendering changes.
On a booking conflict, refresh availability before asking the user to choose another
slot.

Discovery uses `GET /v1/salons?surface=home` for the home feed and `surface=search`
for search screens. Keep `shuffle_seed` stable across a paginated view. Visibility
and placement are enforced before pagination; do not reorder client-side.
QR websites resolve their route token through `/v1/walkin/{token}?fresh=true`
and use returned salon/staff/services rather than the signed-in owner's salon.
See the [website implementation prompt](../backend/docs/WEBSITE_SUPERADMIN_PROMPT.md).

Never place the Supabase service-role key, database URL, R2 secret, or Firebase service
account in a frontend environment.

## Account deletion contract (customer app, owner app, website)

All three call the same endpoints with the user's bearer token; never send a user id or role.

1. `POST /v1/account/deletion/challenges` `{channel: "email"|"phone", contact?}` -> 202
   `{challenge_id, masked_destination, expires_at, resend_available_at, bookings_to_cancel}`.
   `bookings_to_cancel` is the number of upcoming bookings that confirming an **owner**
   deletion will cancel (always 0 for customers): show it in the warning.
2. `POST /v1/account/deletion/challenges/{challenge_id}/verify` `{code}` -> 200
   `{confirmation_token, expires_at}` (nothing is deleted yet).
3. `POST /v1/account/deletion` `{challenge_id, confirmation_token, confirm: "DELETE"}` -> 202
   `{request_id, status, status_token}`. Show an irreversible-action warning first. Afterwards
   the bearer token is rejected (401): sign the user out locally.
4. `GET /v1/account/deletion/{request_id}` with header `X-Status-Token: <status_token>` -> 200
   `{status: pending|processing|completed|failed, stage: queued|refunding|waiting_for_refunds|
   erasing|completed, requested_at, completed_at}`. `failed` means a retry is scheduled; the
   account stays locked. An owner may sit in `pending` / `waiting_for_refunds` for a while
   (refunds settling) - that is normal, not a failure.

Errors use the standard envelope. Handle `deletion_blocked` (409). **Customers**: tell them
to cancel their upcoming bookings / resolve pending requests (`details.open_bookings`,
`details.pending_requests`). **Owners are no longer blocked by open bookings or requests**
- they are cancelled and refunded by the backend; an owner is blocked only by an active paid
subscription (`details.active_subscriptions`). Also handle `contact_mismatch` (422),
`invalid_verification_code` (400), and 429 (honor `resend_available_at`). Customers whose
booking is cancelled because the salon closed receive a `booking_cancelled` notification
(`data.reason = "salon_closed"`) and the booking has `cancellation_reason = "salon_closed"`.
Details: `backend/docs/ACCOUNT_DELETION.md`.


Prepared locally: category-based staff menus, bulk services and consecutive multi-staff visits
are documented in [the visit contract](../backend/docs/STAFF_SERVICE_VISITS.md). Migration/release approval and native acceptance remain separate.
