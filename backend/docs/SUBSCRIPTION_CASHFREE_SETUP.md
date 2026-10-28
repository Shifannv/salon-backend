# Cashfree subscription checkout

This collects one paid subscription period for Salones, with manual renewal. It uses the existing subscription billing records, price snapshots, idempotency, verification, webhook worker and entitlement activation. Booking payments remain separately configured.

## Owner journey

1. The owner app's Choose/Renew button opens `https://salones.in/subscription/checkout?plan=<code>`.
2. The website keeps the selected code through owner sign-in. The owner must use the account that owns the salon; the app never puts authentication tokens or prices in the link.
3. The review page reads the authenticated salon's effective plan price, normal price and salon offer percentage from the backend. The normal price is crossed out above a lower offered price. Amounts preserve paise.
4. Pay calls `POST /v1/salons/me/subscription/checkout` with only `plan_id` and an idempotency key. The database snapshots the effective price before Cashfree is called.
5. The backend creates a Cashfree order and returns a public `payment_session_id` and `mode`. The website opens Cashfree's hosted checkout. A changed order price/plan blocks payment until the owner reviews it.
6. The browser outcome triggers `POST /v1/salons/me/subscription/verify`. The backend fetches provider payment records, checks the order, amount and currency, and applies entitlement once. Existing active access alone does not prove a renewal was paid.

## Configuration after the merchant account is ready

Set these on the backend and its existing webhook/reconciliation workers through the deployment's secret/configuration mechanism. Never put merchant credentials in the owner app, website public variables, Git or chat.

| Setting | Value |
| --- | --- |
| `SUBSCRIPTION_PROVIDER` | `cashfree` |
| `SUBSCRIPTION_CASHFREE_CLIENT_ID` | Merchant sandbox client ID, supplied as a secret |
| `SUBSCRIPTION_CASHFREE_CLIENT_SECRET` | Matching merchant sandbox client secret, supplied as a secret |
| `SUBSCRIPTION_CASHFREE_ENVIRONMENT` | `sandbox` initially; `production` after sandbox acceptance |
| `SUBSCRIPTION_CASHFREE_API_VERSION` | `2026-01-01` |
| `SUBSCRIPTION_ALLOW_LIVE` | `false` for sandbox; explicit `true` required for production |
| `SUBSCRIPTION_WEBSITE_URL` | `https://salones.in/subscription/checkout` |
| `PUBLIC_API_BASE_URL` | Deployed public API origin, e.g. `https://api.salones.in` |
| `SUBSCRIPTION_GRACE_DAYS` | Existing agreed policy; explicitly choose `0` if no grace is intended |

Complete Cashfree merchant activation and domain whitelisting for the actual website domain (including its canonical `www` host if used). Add the webhook `https://api.salones.in/v1/webhooks/cashfree` in Cashfree for payment success/failure/user-drop and refund status. Its signature uses the subscription client secret over the timestamp plus the unchanged raw body. Existing webhook and reconciliation workers must run with the same subscription configuration.

Do not set `PAYMENT_PROVIDER=cashfree` merely to enable subscriptions: that setting controls customer booking collection. If booking collection also uses Cashfree, it needs distinct credentials so the shared webhook intake cannot confuse booking revenue with subscription revenue. Configuration rejects identical active booking/subscription secrets.

Credentials alone do not publish this feature. Deploy the reviewed backend and website code first, satisfy the existing database migration gates, configure the webhook/domain, and complete sandbox acceptance before enabling production. This document does not authorize a deployment or migration.

## Acceptance and recovery

- Use the designated test salon. Verify normal amount, amount offer, percentage offer and selected plan in the app and website review.
- Test Cashfree sandbox success, failure, closing checkout, return/reload, double-click, delayed webhook and provider timeout. Confirm one billing record/payment and one entitlement application.
- Provider timeouts and malformed successful create responses retain the original receipt for reconciliation. Never create another order solely because the response was lost.
- Resolve old open orders before changing providers. Old-provider orders cannot be resumed or replayed through a new provider.
- Browser promises and callbacks never prove payment. A renewal succeeds only when verification confirms this order and the matching entitlement is active.
- Refund status reads are absolute and monotonic; refund events do not automatically revoke access. Existing operator policy governs access after refunds.
- Cashfree sandbox/live merchant calls are not established by local mocked tests. No live charge should be claimed before sandbox and operator-approved live acceptance.

Official contracts: [Hosted web checkout](https://www.cashfree.com/docs/payments/online/web/redirect), [Create order](https://www.cashfree.com/docs/api-reference/payments/latest/orders/create-order), [Get order payments](https://www.cashfree.com/docs/api-reference/payments/latest/payments/get-payments-for-an-order), [Create refund](https://www.cashfree.com/docs/api-reference/payments/latest/refunds/create-refund).
