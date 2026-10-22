# Frontend update lists

| | |
|---|---|
| **Date** | 2026-10-22 |
| **Backend commit** | `97e69a2` plus uncommitted work on branch `shifan` |
| **Evidence** | [frontend-api-usage-2026-10-22.md](frontend-api-usage-2026-10-22.md) and the [static audit](FULL_API_ARCHITECTURE_AUDIT_2026-10-21.md) |
| **Rule** | The backend team has not changed any frontend code. Each team applies its own list. |

Paths are relative to each repository. Line numbers were read on 2026-10-22; check them if the file has moved on.

Priority: **P1** do before real-API testing, **P2** do before launch, **P3** when convenient.

## 1. Customer app (`Salon-Customer-APP/customer-app`)

| # | Pri | Change | Why | Evidence |
|---|---|---|---|---|
| C1 | P1 | Stop calling `GET /v1/salons/{id}/payment-options`. | The route does not exist (404). The app calls it on every booking-confirm screen and silently falls back to Pay at Salon. | `src/server-state/payments.ts:82`; used by `src/screens/booking/BookingConfirmScreen.tsx:32` |
| C2 | P2 | When you build online checkout, read the fields the salon responses already carry, and rewrite `parsePaymentOptions` to match. Shipped shape: `accepts_bookings`, `payment_options` (list of `PAY_AT_SALON` / `PAY_ONLINE`), `online_payment_available`, `online_payment_unavailable_reason`. Your parser expects `pay_online` and `pay_at_salon` objects instead. | The backend never returns your parser's shape. | `src/server-state/payments.ts:39-52`; backend `app/api/v1/schemas/platform.py:101-119` |
| C3 | P1 | Hide the cancellation-fee preview, or mock it, until the backend builds it. | `GET /v1/bookings/{id}/cancellation-quote` does not exist. The cancellation bands are approved but not built. | `src/services/supabase/booking.service.ts:183` |
| C4 | P2 | Account deletion: show the `deletion_blocked` message and the `open_bookings` / `pending_requests` counts from `error.details`. A customer who is **checked in** is now blocked too. | Matches the decision that a customer with a current, future or pending booking cannot delete. | `src/services/api/accountDeletion.service.ts:111` already maps 409 to `blocked`; confirm the screen shows the counts |
| C5 | P3 | Optional: `POST /v1/auth/forgot-password` and `/auth/refresh` exist but you use the Supabase SDK. No action unless you want server-side throttled reset. | Information. | |

**Keep calling (other clients' duplicates are not yours to remove):** `GET` and `PATCH /v1/customer/profile` (`src/services/supabase/profile.service.ts:40`, `:49`), `POST /v1/customer/profile/avatar` (`:75`), `GET /v1/salons` and `/v1/salons/nearby` (`salon.service.ts:137`, `:166`).

**No change needed for the booking-error fix.** Real conflicts keep their `slot_unavailable` and `salon_not_accepting_bookings` codes. A genuine outage now returns 500 instead of a false 409, and your client already shows a safe message for any status of 500 or above (`src/services/api/apiClient.ts:199-202`).

## 2. Owner app (`salon-owner-APP`)

| # | Pri | Change | Why | Evidence |
|---|---|---|---|---|
| O1 | P1 | Hide or mock these features until the backend builds them; each call returns 404 today. | The routes are in `MARKETPLACE_CONTRACT.md`, which is forward design and not a shipped contract. | see the next table |
| O2 | P1 | Add explicit 404 handling to the calls that have none: alert settings and the two notification acknowledgements. | They currently surface a raw error. The commission, ledger and slot-filler repositories already resolve a 404 to "not deployed yet". | `src/api/repositories/alert-settings.repository.ts:29`; `notification-ack.repository.ts:15`, `:23` |
| O3 | P2 | Optional: add check-in and no-show actions. | The backend supports `POST /v1/bookings/{id}/check-in` and `/no-show`; no screen calls them. | usage document §5 |
| O4 | P2 | Waitlist: when the review thread is built, show the open change requests from `GET /v1/salons/me/reviews` and poll `open_review_count`. | Design only for now. | [.plans/salon-review-thread-spec.md](../../../.plans/salon-review-thread-spec.md) |
| O5 | P3 | When the backend adds `PATCH /v1/salons/me/payout-account`, switch from `PUT`. | `PUT` has merge (PATCH) semantics. Keep `PUT` until then. | `src/api/repositories/payout.repository.ts:30` |

Routes that return 404 today:

| Feature | Route | File |
|---|---|---|
| Alert settings | `GET` / `PATCH /v1/salons/me/alert-settings` | `src/api/repositories/alert-settings.repository.ts:29` |
| Commission rules | `GET` / `POST /v1/salons/me/commission-rules` | `commission-rules.repository.ts:35`, `:44` |
| Daily ledger | `GET /v1/salons/me/ledger/daily` | `ledger.repository.ts:62` |
| Slot filler | `/v1/salons/me/slot-filler-rules` and `/{id}` | `slot-filler.repository.ts:39`, `:61` |
| Delivery acknowledgement | `POST /v1/notifications/{id}/delivered` | `notification-ack.repository.ts:15` |
| Session start | `POST /v1/auth/session-started` | `notification-ack.repository.ts:23` |

**Keep calling:** `PATCH /v1/profiles/me` (`src/api/repositories/auth.repository.ts:187`) and the signed avatar upload `POST /v1/profiles/me/avatar-upload-url` (`src/api/image-storage.ts:38`). You are the only caller of both.

**Not verified:** the default of `EXPO_PUBLIC_USE_MOCK_API` (`src/mocks/server.ts:14`). It is set in environment files, which the backend team did not read. Confirm it is `false` for real-API builds.

## 3. Website (`salon-QR-Walking-Web/walking-customer-web`)

The website must run the same customer and owner workflows as the apps, on the same APIs.

| # | Pri | Surface | Change | Evidence |
|---|---|---|---|---|
| W1 | P1 | Owner workspace | Build it. Today the website calls **no** owner route. Backend routes already exist: `POST /v1/auth/owner-access`, `GET`/`PATCH /v1/salons/me`, `POST /v1/salons/me/complete-profile`, `GET /v1/salons/me/setup-status`, then every `/v1/salons/me/*` route (images, services, staff, holidays, blocks, payout, subscription, bookings). | usage document §6 |
| W2 | P1 | Owner waitlist | Show `approval_status` and `rejection_reason` from `GET /v1/salons/me`, and the decision notification from `GET /v1/notifications`. Poll; there is no push to the web yet. | `backend/docs/SALON_APPROVAL.md` |
| W3 | P2 | Customer account | Add profile view and edit (`GET`/`PATCH /v1/profiles/me`; or the customer routes the app uses), notifications (`GET /v1/notifications`, `POST …/{id}/read`, `POST …/read-all`) and device registration if web push is wanted. Today only bookings and account deletion are wired. | usage document §6 |
| W4 | P2 | Account deletion | Show the `deletion_blocked` message and counts, as for the customer app (C4). | `lib/api/` account deletion calls |
| W5 | P2 | Super-admin | Add a deleted-salon review screen: the queue `GET /v1/admin/deleted-salons` and the statement `GET /v1/admin/deleted-salons/{salon_id}/statement`. Money totals per month and currency, including the platform fee and the salon's total. | backend `app/api/v1/routes/account_deletion.py` |
| W6 | P3 | Super-admin | After the review thread is built, add the review screen (requests with an optional section, send, resolve, withdraw). | review thread spec |
| W7 | P3 | Super-admin | `GET /v1/admin/catalog/languages` has no caller; no action. | usage document §4 |

**Already wired and correct:** public discovery and QR booking (8 routes), the 26 `/v1/admin/*` routes, and bookings and account deletion for customers.

**Keep calling:** both forms of the admin deactivate (`POST …/deactivate` and `PATCH` with `is_active`) while they coexist (`lib/api/admin.ts:39`, `:54-55`, `:61`).

**Constraint (already recorded):** an account whose role is `owner` cannot complete the QR customer booking. Use a separate customer account for the QR flow (`docs/FRONTEND_INTEGRATION_PROMPTS.md`).

## 4. Changes coming from the backend

None of these needs a client change before it ships; each adds to the API.

| Change | Status | What clients will see |
|---|---|---|
| Booking errors: outages return 500, not 409 | Done in the working tree, not committed | Only genuine failures change |
| `checked_in` blocks customer account deletion | Done, not committed | Same `deletion_blocked` response, more cases |
| Closed-salon statement endpoints | Done, not committed | New super-admin routes |
| Reviewed financial purge of closed salons | Design only | Nothing until built |
| Review thread | Design only | New routes and one added field, `open_review_count` |
| `PATCH /v1/salons/me/payout-account` | Proposed | A new alias; `PUT` stays |
| Removal of `GET /v1/profiles/me` and `GET /v1/admin/catalog/languages` | Candidates; no caller found | Announced first; removed only after server logs show no calls |
