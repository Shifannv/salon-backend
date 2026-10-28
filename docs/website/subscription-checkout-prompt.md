# Prompt: build the subscription pages on salones.in

Paste everything below the line into the coding agent working on the Salones website.

---

Build two pages on the Salones website (`https://salones.in`) where salon owners buy a plan.
Owners reach them in two ways:

1. **From the website.** An owner runs their salon on the website and opens **Subscription** from its menu, which goes to `/subscription`.
2. **From the owner app.** The app cannot sell plans because of store policy. When an owner taps "Choose Growth" or "Choose Premium", it opens `https://salones.in/subscription/checkout?plan=<plan_code>`. That link must go straight to payment for that plan.

Read this site's existing auth, API client, layout and design tokens first, and reuse them. Do not add a second API client or a second Supabase client.

## Routes

### `/subscription`: plan list
- **Header:** "Choose your plan".
- **Current plan card**, shown when signed in:
  - **Trial:** "Trial", days left, and "N of 500 bookings used", with a progress bar.
  - **Paid:** "Growth" or "Premium", with "Active until <date>".
  - **Ended:** "Trial ended" or "Plan ended", with the backend's `wall_messages[0]` text.
- **Interval toggle:** Monthly, 6 months, Yearly. Each toggle shows a "Save N%" badge, using the smallest `discount_percent` among the plans for that interval.
- **Plan cards:** Growth (tier 1) and Premium (tier 2) for the selected interval. Each card shows:
  - the price, from `price_amount` formatted as INR with no decimals (₹1,675);
  - the period ("per 6 months");
  - "₹279 a month", from `monthly_equivalent`, when present;
  - a "Save 20%" pill;
  - the features list;
  - a **"Special price for your salon"** tag plus the struck-through `default_price_amount` when `custom_price` is true;
  - a **"Current plan"** badge on the active tier;
  - a button: **"Choose Growth"** / **"Choose Premium"**, or **"Renew"** on the current tier. It links to `/subscription/checkout?plan=<code>`.
- **Signed out:** show the plans with the default prices. The buttons still link to checkout, and sign-in happens there.

### `/subscription/checkout?plan=<code>`: payment for one plan
1. **Not signed in:** send the owner to the site's sign-in, with a return URL of this exact path *including* `?plan=…`. Use the same Supabase project and methods as the rest of the site: phone OTP and Google. After sign-in, the owner lands back here.
2. **Load the data:**
   - `GET /v1/subscription-plans`, then find the plan whose `code` equals `plan`.
   - `GET /v1/subscriptions/config`.
   - `GET /v1/salons/me/subscription`.
3. **Unknown or missing `plan`:** show "This plan is not available" and a link to `/subscription`.
4. **Order summary:** plan name, period, price, "Save N%", and the special-price tag if any. Show "Prices are in INR." Do not claim GST is included, because `tax_inclusive` may be null.
5. **"Pay ₹1,675":**
   - Call `POST /v1/salons/me/subscription/checkout`.
   - Open Razorpay Checkout with the returned `client_payload`.
   - On success, call `POST /v1/salons/me/subscription/verify`.
   - Show the result.
6. **Success:** "You're on Growth until <paid_through>". Offer buttons for "Open the Salones app" and "Back to dashboard". The app picks up the new plan by itself the next time it loads.

## API

- **Base URL:** `https://api.salones.in/v1`, taken from the site's existing env variable. Do not hard-code it.
- **Auth:** `Authorization: Bearer <supabase access_token>` on every call.
- **Money:** amounts arrive as strings (`"1675.00"`). Parse them to numbers only for display. Never send a price to the backend.

| Call | Notes |
|---|---|
| `GET /subscriptions/config` | `{ enabled, provider, public_key, currency, checkout_url, native_purchase_allowed:false }`. If `enabled` is false, show "Online payment is not available right now. Please contact support." and no Pay button. |
| `GET /subscription-plans` | Array of `{ id, code, name, tier, price_amount, default_price_amount, custom_price, currency, billing_interval: "monthly"\|"semiannual"\|"yearly", features: {...}, monthly_equivalent, discount_percent, tax_inclusive }`. Prices are already this salon's. Owners only: any other role gets 403, so show "Only the salon owner can buy a plan." |
| `GET /salons/me/subscription` | `{ status, plan:{code,name,tier}\|null, entitlement_state, paid_through, grace_ends_at, cancelled, open_checkout, latest_payment, ... }`. |
| `GET /salons/me/access-state` | `{ access_state, trial_ends_at, trial_booking_limit, trial_bookings_counted, subscription_wall, wall_messages[], paid_through, ... }`. Used for the current-plan card. |
| `POST /salons/me/subscription/checkout` | Body `{ "plan_id": "<uuid from the plan list>" }`. **Requires the header `Idempotency-Key: <uuid>`.** Returns `{ billing_id, order_ref, amount, currency, plan_code, expires_at, client_payload: { key_id, order_id, amount (paise), currency } }`. |
| `POST /salons/me/subscription/verify` | Body `{ order_ref, payment_ref?, signature? }`, where `payment_ref` and `signature` come from Razorpay's handler response. Returns the subscription state. Safe to call repeatedly. |

**Feature labels:**

| Key | Label |
|---|---|
| `unlimited_bookings` | Unlimited bookings |
| `split_bill` | Split bill |
| `daily_ledger` | Daily ledger |
| `rank_boost` | Ranked higher for customers |
| `smart_slot_filler` | Smart slot filler |
| `sms_alerts` | SMS alerts (up to `monthly_alert_cap` a month) |

## Payment rules (do not skip)

- **Idempotency key:** create one UUID per (salon, plan) attempt. Keep it in `sessionStorage` and reuse it on retries and on page reload, so a double click or a refresh never creates two orders. Clear it after a successful verify.
- **Razorpay Checkout:**
  - Load `https://checkout.razorpay.com/v1/checkout.js` only on the checkout page.
  - Use `key: client_payload.key_id`, `order_id: client_payload.order_id`, `amount: client_payload.amount`, and `currency`.
  - Prefill the owner's name, email and phone when known.
- **Only `verify` decides whether the payment succeeded.**
  - Never show "Paid" from the Razorpay callback alone.
  - If the owner closes the Razorpay window or the network drops, call `verify` with the `order_ref` anyway. The payment may have gone through.
- **409 "A subscription payment is already open":** read `open_checkout` from `GET /salons/me/subscription`.
  - If it is the same plan, retry checkout with the **same** idempotency key to resume it.
  - Otherwise, say "Finish or wait for your previous payment (expires at <time>)".
- **503:** billing is off. Show the contact-support message.
- **Errors:** read the error envelope's `code` and show friendly text. Never print raw server errors.
- **Pay button:** disable it while a request is in flight.

## States to handle on both pages

- loading (skeletons);
- signed out;
- not an owner;
- plans empty ("Plans are not available yet");
- invalid plan code;
- billing disabled;
- payment cancelled ("Payment was not completed. You have not been charged.");
- payment failed (with a retry button);
- verifying ("Confirming your payment…", polling `verify` up to 3 times, 3 seconds apart);
- success;
- offline.

## Security

- Never put the Razorpay secret or any service key in the website. Only the public `key_id` comes from the API.
- Validate `plan` against the codes from the API. Never interpolate it into HTML.
- Keep the `?plan=` value through the sign-in redirect, and only allow same-site return URLs (an open-redirect guard).

## Design

- Match the site's existing typography, colours and card style. It should feel like part of the same product as the owner app: rounded cards and green "Save" pills.
- Make it mobile first, because most owners arrive from the phone app. The Pay button should be sticky at the bottom on small screens.
- Make it accessible: labelled buttons, visible focus, a contrast ratio of at least 4.5:1, and a toggle that is keyboard operable (`role="tablist"`).

## Done when

- `/subscription` and `/subscription/checkout?plan=growth_6m` work both signed in and signed out.
- A test-mode Razorpay payment moves the owner to Growth, and `GET /salons/me/subscription` shows `entitlement_state: "active"`.
- Reloading during payment never creates a second order.
- An unknown `?plan=` code shows the "not available" state.
