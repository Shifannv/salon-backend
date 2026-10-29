# Cashfree verification — 29 October 2026

## Result

Production credentials appear to authenticate successfully. Payment collection is not yet verified end to end and remains disabled on the deployed API. No order, charge, refund, database mutation, production configuration update, or frontend activation was performed.

## Evidence

- Loaded the user-updated local credentials in process memory only; no credential values were printed or saved.
- Local configuration selects `PAYMENT_PROVIDER=none`, `CASHFREE_ENABLED=true`, and `CASHFREE_ENV=sandbox`.
- Read-only lookup of a randomly generated nonexistent order against sandbox: HTTP 401, `authentication_error`, `request_failed`.
- Same kind of read-only lookup against production: HTTP 404, `invalid_request_error`, `order_not_found`. This is evidence that production authentication passed; it does not prove order creation, payment capture, settlement, or webhook processing.
- Public deployed `GET https://api.salones.in/v1/payments/config`: HTTP 200, `enabled=false`, `provider=null`.
- Actual local settings validation fails for `EMAIL_WORKER_POLL_SECONDS` (not a valid integer) and `WALKIN_BASE_URL` (multiple URLs instead of one).
- Temporary process-only overrides for those two settings allow validation and confirm booking collection is disabled. A further process-only activation check selecting Cashfree production with live acknowledgement fails because `PAYMENT_COMMISSION_BASE` is missing. Environment files were not modified.
- Easy Split is not explicitly configured locally. Its merchant entitlement and active salon settlement accounts were not checked. The documented booking model requires provider-side split settlement; do not enable broad salon collection until that path is verified.
- Subscription billing is independent: local `SUBSCRIPTION_PROVIDER=none` and separate subscription credentials are absent. Booking credentials alone do not activate owner subscription checkout.

## Local regression checks

From `backend/`:

- `./.venv/Scripts/python.exe -m pytest -q --basetemp=.artifacts/pytest-cashfree-20261029`: exit 0; 1592 passed, 180 skipped, one Starlette/AnyIO deprecation warning; 52.24 seconds.
- `./.venv/Scripts/python.exe -m ruff check app tests migrations`: exit 0; all checks passed.

These tests use the repository's isolated test configuration and fake/mock payment adapters. Skipped integration tests do not verify the live database or provider.

## Activation prerequisites

1. Correct the two invalid local settings, select the matching Cashfree environment, and supply the approved commission base. Production additionally requires explicit live activation settings.
2. Verify Cashfree Easy Split entitlement and each participating salon's active settlement account; separately configure subscription billing if required.
3. Reconcile the intended deployed backend source/schema and worker readiness before releasing payment functionality. A local environment edit does not update the Cloud Run runtime configuration.
4. Exercise a controlled checkout using an authenticated test customer and an approved salon: create/resume an order, complete payment, refresh server status, verify signed webhook processing and ledger reconciliation, then verify refund/settlement behavior.
5. Enable and exercise the customer, owner, and website integrations in their separate repositories only after backend payment acceptance. No frontend repositories were changed during this verification.

Provider reference used for the read-only probe: https://www.cashfree.com/docs/api-reference/payments/latest/orders/get-order

## Backend activation follow-up

The user requested backend-only enablement and further verification, including a platform/browser connection if useful.

### Additional checks

- Rechecked current local settings: the same email polling and walk-in URL validation errors remain; booking provider remains `none` and Cashfree mode remains sandbox.
- Repeated production authentication with a control: credentialed nonexistent-order lookup returns 404 `order_not_found`; unauthenticated lookup returns 401 `authentication_error`. This supports production credential validity.
- Production Easy Split nonexistent-vendor lookup returns 400 `api_request_failed`, message `vendor does not exist`. It does not establish entitlement, an active vendor, deferred settlement, or release controls.
- Rechecked deployed health and payment configuration: HTTP 200/healthy; collection disabled.
- No Cashfree plugin was found by the connected plugin search. The available connected browser opens the merchant URL but redirects to the Cashfree login page. The user's existing desktop login is not present in that browser. Requested interactive sign-in and separate sandbox configuration; neither was available during these checks. Never send login credentials or OTPs in chat.
- Full backend suite rerun: **1615 passed, 180 skipped**, one existing Starlette/AnyIO deprecation warning, exit 0, 79.23 seconds. Ruff: all checks passed, exit 0. Counts refer to the source present at execution time.
- Created a separate task-labelled PostgreSQL 18 container on `127.0.0.1:55439`, using disposable test credentials and no live data. Ran `test_payment_ledger_sql.py`, `test_checkout_safety_sql.py`, `test_subscription_billing_sql.py`, `test_booking_finance_sql.py`, and `test_u08_policy_sql.py`: **71 passed**, exit 0, 60.20 seconds. The test-created container was stopped after verifying its exact ID and task label. These SQL checks supplement the full run; they do not convert every skipped test into a pass.

### Activation finding

The latest U08 policy supersedes legacy immediate splits and customer surcharges. It requires provider-controlled held funds, service completion, and admin-approved release. `app/domain/services/checkout.py:online_checkout_available` deliberately refuses to advertise U08 collection, and `app/application/use_cases/payments/booking.py:create_intent` rejects U08 before calling a gateway. `tests/unit/test_u08_checkout_activation.py` verifies that adding credentials cannot enable this policy. The existing Cashfree adapter still sends static `order_splits` at order creation and does not implement the approved held-funds/release workflow.

Therefore selecting `PAYMENT_PROVIDER=cashfree` is insufficient for the requested approved booking flow. Do not bypass these guards or select the legacy surcharge policy merely to make the enabled flag true. Provider merchant acceptance and the missing held-funds/release implementation must precede production activation. Correcting the local settings alone cannot complete this work.

No payment was charged, no order/refund was created, and no application code, environment file, production setting, database schema, or frontend repository was changed.
