# Marketplace model: API contract (single source for backend, apps and website)

Status: **agreed design, built phase by phase**. Backend implements exactly this; the owner app, customer app and website
build against it with mocks and then regenerate types from the real OpenAPI. Everything is **additive**: an older app
version keeps working (new response fields are optional and new routes are new). Product rules live in
`PAYMENT_DECISIONS.md` and the approved plan; this file is the wire format.

## 0. Conventions

- JSON `snake_case`. IDs are UUID strings. Datetimes are ISO-8601 with offset. Money is a **string with two decimals**
  (`"225.00"`), never a float. Percentages are strings (`"10.00"`).
- Errors use the existing envelope `{"code": "...", "message": "..."}`; codes are stable and listed per route.
  Entitlement errors: **403 `subscription_required`** (salon locked and not subscribed) and **403 `entitlement_required`**
  (subscribed but the tier does not include the feature). Neither reveals prices.
- Authorization lives in use cases. "Owner" below means the salon owner; "staff" the salon's staff user. Customers and
  other salons' owners always get 403/404.
- The client never computes pricing, refunds, discounts, access state or caps. It renders what the server returns.

## 1. Access state (trial, soft wall, entitlements)

`GET /v1/salons/me/access-state` (owner, staff) -> 200

```json
{
  "state": "trialing",
  "soft_wall_enforced": false,
  "is_locked": false,
  "trial": {
    "started_at": "2026-10-13T08:00:00+00:00",
    "ends_at": "2026-12-12T08:00:00+00:00",
    "bookings_used": 37,
    "bookings_limit": 120,
    "days_left": 60,
    "ended_reason": null
  },
  "lock_effective_at": null,
  "subscription": {
    "tier": null,
    "status": null,
    "paid_through": null
  },
  "entitlements": {
    "unlimited_bookings": true,
    "split_bill": true,
    "daily_ledger": true,
    "rank_boost": false,
    "smart_slot_filler": false,
    "sms_alerts": false
  }
}
```

- `state` is one of `trialing | soft_locked | subscribed_growth | subscribed_premium`.
- `trial.ended_reason` is `null | "booking_limit" | "date"` and, once set, never reverts (cancellations do not reopen a
  finished trial). `trial.days_left` is `0` when ended.
- `is_locked = soft_wall_enforced AND state == "soft_locked"`. While `SOFT_WALL_ENABLED=false` the state is still reported
  but nothing is masked and `is_locked` is always `false`.
- `trial` is `null` for a salon that has never had one. `subscription.tier` is `"growth" | "premium" | null`;
  `paid_through` is an ISO datetime or `null`.
- Trial entitlements equal Growth (`split_bill`, `daily_ledger`, `unlimited_bookings` true; the rest false).
  Premium adds `rank_boost`, `smart_slot_filler`, `sms_alerts`. A locked, unsubscribed salon has every entitlement false
  except that it can still approve/complete/cancel its bookings.
- The response carries **no URLs and no prices**: the native owner app must show only plain text ("Manage your
  subscription on our website") because of store billing rules.

## 2. Masked bookings (owner and staff views)

Applies to every response that returns a booking to an owner or staff user: `GET /v1/bookings`,
`GET /v1/bookings/{id}`, the response of create/approve/reject/cancel/complete/payment actions,
`GET /v1/booking-action-requests`, and the closure preview. New optional fields on `BookingResponse`:

```json
{
  "is_masked": true,
  "customer_name": "Rahul K.",
  "customer_phone": null,
  "customer_phone_masked": "98XXXXXX21",
  "contact_cta": "Subscribe to unlock",
  "unmasked_reason": null
}
```

Rules (server-enforced):
- A booking is masked for owner/staff only when the salon `is_locked` AND the booking is **not** unmasked by an exemption.
  `is_masked` defaults to `false` (older servers omit it).
- When masked: `customer_phone` is **`null`** (fail-safe: an app that does not know the new fields shows "no phone" and
  never dials a masked string), `customer_phone_masked` carries the display value, `customer_name` is reduced to first
  name plus initial (`"Rahul K."`; a single word stays as is), `contact_cta` is `"Subscribe to unlock"`. Time, services,
  staff, price, status and payment fields stay visible. Notes are hidden (`null`).
- Exemptions (the booking stays unmasked and carries `unmasked_reason`):
  - `"paid_before_lock"`: `payment_preference == "pay_full"`, a **captured** gateway payment whose `paid_at` is before
    `lock_effective_at`, and the booking status is still `pending` or `confirmed`.
  - `"owner_entered"`: `source == "manual_walkin"` (the owner typed that data themselves).
- There is no queue "token" in this product; nothing token-like is returned or masked.
- Customers always see their own booking unmasked. Masking never applies to customer views.
- Owner **notifications** (`/v1/notifications` rows, push title/body, `data`) created while the salon is locked contain no
  customer name or phone: title `"New booking"`, body `"A customer booked an appointment. Subscribe to see customer details."`.
- Enforcement is also in the database: the `authenticated` role cannot read `bookings.customer_phone` / `customer_name`
  (column privileges), owners cannot write bookings directly, and Realtime payloads for `bookings` carry no contact data.

## 3. Payment modes

- Customer-facing modes are only **Pay Online** (`payment_preference: "pay_full"`) and **Pay at Salon**
  (`payment_preference: "pay_at_salon"`). `pay_advance` stays valid in the database but is no longer offered or accepted
  from new clients (422 `payment_preference_unsupported`). Customers never see a platform or convenience fee; the total
  is the salon's service price (after an active slot-filler discount, section 6).
- `GET /v1/salons/{salon_id}/payment-options` (public, authenticated optional) -> 200

```json
{
  "pay_online": { "available": false, "reason": "salon_not_ready" },
  "pay_at_salon": { "available": true, "instruments": ["cash", "upi_direct"] }
}
```

  `reason` is `null | "provider_disabled" | "salon_not_ready"` (the salon's payout vendor is not `active`). Pay at Salon is
  always available. `GET /v1/payments/config` keeps its current shape.
- **Pay at Salon confirmation.** The customer taps "I paid at the salon" (existing
  `POST /v1/bookings/{id}/payment-confirmation-requests`); the owner answers through the existing
  `POST /v1/booking-action-requests/{id}/respond` or records it directly with `POST /v1/bookings/{id}/payment`.
  Both accept an optional `payment_instrument`:

```json
{ "payment_method": "cash", "payment_instrument": "cash" }
```

  `payment_method` stays `"cash" | "online"`. Direct UPI to the salon is `{"payment_method": "online", "payment_instrument":
  "upi_direct"}` and is recorded as a **manual** ledger row (no gateway, no fee). When omitted the instrument is `cash`.
  The customer's booking updates in real time (`payment_status`, `latest_payment_request_decision`).

## 4. Cancellation and refund quote (Pay Online)

`GET /v1/bookings/{id}/cancellation-quote` (the booking's customer only) -> 200

```json
{
  "booking_id": "b1c2...",
  "can_cancel": true,
  "payment_preference": "pay_full",
  "paid_online": true,
  "currency": "INR",
  "amount_paid": "250.00",
  "refund_amount": "225.00",
  "deduction_amount": "25.00",
  "deduction_rule": { "type": "percent", "value": "10.00" },
  "applies_to": "customer_cancellation",
  "message": "You will be refunded 225.00. 25.00 is kept as a cancellation charge."
}
```

- For Pay at Salon (or an unpaid online booking) `paid_online` is `false` and `refund_amount` / `deduction_amount` are
  `"0.00"`: nothing to refund and no fee.
- `deduction_rule.type` is `"percent" | "flat"` (config `CANCELLATION_DEDUCTION_TYPE`, `CANCELLATION_DEDUCTION_VALUE`;
  default **percent 10.00**; the owner must confirm Rs 10 flat vs 10 percent). The deduction never exceeds the amount paid.
- `POST /v1/bookings/{id}/cancel` (customer) now, for a paid online booking, **creates the refund server-side** for
  `refund_amount` with the deterministic idempotency key `cancel:{booking_id}` (a repeat call never refunds twice), and
  returns the usual `BookingResponse` plus an optional field:

```json
{ "cancellation_refund": { "status": "pending", "amount": "225.00", "deduction": "25.00" } }
```

  `status` is `"pending" | "refunded" | "none"`. A salon rejection, salon/owner cancellation and salon closure refund the
  **full** amount paid (no deduction). Refund amounts always come from the server.

## 5. Split-bill: commission rules and daily ledger

Entitlement: `split_bill` (rules) and `daily_ledger` (ledger), i.e. trial, Growth or Premium; otherwise 403.

- `POST /v1/salons/me/commission-rules` (owner) -> 201

```json
{ "staff_id": "9f...|null", "staff_percent": "40.00" }
```

  `staff_id: null` sets the salon default. The salon share is `100 - staff_percent`. Creating a rule supersedes the previous
  rule for the same scope (rules are versioned, never edited in place). Validation: `0 <= staff_percent <= 100`.
- `GET /v1/salons/me/commission-rules` -> 200

```json
{
  "default": { "id": "r1", "staff_id": null, "staff_percent": "40.00", "salon_percent": "60.00", "effective_from": "..." },
  "rules": [ { "id": "r2", "staff_id": "9f..", "staff_name": "Asha", "staff_percent": "50.00", "salon_percent": "50.00", "effective_from": "..." } ]
}
```

  The stylist rule wins over the default; no rule means 0 percent to the stylist (all revenue is the salon's).
- On the transition of a booking to `completed` (database trigger, exactly once) the ledger records, per booking:
  `service_gross` (the booking's service total after discount), `stylist_payout` (`gross * staff_percent`),
  `gateway_fee` (gateway-paid rows only: `PAYMENT_GATEWAY_FEE_PERCENT` of gross, borne by the **salon**, deducted from the
  salon share), `owner_net` (`gross - stylist_payout - gateway_fee`), the payment source (`cash | online | upi_direct`) and
  the rule id and percentages used (a snapshot). The ledger is written for every salon; **reading** it needs the entitlement.
- `GET /v1/salons/me/ledger/daily?date=YYYY-MM-DD` (default today in the salon timezone) -> 200

```json
{
  "date": "2026-10-13",
  "timezone": "Asia/Kolkata",
  "currency": "INR",
  "totals": {
    "bookings_completed": 6,
    "service_gross": "2400.00",
    "stylist_payouts": "960.00",
    "gateway_fees": "24.00",
    "owner_net": "1416.00",
    "cash_collected": "1000.00",
    "online_collected": "1400.00",
    "upi_direct_collected": "0.00"
  },
  "by_stylist": [
    { "staff_id": "9f..", "staff_name": "Asha", "bookings": 3, "gross": "1200.00", "payout": "480.00", "salon_share": "720.00" }
  ],
  "entries": [
    {
      "booking_id": "b1..", "completed_at": "2026-10-13T11:20:00+05:30",
      "service_names": ["Haircut"], "staff_id": "9f..", "staff_name": "Asha",
      "payment_source": "online", "gross": "400.00", "gateway_fee": "8.00",
      "stylist_payout": "160.00", "owner_net": "232.00", "staff_percent": "40.00"
    }
  ]
}
```

  An empty day returns zero totals and empty arrays (never 404). A completed booking can never produce two ledger rows.

## 6. Smart slot filler (Premium)

Entitlement: `smart_slot_filler`; otherwise 403 `entitlement_required`.

- `POST /v1/salons/me/slot-filler-rules` (owner) -> 201; `GET` -> 200 `{ "rules": [...] }`; `PATCH /{id}`; `DELETE /{id}`
  deactivates (soft, no hard delete).

```json
{ "day_of_week": 2, "start_time": "12:00", "end_time": "16:00", "discount_percent": "20.00", "is_active": true }
```

  `day_of_week` is ISO (1 = Monday ... 7 = Sunday), times are `HH:MM` in the salon timezone, `start_time < end_time`,
  `0 < discount_percent <= SLOT_FILLER_MAX_DISCOUNT_PERCENT` (default 50, a fat-finger guard). Overlapping active windows on
  the same weekday are rejected (422 `slot_filler_overlap`).
- **Customer discount.** A booking whose appointment start falls inside an active window of a Premium salon gets the
  discount applied by the server inside booking creation. `BookingResponse` gains `original_price`, `discount_percent`,
  `discount_amount` (all optional strings; `total_price` is the discounted price that online payment charges).
  `GET /v1/availability` slot items gain an optional `discount_percent` (a display hint; availability itself is unchanged).
- **Search.** `GET /v1/salons` and the salon detail gain `slot_discount` (the window active **now**, else `null`):

```json
{ "discount_percent": "20.00", "label": "20% off until 4 PM", "ends_at": "2026-10-13T16:00:00+05:30" }
```

  Ranking: when a request carries `lat` and `lng`, a Premium salon with an active window **now** and within 2 km gets an
  additional rank weight `SLOT_FILLER_RANK_BOOST` (config, no invented default: unset means no boost). The boost only
  reorders; it never hides a salon or changes `isSalonVisible` / availability.

## 7. Alerts: delivery acknowledgement, session and settings

- `POST /v1/notifications/{notification_id}/delivered` (the notification's recipient) -> 204. Idempotent per
  `(notification, device, state)`.

```json
{ "state": "received", "device_token": "optional-string", "received_at": "2026-10-13T10:00:03+05:30" }
```

  `state` is `"received" | "displayed" | "opened"`. A `received` or `opened` ack cancels the pending SMS fallback; an
  `opened` ack also sets `read_at`.
- `POST /v1/auth/session-started` (any authenticated user; owner/staff matter) -> 200 `{ "sms_alert_active": true }`,
  body `{ "platform": "android", "app_version": "1.0.8" }` (both optional). Throttled to one write per minute per user.
  Updates the user's last-session time and re-enables `sms_alert_active` if it was switched off for inactivity.
- `GET /v1/salons/me/alert-settings` (owner) -> 200

```json
{
  "channel_available": true,
  "sms_alert_enabled": true,
  "sms_alert_active": true,
  "auto_disabled_reason": null,
  "monthly_cap": 300,
  "used": 12,
  "remaining": 288,
  "period": "2026-10",
  "last_session_at": "2026-10-13T09:58:00+05:30"
}
```

  `auto_disabled_reason` is `null | "owner_inactive" | "cap_reached" | "not_premium"`. `channel_available` is `false` on
  non-Premium salons. `PATCH /v1/salons/me/alert-settings` body `{ "sms_alert_enabled": false }` -> 200 (same shape).
- **Circuit breaker** (backend only): a Premium booking creates the push; if no `received`/`opened` ack (and not read) arrives
  within 5 minutes and `sms_alert_enabled AND sms_alert_active` and the monthly counter is below 300, the worker sends an
  SMS/WhatsApp via the provider-neutral messaging port and logs it. The counter increment is atomic (a hard stop at 300 for
  SMS and WhatsApp combined). `sms_alert_active` becomes `false` when the owner has had no valid session for 24 hours.
  The app can only ack when it runs: a push shown by the OS tray is not observable, so acks come from foreground receipt, a
  tap, or opening the app (which acks recent unread notifications). A fallback may therefore reach an owner who saw the
  push in the tray but did not open the app within 5 minutes; the 300 cap bounds the cost.

## 8. Subscription read model (finished by the stage-2 work)

The website purchase flow and the owner app status display use the stage-2 routes documented in
`docs/Salon-Owner-App-Backend-API-Document.md` (`GET /v1/subscriptions/config`, `GET /v1/subscription-plans`,
`GET /v1/salons/me/subscription`, `POST /v1/salons/me/subscription/checkout|verify|cancel`,
`GET /v1/salons/me/subscription/payments`). The native owner app does **not** call checkout/verify/cancel and shows no
prices (`subscriptions/config.native_purchase_allowed` is `false`).

## 9. Configuration added by this model

`SOFT_WALL_ENABLED` (default `false`), `TRIAL_BOOKING_LIMIT` (120), `TRIAL_DAYS` (60), `PAYMENT_GATEWAY_FEE_PERCENT` (2.0,
ledger/payout only, never shown to customers), `CANCELLATION_DEDUCTION_TYPE` / `CANCELLATION_DEDUCTION_VALUE`
(percent / 10.00), `SLOT_FILLER_MAX_DISCOUNT_PERCENT` (50), `SLOT_FILLER_RANK_BOOST` (unset = off), `ALERT_MONTHLY_CAP` (300),
`ALERT_FALLBACK_DELAY_SECONDS` (300), `ALERT_INACTIVITY_HOURS` (24), `MESSAGING_PROVIDER` (`none`; a fake provider exists for tests).
Platform commission is `0` in this model (`PAYMENT_PLATFORM_FEE_PERCENT=0` is valid and means no commission).
