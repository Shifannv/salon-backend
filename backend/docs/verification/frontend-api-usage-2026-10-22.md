# Frontend API usage matrix

| | |
|---|---|
| **Date** | 2026-10-22 |
| **Backend commit** | `97e69a2` (branch `shifan`) |
| **Clients scanned** | `Salon-Customer-APP/customer-app`, `salon-owner-APP`, `salon-QR-Walking-Web/walking-customer-web` |
| **Mode** | Static and read-only. No frontend or backend file was changed. No client was run. |
| **Related** | [Static API and architecture audit](FULL_API_ARCHITECTURE_AUDIT_2026-10-21.md), §6.1 and DOC-06 |

## 1. Summary

This scan shows which backend routes each of the three frontends calls in its source code. It answers two questions from the audit: which duplicate endpoints can be removed, and how integrated each client is.

- **104 of 140 backend routes are called by at least one client.** Customer app: 28. Owner app: 61. Website: 44.
- **9 client calls point at routes that do not exist in the backend.** The owner app calls 7 and the customer app calls 2. Every one of them is a route described in `backend/docs/MARKETPLACE_CONTRACT.md` but never built. These calls fail with 404 against the real backend. This is the most important result of the scan (§3).
- **No duplicate endpoint can be removed yet without changing a client first.** Both sides of most duplicate pairs are in use. Three routes have no caller at all and are the only clean removal candidates (§4).
- **The website does not call any owner-workspace route.** It covers public discovery, QR booking and part of the customer account (§6). The owner flow on the website is not built yet. The backend APIs it needs already exist.
- **Integration is mixed, as the audit states.** The owner app and the website both have a mock mode. The website refuses mock mode in production.

## 2. Method and limits

1. Every `.ts`, `.tsx`, `.js` and `.jsx` file was read. These were excluded: `node_modules`, build output, tests, end-to-end scripts, mock folders, and generated OpenAPI type files (`openapi.generated.ts`, `src/api/generated/`, `schema.d.ts`). Type files list every backend path, so counting them would hide real usage.
2. A path counts as a call when it appears in a call such as `apiGet('/v1/...')` or `apiClient().post('/salons/me/images')`, or as a literal next to one. Each client's base prefix was applied:
   - the customer app writes `/v1/...` in full;
   - the owner app's client appends `/v1` (`src/api/client.ts:26`);
   - the website's super-admin helper uses a `/v1/admin` base (`lib/api/admin.ts:9`);
   - the website's two proxies forward `/api/public/v1/...` and `/api/admin/proxy/...` to `/v1/...`.
3. Dynamic segments such as `${id}` were normalised to `{}`, appended query strings were removed, and each call was matched to the 140-route inventory. Where the HTTP method was visible it was matched too.
4. Ten random matrix rows were checked by hand against the cited source line. All ten were correct.

**Limits.** This is source-level evidence, not runtime evidence.

- A call that builds its path in a way the scan cannot read is missed. This would make a route look unused when it is not. The scan was refined twice to catch multi-line calls, and the known misses were fixed.
- A call inside code that never runs (a dead screen, or a mock-only branch) still counts as a call.
- Routes reached through a URL the backend returns, rather than a path in client code, show as uncalled. §5 lists them separately.

## 3. Client calls to routes that do not exist

These calls return 404 from the real backend. Each matches an unbuilt section of `backend/docs/MARKETPLACE_CONTRACT.md`. This confirms audit finding DOC-06: client teams built against a forward-design document as if it were the shipped contract.

| Client | Called path | Source | Handles a 404? | What the backend has instead |
|---|---|---|---|---|
| Customer app | `GET /v1/salons/{id}/payment-options` | `src/server-state/payments.ts:82` | Falls back to "Pay at Salon only" on any error (`:77`). Online payment is intentionally off in the app today (`ONLINE_PAYMENT_FLOW_IMPLEMENTED = false`, `payments.ts:12`), so the 404 does no harm yet, but it wastes one failed request on every booking-confirm screen (`BookingConfirmScreen.tsx:32`). | Nothing at this path. Each salon response already carries a `payment_options` block (`backend/app/api/v1/schemas/platform.py:101-119`). The client should read that field. Its shape differs from what the app's parser expects: the backend ships `payment_options: ["PAY_AT_SALON" | "PAY_ONLINE"]`, `online_payment_available` and `online_payment_unavailable_reason`, while `parsePaymentOptions` (`payments.ts:39-52`) expects `pay_online` and `pay_at_salon` objects. |
| Customer app | `GET /v1/bookings/{id}/cancellation-quote` | `src/services/supabase/booking.service.ts:183` | No explicit handling | Not built (cancellation bands are approved but not built; `docs/agent-memory/shared/roadmap.md`) |
| Owner app | `GET`/`PATCH /v1/salons/me/alert-settings` | `src/api/repositories/alert-settings.repository.ts:29` | No explicit handling | Not built |
| Owner app | `GET`/`POST /v1/salons/me/commission-rules` | `src/api/repositories/commission-rules.repository.ts:35`, `:44` | Yes: resolves `null` ("not deployed yet", `:31`) | Not built |
| Owner app | `GET /v1/salons/me/ledger/daily` | `src/api/repositories/ledger.repository.ts:62` | Yes | Not built |
| Owner app | `/v1/salons/me/slot-filler-rules` and `/{id}` | `src/api/repositories/slot-filler.repository.ts:39`, `:61` | Yes | Not built |
| Owner app | `POST /v1/notifications/{id}/delivered` | `src/api/repositories/notification-ack.repository.ts:15` | No explicit handling | Not built |
| Owner app | `POST /v1/auth/session-started` | `src/api/repositories/notification-ack.repository.ts:23` | No explicit handling | Not built |

**Action for each client team.** Hide these features, or keep them on mock data, until the backend routes exist. For the customer app's `payment-options` call, switch to the `payment_options` field that is already shipped. That needs no backend change.

**Action for the backend.** Mark each unbuilt section of `MARKETPLACE_CONTRACT.md` as "not built", per audit DOC-06.

## 4. Duplicate endpoints: who calls each side

C = customer app, O = owner app, W = website, `-` = no caller.

| Route | Callers | Evidence |
|---|---|---|
| `GET /v1/auth/me` | C, O, W | `customer-app/src/services/api/accountDeletion.service.ts:88`; `salon-owner-APP/src/api/repositories/account.repository.ts:91` |
| `GET /v1/profiles/me` | **-** | none |
| `GET /v1/customer/profile` | C | `src/services/supabase/profile.service.ts:40` |
| `PATCH /v1/profiles/me` | O | `src/api/repositories/auth.repository.ts:187` |
| `PATCH /v1/customer/profile` | C | `src/services/supabase/profile.service.ts:49` |
| `POST /v1/profiles/me/avatar-upload-url` (signed upload) | O | `src/api/image-storage.ts` |
| `POST /v1/customer/profile/avatar` (multipart upload) | C | `src/services/supabase/profile.service.ts:75` |
| `GET /v1/salons` | C, W | `customer-app/src/services/supabase/salon.service.ts:137`; `walking-customer-web/lib/api/public.ts:32` |
| `GET /v1/salons/nearby` | C, W | `customer-app/src/services/supabase/salon.service.ts:166`; `walking-customer-web/lib/api/public.ts:47` |
| `PUT /v1/salons/me/payout-account` | O | `src/api/repositories/payout.repository.ts:30` |
| Admin `POST …/deactivate` and `PATCH` with `is_active` (categories, subcategories, plans) | W uses both forms | `lib/api/admin.ts:39`, `:54-55`, `:61` |
| `GET /v1/admin/catalog/languages` | **-** | none |

**What this changes in the audit's §6.1 recommendation**

- The audit proposed keeping `/v1/profiles/me` and deprecating `/v1/customer/profile`. The evidence points the other way for reads: `GET /v1/profiles/me` has **no** caller, while the customer app relies on `GET /v1/customer/profile`.
- Each client uses a different pair for updates and avatars: the customer app uses `/customer/profile` with multipart upload, and the owner app uses `/profiles/me` with signed upload. **Both pairs must stay** until one client migrates.
- **Clean removal candidates (no caller):** `GET /v1/profiles/me` and `GET /v1/admin/catalog/languages`. Remove each in its own pull request, after a deprecation note and a check of server logs, because a client not scanned here (an old app build still installed on phones) could still call them.
- **Everything else in §6.1 stays for now.** `GET /v1/salons/nearby` and the admin deactivate commands are in active use.

## 5. Routes no client calls

| Group | Routes | Why no client calls them |
|---|---|---|
| Reached through a returned URL | `PUT /v1/media/uploads/{token}`, `GET /v1/media/results/{token}`, `GET /v1/walkin/{qr_token}/qr` | Clients use the `upload_url`/`result_url` the backend returns (`salon-owner-APP/src/api/image-storage.ts`), and the QR image URL comes from `GET /v1/salons/me/qr`. **In use; not removable.** |
| Online payments | `/v1/bookings/{id}/payments`, `…/intent`, `/confirm`, `/refresh`, `/cancel`, `…/refund`; `/v1/salons/me/earnings`, `/settlement-account`, `…/register`, `/payout-account/history` | Dormant by design until a payment provider is configured (`docs/agent-memory/shared/roadmap.md`) |
| Subscription purchase | `/v1/subscription-plans`, `/v1/subscriptions/config`, `/v1/salons/me/subscription/checkout`, `/verify`, `/cancel`, `/payments` | Website-only purchase by design (`backend/docs/SUBSCRIPTIONS.md`); not yet built in the website |
| Booking lifecycle | `POST /v1/bookings/{id}/check-in`, `/no-show`, `POST /v1/bookings/quote` | No client uses the check-in and no-show states added in migration 0034. This is worth raising with the owner-app team: the backend supports these states, but no screen uses them. |
| Support and email | `/v1/support/tickets`, `…/{id}`, `…/{id}/reply`, `GET /v1/email/events/{id}` | No client UI yet |
| Auth helpers | `POST /v1/auth/refresh`, `POST /v1/auth/forgot-password` | Clients use the Supabase SDK directly (`salon-owner-APP/src/api/client.ts:71`) |
| Owner edits | `PATCH /v1/salons/me/images/{id}` | No client edits an image after upload |
| Duplicates | `GET /v1/profiles/me`, `GET /v1/admin/catalog/languages` | See §4 |
| Platform | `POST /v1/webhooks/{provider}`, `/health*` | Called by providers and infrastructure, not by clients |

**No route in this table should be removed because of this scan.** Being uncalled today is not the same as unused: most of these routes are dormant by design, or waiting for a client screen.

## 6. Website coverage against the required surfaces

The website must run the full customer flow and the full owner flow on the same APIs as the apps (owner decision, 2026-10-22).

| Website surface | Routes it calls today | Missing in the website |
|---|---|---|
| Public discovery and QR | 8: salons, nearby, salon detail, services, staff, availability, walk-in resolve, verify-phone | none |
| Customer account | 10: `GET /v1/auth/me`; booking create, list, detail and cancel; QR booking; the four account-deletion routes | Profile view and edit, notifications, device registration |
| Owner workspace | **0** | The whole owner flow: owner access, onboarding, setup status, the approval waitlist, and every `/v1/salons/me/*` route. The backend routes exist; this is website work. |
| Super-admin | 26 `/v1/admin/*` routes | none found |

## 7. Input to ERR-02 (booking errors)

ERR-02 changes booking creation so that a genuine server failure returns 500 instead of 409. The clients already handle a 500 safely:

- **Customer app:** any status of 500 or above gets a generic safe message (`src/services/api/apiClient.ts:199-202`), separate from `slot_unavailable` (`src/utils/customerError.ts:9`).
- **Owner app:** the walk-in flow only special-cases a slot conflict or a 409 (`src/hooks/useWalkin.ts:95`). Other errors use the normal error path.
- **Website:** booking calls go through the server-side proxy, which maps upstream failures to its own error response (`lib/server/bff.ts`, `upstreamUnavailable`).

No client change is needed for ERR-02.

## 8. Mock modes

| Client | Switch | Evidence |
|---|---|---|
| Customer app | None found for the API | Only static mock categories (`MOCK_CATEGORIES`) |
| Owner app | `EXPO_PUBLIC_USE_MOCK_API` | `src/mocks/server.ts:14`. The default is set in environment files, which this scan does not read, so it is not verified. |
| Website | `API_MOCK` (optional; `true` uses an in-process fake backend) | `lib/server/env.ts:10`; refused in production (`:15-16`); `lib/server/mock/backend.ts:15` |

## 9. Appendix: per-route usage

Every one of the 140 backend routes. Callers: C = customer app, O = owner app, W = website, `-` = none found. Evidence shows up to two source locations (client letter, file and line). Read §5 before treating any `-` row as removable.

| Route | Callers | Evidence |
|---|---|---|
| `GET /v1/availability` | C, O, W | `C:src/services/supabase/booking.service.ts:118`; `O:src/api/repositories/booking.repository.ts:78` |
| `GET /v1/catalog/categories` | C, O | `C:src/services/supabase/salon.service.ts:205`; `O:src/api/repositories/catalog.repository.ts:39` |
| `GET /v1/catalog/categories/{category_id}/subcategories` | C | `C:src/services/supabase/salon.service.ts:209` |
| `GET /v1/payments/config` | C | `C:src/server-state/payments.ts:22` |
| `GET /v1/salons` | C, W | `C:src/services/supabase/salon.service.ts:137`; `W:lib/api/public.ts:32` |
| `GET /v1/salons/nearby` | C, W | `C:src/services/supabase/salon.service.ts:166`; `W:lib/api/public.ts:47` |
| `GET /v1/salons/{salon_id}` | C, W | `C:src/services/supabase/salon.service.ts:176`; `W:lib/api/public.ts:51` |
| `GET /v1/salons/{salon_id}/services` | C, W | `C:src/services/supabase/booking.service.ts:131`; `C:src/services/supabase/salon.service.ts:194` |
| `GET /v1/salons/{salon_id}/staff` | C, W | `C:src/services/supabase/salon.service.ts:237`; `W:lib/api/public.ts:59` |
| `GET /v1/subscriptions/config` | - | – |
| `POST /v1/account/deletion` | C, O, W | `C:src/services/api/accountDeletion.service.ts:60`; `O:src/api/repositories/account.repository.ts:61` |
| `POST /v1/account/deletion/challenges` | C, O, W | `C:src/services/api/accountDeletion.service.ts:54`; `O:src/api/repositories/account.repository.ts:48` |
| `POST /v1/account/deletion/challenges/{challenge_id}/verify` | C, O, W | `C:src/services/api/accountDeletion.service.ts:57`; `O:src/api/repositories/account.repository.ts:54` |
| `GET /v1/account/deletion/{request_id}` | O, W | `O:src/api/repositories/account.repository.ts:75`; `W:app/api/account-deletion/[action]/route.ts:103` |
| `POST /v1/auth/forgot-password` | - | – |
| `GET /v1/auth/me` | C, O, W | `C:src/services/api/accountDeletion.service.ts:88`; `O:src/api/repositories/account.repository.ts:91` |
| `POST /v1/auth/owner-access` | O | `O:src/api/repositories/auth.repository.ts:58` |
| `POST /v1/auth/refresh` | - | – |
| `GET /v1/profiles/me` | - | – |
| `PATCH /v1/profiles/me` | O | `O:src/api/repositories/auth.repository.ts:187` |
| `GET /v1/customer/profile` | C | `C:src/services/supabase/profile.service.ts:40` |
| `PATCH /v1/customer/profile` | C | `C:src/services/supabase/profile.service.ts:49` |
| `POST /v1/reports` | C | `C:src/services/supabase/report.service.ts:23` |
| `GET /v1/salons/me` | O | `O:src/api/repositories/salon.repository.ts:50` |
| `PATCH /v1/salons/me` | O | `O:src/api/repositories/salon.repository.ts:59` |
| `GET /v1/salons/me/blocks` | O | `O:src/api/repositories/holiday.repository.ts:42` |
| `POST /v1/salons/me/blocks` | O | `O:src/api/repositories/holiday.repository.ts:48` |
| `DELETE /v1/salons/me/blocks/{block_id}` | O | `O:src/api/repositories/holiday.repository.ts:53` |
| `POST /v1/salons/me/closures` | O | `O:src/api/repositories/holiday.repository.ts:109` |
| `POST /v1/salons/me/closures/preview` | O | `O:src/api/repositories/holiday.repository.ts:105` |
| `POST /v1/salons/me/complete-profile` | O | `O:src/api/repositories/salon.repository.ts:64` |
| `GET /v1/salons/me/earnings` | - | – |
| `GET /v1/salons/me/holidays` | O | `O:src/api/repositories/holiday.repository.ts:22` |
| `POST /v1/salons/me/holidays` | O | `O:src/api/repositories/holiday.repository.ts:27` |
| `DELETE /v1/salons/me/holidays/{holiday_id}` | O | `O:src/api/repositories/holiday.repository.ts:32` |
| `GET /v1/salons/me/images` | O | `O:src/api/repositories/salon.repository.ts:74` |
| `POST /v1/salons/me/images` | O | `O:src/api/repositories/salon.repository.ts:80`; `O:src/api/repositories/salon.repository.ts:87` |
| `DELETE /v1/salons/me/images/{image_id}` | O | `O:src/api/repositories/salon.repository.ts:97` |
| `PATCH /v1/salons/me/images/{image_id}` | - | – |
| `GET /v1/salons/me/payout-account` | O | `O:src/api/repositories/payout.repository.ts:21` |
| `PUT /v1/salons/me/payout-account` | O | `O:src/api/repositories/payout.repository.ts:30` |
| `GET /v1/salons/me/payout-account/history` | - | – |
| `GET /v1/salons/me/qr` | O | `O:src/api/repositories/salon.repository.ts:112` |
| `GET /v1/salons/me/services` | O | `O:src/api/repositories/service.repository.ts:43` |
| `POST /v1/salons/me/services` | O | `O:src/api/repositories/service.repository.ts:48` |
| `DELETE /v1/salons/me/services/{service_id}` | O | `O:src/api/repositories/service.repository.ts:62` |
| `PATCH /v1/salons/me/services/{service_id}` | O | `O:src/api/repositories/service.repository.ts:55` |
| `PATCH /v1/salons/me/settings` | O | `O:src/api/repositories/salon.repository.ts:69` |
| `GET /v1/salons/me/settlement-account` | - | – |
| `POST /v1/salons/me/settlement-account/register` | - | – |
| `GET /v1/salons/me/setup-status` | O | `O:src/api/repositories/setup-status.repository.ts:21` |
| `GET /v1/salons/me/staff` | O | `O:src/api/repositories/staff.repository.ts:55` |
| `POST /v1/salons/me/staff` | O | `O:src/api/repositories/staff.repository.ts:62` |
| `DELETE /v1/salons/me/staff/{staff_id}` | O | `O:src/api/repositories/staff.repository.ts:83`; `O:src/api/repositories/staff.repository.ts:88` |
| `PATCH /v1/salons/me/staff/{staff_id}` | O | `O:src/api/repositories/staff.repository.ts:67`; `O:src/api/repositories/staff.repository.ts:73` |
| `GET /v1/salons/me/staff/{staff_id}/services` | O | `O:src/api/repositories/staff.repository.ts:106` |
| `POST /v1/salons/me/staff/{staff_id}/services` | O | `O:src/api/repositories/staff.repository.ts:101` |
| `GET /v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages` | O | `O:src/api/repositories/staff.repository.ts:112`; `O:src/api/repositories/staff.repository.ts:127` |
| `PUT /v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages` | O | `O:src/api/repositories/staff.repository.ts:112`; `O:src/api/repositories/staff.repository.ts:127` |
| `GET /v1/booking-action-requests` | O | `O:src/api/repositories/booking-action-request.repository.ts:34` |
| `POST /v1/booking-action-requests/{request_id}/respond` | O | `O:src/api/repositories/booking-action-request.repository.ts:73` |
| `GET /v1/bookings` | C, O, W | `C:src/services/supabase/booking.service.ts:77`; `O:src/api/repositories/booking.repository.ts:59` |
| `POST /v1/bookings` | C, O, W | `C:src/services/supabase/booking.service.ts:138`; `C:src/services/supabase/booking.service.ts:77` |
| `POST /v1/bookings/quote` | - | – |
| `GET /v1/bookings/{booking_id}` | C, O, W | `C:src/services/supabase/booking.service.ts:160`; `O:src/api/repositories/booking.repository.ts:68` |
| `POST /v1/bookings/{booking_id}/approve` | O | `O:src/api/repositories/booking.repository.ts:95` |
| `POST /v1/bookings/{booking_id}/cancel` | C, W | `C:src/services/supabase/booking.service.ts:172`; `W:app/api/customer/bookings/[id]/cancel/route.ts:38` |
| `POST /v1/bookings/{booking_id}/cancel/barber` | O | `O:src/api/repositories/booking.repository.ts:134` |
| `POST /v1/bookings/{booking_id}/cancellation-requests` | C | `C:src/services/supabase/booking.service.ts:192` |
| `POST /v1/bookings/{booking_id}/check-in` | - | – |
| `POST /v1/bookings/{booking_id}/complete` | O | `O:src/api/repositories/booking.repository.ts:108` |
| `POST /v1/bookings/{booking_id}/delay` | O | `O:src/api/repositories/booking.repository.ts:125` |
| `POST /v1/bookings/{booking_id}/no-show` | - | – |
| `POST /v1/bookings/{booking_id}/payment` | O | `O:src/api/repositories/booking.repository.ts:142` |
| `POST /v1/bookings/{booking_id}/payment-confirmation-requests` | C | `C:src/services/supabase/booking.service.ts:188` |
| `POST /v1/bookings/{booking_id}/reject` | O | `O:src/api/repositories/booking.repository.ts:101` |
| `GET /v1/walkin/{qr_token}` | W | `W:lib/api/public.ts:6` |
| `POST /v1/walkin/{qr_token}/bookings` | W | `W:app/api/customer/bookings/route.ts:34` |
| `GET /v1/walkin/{qr_token}/qr` | - | – |
| `POST /v1/walkin/{qr_token}/verify-phone` | W | `W:app/api/customer/verify-phone/route.ts:34` |
| `GET /v1/bookings/{booking_id}/payments` | - | – |
| `POST /v1/bookings/{booking_id}/payments/cancel` | - | – |
| `POST /v1/bookings/{booking_id}/payments/confirm` | - | – |
| `POST /v1/bookings/{booking_id}/payments/intent` | - | – |
| `POST /v1/bookings/{booking_id}/payments/refresh` | - | – |
| `POST /v1/bookings/{booking_id}/payments/{payment_id}/refund` | - | – |
| `GET /v1/salons/me/access-state` | O | `O:src/api/repositories/access-state.repository.ts:61` |
| `GET /v1/salons/me/subscription` | O | `O:src/api/repositories/subscription.repository.ts:28` |
| `POST /v1/salons/me/subscription/cancel` | - | – |
| `POST /v1/salons/me/subscription/checkout` | - | – |
| `GET /v1/salons/me/subscription/payments` | - | – |
| `POST /v1/salons/me/subscription/verify` | - | – |
| `GET /v1/subscription-plans` | - | – |
| `POST /v1/customer/profile/avatar` | C | `C:src/services/supabase/profile.service.ts:75` |
| `GET /v1/media/results/{token}` | - | – |
| `PUT /v1/media/uploads/{token}` | - | – |
| `POST /v1/profiles/me/avatar-upload-url` | O | `O:src/api/image-storage.ts:38` |
| `POST /v1/salons/me/images/upload-url` | O | `O:src/api/image-storage.ts:40` |
| `POST /v1/salons/me/staff/{staff_id}/photo-upload-url` | O | `O:src/api/image-storage.ts:42` |
| `POST /v1/devices` | C, O | `C:src/services/firebase/pushNotifications.service.ts:162`; `O:src/api/repositories/notification.repository.ts:49` |
| `DELETE /v1/devices/{token}` | C, O | `C:src/services/firebase/pushNotifications.service.ts:178`; `O:src/api/repositories/notification.repository.ts:55` |
| `GET /v1/email/events/{event_id}` | - | – |
| `GET /v1/notifications` | C, O | `C:src/services/supabase/notification.service.ts:59`; `C:src/services/supabase/notification.service.ts:79` |
| `POST /v1/notifications/read-all` | C, O | `C:src/services/supabase/notification.service.ts:73`; `O:src/api/repositories/notification.repository.ts:34` |
| `POST /v1/notifications/{notification_id}/read` | C, O | `C:src/services/supabase/notification.service.ts:66`; `C:src/services/supabase/notification.service.ts:82` |
| `POST /v1/support/tickets` | - | – |
| `GET /v1/support/tickets/{ticket_id}` | - | – |
| `POST /v1/support/tickets/{ticket_id}/reply` | - | – |
| `GET /v1/admin/account-deletions` | W | `W:lib/api/admin.ts:106` |
| `GET /v1/admin/catalog/categories` | W | `W:lib/api/admin.ts:50` |
| `POST /v1/admin/catalog/categories` | W | `W:lib/api/admin.ts:52` |
| `PATCH /v1/admin/catalog/categories/{category_id}` | W | `W:lib/api/admin.ts:54` |
| `POST /v1/admin/catalog/categories/{category_id}/deactivate` | W | `W:lib/api/admin.ts:55` |
| `GET /v1/admin/catalog/categories/{category_id}/subcategories` | W | `W:lib/api/admin.ts:57` |
| `GET /v1/admin/catalog/languages` | - | – |
| `POST /v1/admin/catalog/subcategories` | W | `W:lib/api/admin.ts:59` |
| `PATCH /v1/admin/catalog/subcategories/{subcategory_id}` | W | `W:lib/api/admin.ts:61` |
| `POST /v1/admin/catalog/subcategories/{subcategory_id}/deactivate` | W | `W:lib/api/admin.ts:62` |
| `GET /v1/admin/salons` | W | `W:lib/api/admin.ts:25` |
| `POST /v1/admin/salons` | W | `W:lib/api/admin.ts:32` |
| `GET /v1/admin/salons/{salon_id}` | W | `W:lib/api/admin.ts:26` |
| `PATCH /v1/admin/salons/{salon_id}` | W | `W:lib/api/admin.ts:31` |
| `POST /v1/admin/salons/{salon_id}/approve` | W | `W:lib/api/admin.ts:28` |
| `POST /v1/admin/salons/{salon_id}/deactivate` | W | `W:lib/api/admin.ts:30` |
| `GET /v1/admin/salons/{salon_id}/onboarding` | W | `W:lib/api/admin.ts:27` |
| `POST /v1/admin/salons/{salon_id}/reject` | W | `W:lib/api/admin.ts:29` |
| `GET /v1/admin/salons/{salon_id}/subscription` | W | `W:lib/api/admin.ts:41` |
| `POST /v1/admin/salons/{salon_id}/subscription/test` | W | `W:lib/api/admin.ts:43` |
| `GET /v1/admin/subscription-events` | W | `W:lib/api/admin.ts:47` |
| `GET /v1/admin/subscription-plans` | W | `W:lib/api/admin.ts:36` |
| `POST /v1/admin/subscription-plans` | W | `W:lib/api/admin.ts:37` |
| `PATCH /v1/admin/subscription-plans/{plan_id}` | W | `W:lib/api/admin.ts:38` |
| `POST /v1/admin/subscription-plans/{plan_id}/deactivate` | W | `W:lib/api/admin.ts:39` |
| `POST /v1/admin/subscriptions/{subscription_id}/cancel` | W | `W:lib/api/admin.ts:44` |
| `POST /v1/admin/subscriptions/{subscription_id}/suspend` | W | `W:lib/api/admin.ts:45` |
| `POST /v1/webhooks/{provider}` | - | – |
| `GET /health` | - | – |
| `GET /health/db` | - | – |
| `GET /health/ready` | - | – |
| `GET /health/redis` | - | – |
