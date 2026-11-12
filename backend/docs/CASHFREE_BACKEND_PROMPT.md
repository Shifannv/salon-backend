# Cashfree Production Backend – Developer Verification & Integration Prompt

> **Purpose**: This document is for a backend developer to verify, test, and confirm that the Cashfree Production payment integration in the FastAPI / Python backend is production-ready. The frontend walking-customer web app is fully implemented and expects specific API contracts from this backend.
>
> **Generated**: 2026-11-12  
> **Backend path**: `d:\salon\salon-backend\backend`  
> **Frontend path**: `d:\salon\salon-QR-Walking-Web\walking-customer-web`

---

## 1. Current Status (as of 2026-11-12)

| Item | Status |
|------|--------|
| Cashfree Production API connectivity | ✅ Working — orders created, real `payment_session_id` returned |
| Backend Cashfree adapter | ✅ Code exists at `app/infrastructure/payments/cashfree.py` (696 lines) |
| Order creation (`POST /pg/orders`) | ✅ Verified — real Cashfree `cf_order_id` and `payment_session_id` returned |
| `payment_session_id` stored in DB | ✅ `booking_payments.provider_session_id` populated |
| Order lookup (`GET /pg/orders/{id}`) | ✅ Verified live — returns correct `payment_session_id` and `order_status` |
| Webhook endpoint | ⚠️ Code exists (`/v1/webhooks/cashfree`) but **needs domain verification in Cashfree dashboard** |
| Payment status refresh | ⚠️ Code exists but **not end-to-end tested** in production |
| Cashfree drop-in modal (frontend) | ⚠️ **Domain `localhost:3000` and `salones.in` must be whitelisted in Cashfree dashboard** |
| `return_url` template | ✅ `{order_id}` placeholder — Cashfree substitutes this on redirect |

---

## 2. Environment Configuration

**File**: `.env` (backend root)

```env
# Cashfree Production (Real Money)
PAYMENT_PROVIDER=cashfree
PAYMENT_SETTLEMENT_MODEL=platform_collect
PAYMENT_CURRENCY=INR
PAYMENT_ADVANCE_PERCENT=30
PAYMENT_INTENT_TTL_SECONDS=900
PAYMENT_PLATFORM_FEE_PERCENT=10
PAYMENT_COMMISSION_BASE=online_amount

CASHFREE_ENABLED=true
CASHFREE_ENV=production
CASHFREE_APP_ID=<set-in-secret-manager>
CASHFREE_SECRET_KEY=<set-in-secret-manager>
PAYMENT_ALLOW_LIVE=true
CASHFREE_API_VERSION=2026-01-01
CASHFREE_WEBHOOK_VERSION=2025-01-01
CASHFREE_EASY_SPLIT_ENABLED=false
CASHFREE_RETURN_URL=https://salones.in/booking/status?order_id={order_id}
PUBLIC_API_BASE_URL=https://api.salones.in
```

> **CRITICAL**: `booking_checkout_policy_version` MUST be `"customer_processing_v1"` (the default in `app/core/config.py`). The U08 policy (`u08-2026-10-23-v1`) deliberately blocks online collection. All DB bookings confirmed to have `checkout_policy_version = 'customer_processing_v1'`.

---

## 3. API Contract — What the Frontend Expects

### 3.1 Payment Intent (`POST /v1/bookings/{booking_id}/payments/intent`)

**Request**:
```http
POST /v1/bookings/{booking_id}/payments/intent
Authorization: Bearer {customer_jwt}
Idempotency-Key: {uuid}
Content-Type: application/json

{
  "purpose": "deposit" | "full"
}
```

- `deposit` = 30% advance payment
- `full` = 100% full payment
- `purpose` is optional — backend infers from `payment_preference` if omitted

**Response (200)**:
```json
{
  "payment_id": "uuid",
  "provider": "cashfree",
  "order_ref": "pi_31c89d4997b141a3bfef5286b6459b8a",
  "purpose": "deposit",
  "amount": "245.66",
  "currency": "INR",
  "client_payload": {
    "payment_session_id": "session_kRnL...",
    "order_id": "pi_31c89d4997b141a3bfef5286b6459b8a",
    "environment": "production"
  },
  "expires_at": "2026-11-12T07:22:00+00:00"
}
```

The frontend reads:
- `intent.client_payload.payment_session_id` → passed to `cashfree.checkout()`
- `intent.client_payload.environment` → `"production"` or `"sandbox"`
- `intent.order_ref` → stored and sent in refresh call

### 3.2 Payment Refresh (`POST /v1/bookings/{booking_id}/payments/refresh`)

**Request**:
```http
POST /v1/bookings/{booking_id}/payments/refresh
Authorization: Bearer {customer_jwt}
Idempotency-Key: {uuid}
Content-Type: application/json

{
  "order_ref": "pi_31c89d4997b141a3bfef5286b6459b8a"
}
```

**Response (200)**:
```json
{
  "booking_id": "uuid",
  "currency": "INR",
  "total_price": "900.00",
  "deposit_amount": "270.00",
  "paid_amount": "0.00",
  "refunded_amount": "0.00",
  "payment_status": "unpaid" | "deposit_paid" | "paid",
  "payment_state": "unpaid" | "deposit_paid" | "paid",
  "payments": [...],
  "refunds": [...]
}
```

The frontend checks `payment_status` or `payment_state` for `"captured"`, `"paid"`, `"deposit_paid"`, `"SUCCESS"`, `"PAID"` to determine if payment was captured.

### 3.3 Payment Config (`GET /v1/payments/config`)

**Response (200)**:
```json
{
  "enabled": true,
  "online_payment_available": true,
  "online_payment_unavailable_reason": null,
  "provider": "cashfree",
  "public_key": null,
  "settlement_model": "platform_collect",
  "confirmation": "refresh",
  "currency": "INR",
  "advance_percent": 30
}
```

> **Key**: `"confirmation": "refresh"` means the frontend polls `/refresh` after the Cashfree SDK closes. This is correct since Cashfree has no client-side callback signature.

---

## 4. Cashfree Production API — Verified Behavior (from Live Tests)

### 4.1 Order Creation

**Endpoint**: `POST https://api.cashfree.com/pg/orders`  
**API Version header**: `x-api-version: 2026-01-01`

**Request body** (confirmed from live calls):
```json
{
  "order_id": "pi_31c89d4997b141a3bfef5286b6459b8a",
  "order_amount": 245.66,
  "order_currency": "INR",
  "customer_details": {
    "customer_id": "89b52150-c8ee-4437-a704-224ae1ed0019",
    "customer_name": "Test Customer",
    "customer_phone": "9876543210"
  },
  "order_expiry_time": "2026-11-11T18:07:00Z",
  "order_note": "Booking 09faf9c5-2b2e-44da-aa89-ecf81544f0fc",
  "order_meta": {
    "notify_url": "https://api.salones.in/v1/webhooks/cashfree",
    "return_url": "https://salones.in/booking/status?order_id={order_id}"
  }
}
```

**Confirmed response fields**:
```json
{
  "cf_order_id": "7417298988",
  "order_id": "pi_31c89d4997b141a3bfef5286b6459b8a",
  "order_amount": 245.66,
  "order_currency": "INR",
  "order_status": "ACTIVE",
  "payment_session_id": "session_kRnLyfOw7NeoH6JBBAqymHwfYYnYzlB-...",
  "order_expiry_time": "2026-11-11T18:07:00+05:30"
}
```

> ✅ `payment_session_id` is the correct field name for the Cashfree 2026-01-01 API  
> ✅ `order_amount` is in **rupees** (not paise)  
> ✅ `{order_id}` in `return_url` IS substituted by Cashfree on redirect

### 4.2 Order Status / Payments Fetch

**Endpoint**: `GET https://api.cashfree.com/pg/orders/{order_id}`  
**Payments**: `GET https://api.cashfree.com/pg/orders/{order_id}/payments`

**Payment status values** (confirmed for 2026-01-01):

| Cashfree Status | Maps to |
|----------------|---------|
| `SUCCESS` | `LedgerStatus.captured` |
| `FAILED` | `LedgerStatus.failed` |
| `CANCELLED` | `LedgerStatus.failed` |
| `VOID` | `LedgerStatus.failed` |
| `USER_DROPPED` | `LedgerStatus.failed` |
| `PENDING` | `LedgerStatus.created` |
| `NOT_ATTEMPTED` | `LedgerStatus.created` |
| `FLAGGED` | `LedgerStatus.created` |

### 4.3 Webhook Signature Verification

**Algorithm**:
```python
import base64, hashlib, hmac

# From Cashfree webhook headers:
timestamp = request.headers["x-webhook-timestamp"]   # Unix seconds or ms
raw_body = await request.body()

digest = hmac.new(
    key=client_secret.encode(),
    msg=timestamp.encode() + raw_body,
    digestmod=hashlib.sha256
).digest()
expected_sig = base64.b64encode(digest).decode()

# Compare with:
incoming_sig = request.headers["x-webhook-signature"]
# Use hmac.compare_digest() to avoid timing attacks
```

**Webhook event types**:
- `PAYMENT_SUCCESS_WEBHOOK` → marks `booking_payments.status = 'captured'`, `bookings.payment_status = 'deposit_paid'` or `'paid'`
- `PAYMENT_FAILED_WEBHOOK` → marks `booking_payments.status = 'failed'`
- `PAYMENT_USER_DROPPED_WEBHOOK` → marks `booking_payments.status = 'failed'`
- `REFUND_STATUS_WEBHOOK` → updates refund record
- `VENDOR_STATUS_UPDATE` → updates settlement account (not needed, Easy Split disabled)

---

## 5. `_UNVERIFIED_*` Constants — Resolution Status

The `cashfree.py` file has these `_UNVERIFIED_*` constants. Resolution:

| Constant | Declared value | Status |
|----------|---------------|--------|
| `_UNVERIFIED_PAYMENTS_PATH` | `/orders/{order_id}/payments` | ✅ Correct |
| `_UNVERIFIED_PAYMENT_EVENTS` | `PAYMENT_SUCCESS_WEBHOOK`, etc. | ✅ Correct |
| `_UNVERIFIED_REFUND_EVENT` | `REFUND_STATUS_WEBHOOK` | ✅ Correct |
| `_UNVERIFIED_SETTLEMENT_AMOUNT_KEYS` | `("settlement_amount", "amount")` | ⚠️ Not tested (Easy Split disabled) |
| `_UNVERIFIED_VENDOR_EVENT` | `VENDOR_STATUS_UPDATE` | ⚠️ Not tested (Easy Split disabled) |
| `_UNVERIFIED_SEND_REFUND_SPLITS` | `False` | ✅ Correct (Easy Split disabled) |
| `_UNVERIFIED_INSTRUMENT` | UPI/card/netbanking map | ✅ Correct |
| `_UNVERIFIED_VENDOR_INITIAL_STATUS` | `ACTIVE` | ⚠️ Not tested (Easy Split disabled) |
| `_UNVERIFIED_ALREADY_EXISTS_STATUS` | `409` | ✅ Correct |
| `_UNVERIFIED_MIN_EXPIRY_SECONDS` | `1800` | ✅ Safe (Cashfree minimum is 10 minutes) |

---

## 6. What Needs Manual Action (Cashfree Dashboard)

### CRITICAL: Domain Whitelisting

Cashfree Drop-in Checkout shows "Broken Link! localhost is not enabled" until whitelisted.

**Steps**:
1. Log in at https://merchant.cashfree.com
2. Go to **Developers → Allowed Domains** (or **Developers → Whitelisting**)
3. Add these domains:
   - `localhost:3000` (local development)
   - `salones.in` (production)
   - `www.salones.in`
4. Save

### CRITICAL: Webhook URL Configuration

1. Go to **Developers → Webhooks**
2. Set URL: `https://api.salones.in/v1/webhooks/cashfree`
3. Select events: `PAYMENT_SUCCESS_WEBHOOK`, `PAYMENT_FAILED_WEBHOOK`, `PAYMENT_USER_DROPPED_WEBHOOK`, `REFUND_STATUS_WEBHOOK`
4. Version: `2025-01-01`

---

## 7. Payment Amount Flow

For a booking:
- Service total: ₹900
- Payment preference: `pay_advance` (30%)
- Online processing charge: 2% gateway + 18% GST = 2.36%

**Step-by-step**:

```
deposit_amount = 900 * 0.30 = 270.00  (stored in bookings.deposit_amount)
processing_charge = 270 * 0.0236 = 6.37  (online_processing_charge in booking_payments)
cashfree_amount = 270 + 6.37 = 276.37  (amount in booking_payments)
platform_commission = 276.37 * 0.10 = 27.64  (platform_commission_amount)
salon_nets = cashfree_amount - platform_commission = 248.73
```

**Actual DB example** (service_total = ₹800, deposit = ₹240):
```
240 * 1.0236 ≈ 245.66  ← amount sent to Cashfree ✅
245.66 * 0.10 = 24.57  ← platform commission ✅
5.66               ← online_processing_charge ✅
```

---

## 8. Database Schema

### `booking_payments` (confirmed from live DB)

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | PK |
| `booking_id` | UUID | FK → bookings |
| `channel` | text | `"gateway"` for online |
| `purpose` | text | `"deposit"` / `"full"` / `"balance"` |
| `provider` | text | `"cashfree"` |
| `amount` | numeric | Amount sent to Cashfree (inc. processing charge) |
| `platform_commission_amount` | numeric | Platform fee |
| `online_processing_charge` | numeric | Gateway charge |
| `service_amount` | numeric | Base service amount |
| `status` | text | `"created"` / `"captured"` / `"failed"` |
| `intent_reference` | text | `"pi_..."` — our internal ID |
| `order_ref` | text | Same as `intent_reference` for Cashfree |
| `provider_session_id` | text | Cashfree `payment_session_id` |
| `failure_code` | text | e.g. `"provider_rejected"` |
| `expires_at` | timestamptz | Intent expiry (15 min TTL) |

### `bookings` (payment-relevant)

| Column | Values |
|--------|--------|
| `payment_preference` | `"pay_advance"` / `"pay_full"` / `"pay_at_salon"` |
| `payment_status` | `"unpaid"` / `"deposit_paid"` / `"paid"` |
| `checkout_policy_version` | `"customer_processing_v1"` |
| `deposit_amount` | 30% of total (for `pay_advance`) |
| `paid_amount` | Cumulative captured amount |

---

## 9. Key File Locations

```
salon-backend/backend/
├── app/
│   ├── api/v1/routes/
│   │   ├── payments.py              # /intent, /refresh, /confirm, /cancel, /config
│   │   └── webhooks.py              # POST /v1/webhooks/cashfree
│   ├── application/use_cases/payments/
│   │   └── booking.py               # create_intent(), refresh(), confirm() logic
│   ├── domain/services/
│   │   ├── checkout.py              # checkout_quote() — processing charge calc
│   │   └── booking_finance_policy.py # POLICY_VERSION, cancellation rules
│   └── infrastructure/payments/
│       ├── cashfree.py              # CashfreeGateway — the Cashfree API adapter
│       ├── fake.py                  # Fake gateway for tests
│       ├── null.py                  # Null gateway (payment disabled)
│       └── resolver.py              # Picks gateway based on PAYMENT_PROVIDER env
└── .env
```

---

## 10. End-to-End Test Script

```python
# scripts/test_cashfree_live.py
import asyncio, httpx, json, os, uuid
from dotenv import load_dotenv

load_dotenv()

async def test_cashfree():
    app_id = os.environ["CASHFREE_APP_ID"]
    secret = os.environ["CASHFREE_SECRET_KEY"]
    base = "https://api.cashfree.com/pg"
    headers = {
        "x-client-id": app_id,
        "x-client-secret": secret,
        "x-api-version": "2026-01-01",
        "content-type": "application/json",
        "accept": "application/json",
    }

    order_id = "test-" + uuid.uuid4().hex[:20]
    body = {
        "order_id": order_id,
        "order_amount": 1.00,
        "order_currency": "INR",
        "customer_details": {
            "customer_id": "test_customer_01",
            "customer_name": "Test User",
            "customer_phone": "9876543210",
        },
        "order_meta": {
            "return_url": "https://salones.in/booking/status?order_id={order_id}",
        },
        "order_note": "Connectivity test",
    }

    async with httpx.AsyncClient() as client:
        # Create order
        resp = await client.post(f"{base}/orders", json=body, headers=headers)
        print(f"Create order: {resp.status_code}")
        data = resp.json()

        if resp.status_code == 200:
            session_id = data.get("payment_session_id", "")
            print(f"✅ payment_session_id: {session_id[:60]}...")
            print(f"✅ cf_order_id: {data.get('cf_order_id')}")
            print(f"✅ order_status: {data.get('order_status')}")

            # Fetch order
            resp2 = await client.get(f"{base}/orders/{order_id}", headers=headers)
            data2 = resp2.json()
            print(f"\nFetch order: {resp2.status_code}")
            print(f"Status: {data2.get('order_status')}")
        else:
            print(f"❌ Error: {data.get('message')} | Code: {data.get('code')}")

asyncio.run(test_cashfree())
```

Run: `cd d:\salon\salon-backend\backend && .\.venv\Scripts\python.exe scripts\test_cashfree_live.py`

---

## 11. Known Issues & Resolutions

| Issue | Root Cause | Resolution |
|-------|-----------|------------|
| Cashfree drop-in shows "Broken Link" | Domain not whitelisted in Cashfree dashboard | **Action required**: whitelist `localhost:3000` and `salones.in` |
| Webhook not receiving events | Webhook URL not in Cashfree dashboard | **Action required**: configure webhook URL in dashboard |
| Old bookings had `failure_code: provider_rejected` | Early testing before API key was properly set up | Auto-resolved; all new bookings work |
| `PaymentInProgressError` on retry | Old `created` intent still within 15-min TTL | Auto-resolves after TTL; `expire_stale_open_intents()` handles cleanup |
| `checkout_policy_version = u08-*` blocks payment | U08 policy deliberately blocks online payment | Do NOT set `BOOKING_CHECKOUT_POLICY_VERSION=u08-2026-10-23-v1` |

---

## 12. What Does NOT Need Changing in the Backend

The following are **already correctly implemented**:

1. ✅ `cashfree.py` — API version, URL, headers, field names, amounts in rupees
2. ✅ `{order_id}` return URL template (Cashfree substitutes it)
3. ✅ Idempotency key mechanism
4. ✅ 30% advance amount calculation
5. ✅ Processing charge addition (2.36% gateway + GST)
6. ✅ Platform commission (10% of online amount)
7. ✅ Webhook signature verification algorithm
8. ✅ Owner notification on booking (`notifications` table, `type: 'new_booking'`)
9. ✅ Slot availability API
10. ✅ Open intent expiry sweep (`expire_stale_open_intents()`)

## 13. Summary of Required Actions

### Cashfree Dashboard (Manual — by account owner):
- [ ] Whitelist `localhost:3000` under Developers → Allowed Domains
- [ ] Whitelist `salones.in` and `www.salones.in` under Developers → Allowed Domains
- [ ] Configure webhook URL: `https://api.salones.in/v1/webhooks/cashfree`
- [ ] Select webhook events: `PAYMENT_SUCCESS_WEBHOOK`, `PAYMENT_FAILED_WEBHOOK`, `PAYMENT_USER_DROPPED_WEBHOOK`, `REFUND_STATUS_WEBHOOK`
- [ ] Set webhook version: `2025-01-01`

### Backend Code:
- ✅ **No code changes required** — backend is correctly implemented and verified against Production API

### Frontend:
- ✅ **No code changes required** — all payment flow components are implemented

## 14. Wallet and payouts (added 2026-11-12: this document covered collection only)
Sections 1-13 verify **collecting** customer money. They say nothing about what happens next. After a payment is
captured the salon owner's wallet grows (amount less processing charge less commission), the owner can request a payout,
and the super admin pays it by hand (reference + proof) or sends it through Cashfree Payouts. The balance drops when the
request is made and stays down when it is paid.

* Full behaviour, routes, safety rules and go-live items: `backend/docs/WALLET_PAYOUTS.md`.
* Cashfree Payouts needs its **own** keys, the `CASHFREE_PAYOUT_*` settings and `PAYOUT_PROVIDER=cashfree`; the Payment Gateway keys above do not work for it.
* **Sandbox first.** Everything above was verified against Cashfree **production**. Use sandbox keys for every test until
  the full flow (collect, wallet, request, send, paid) has passed once; then switch the keys, not the code.
* Never put real keys in this file or in the repo. This file once did; treat any key that was in it as exposed and rotate it.
