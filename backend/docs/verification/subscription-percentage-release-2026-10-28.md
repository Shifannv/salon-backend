# Subscription percentage release and owner-session verification

Completed on 28 October 2026. The user authorized deployment and live verification on Mentrex, then requested verification of the same owner/salon identity after leaving the website and logging out and in again.

## Serving release

- Production: `salon-api-production-subpct-20261028`, 100% traffic.
- Private staging: `salon-api-mumbai-staging-subpct-20261028`.
- Image: `asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:ee92c2f588acbab37e905162cc8346d5eeea387046521db4c2c52eb717858f69`.
- Production rollback: `salon-api-production-api-domain-20261027`.
- Scope: nine application files over the previously serving image `sha256:dfb24746323e9d4cfa2a4fd9cff7d0fee1d7a02ee5d0893a8a436f9f3cfbcef1`. Subscription files came from `d93ba0a`; configuration adds only the checkout URL field/validation, and the shared row helper is included. The broad subsequent refactor and Cashfree adapter are excluded.
- The website percentage controls were already published in production commit `33896ba0835441605b2252e7e1fa2abe07297fcd`; no website deployment was needed. Actual production owner checkout was exercised on Android Chrome.

## Database and configuration

Migration 0049 already existed and was not rerun. Only the existing additive `0050_plan_price_valid_until.sql` was applied, in a transaction with lock/statement timeouts. The original offer table was encrypted, decrypted and hash-verified before applying it. Backup manifest: `%LOCALAPPDATA%/SalonRecovery/subscription-percentage-20261028T174304534274Z/backup-manifest.json`. Alembic history was not upgraded or stamped. All plan prices and existing trials were preserved.

Both revisions expose `SUBSCRIPTION_WEBSITE_URL=https://salones.in/subscription/checkout`; both website origins are retained in CORS. Existing secrets, resources, scaling and identities are preserved. Billing remains disabled. No merchant settings, payment, manual activation, store release or OTA publication occurred.

## Verification

- Exact candidate: 95 subscription tests passed, scoped Ruff passed with project configuration, image built and offline OpenAPI/configuration smoke passed. Staging and the zero-traffic production candidate passed health, database, Redis, percentage input/output, offer route, owner-auth rejection and both CORS checks. Staging remained private. Both `api.salones.in` and `apiv1.mudassirmhd.in` passed after promotion.
- Existing local signed-in super-admin UI called the production API. For Mentrex Growth Monthly, entering 20% calculated and saved INR 399.20 against the current normal INR 499. Native owner app and website review displayed the crossed-out normal price, offered amount and 20% badge.
- Entering INR 349.30 calculated/saved 30%. Native app and production checkout opened by Choose Growth displayed the same plan, INR 349.30 and 30%. No payment started.
- The actual production browser's authenticated owner UUID and salon UUID matched the database; only hashes were recorded. Mentrex has one active salon for that owner. The exact deployed `find_owner_salon_id` resolves the authenticated owner UUID, and offer SQL joins by that salon UUID and plan UUID.
- A new temporary 20% offer was checked before and after a full Android Chrome restart: identical owner, salon and plan UUIDs, INR 399.20 and 20%.
- Website logout used its existing local owner-realm signout. Private plan reads then returned 401 and the selected checkout code survived the login redirect. The user signed in again on the phone. Fresh authenticated reads returned the same owner/salon/plan UUIDs and 20% offer; a page reload visibly rendered INR 399.20 with INR 499 crossed out.
- A read-only execution of the exact deployed repository SQL confirmed that another salon and an unscoped plan read still receive INR 499 with no custom offer. This is database isolation evidence, not a second live owner login.

## Cleanup and remaining boundaries

Temporary overrides were restored to the original state: no override. Browser input for removal was unreliable, so cleanup used guarded transactions restricted to the exact test salon, plan, amount, time range and no expiry; verification cleanup events were appended without impersonating a super-admin. Final read-only database verification confirmed zero overrides, all six plan prices unchanged and Mentrex's original INR 499 monthly price. Fresh signed-in website and native app restoration checks are recorded in the private evidence directory.

Private scripts, receipts, UUID hashes and selected screenshots: `salon-owner-APP/.tmp/subscription-release-20261028/` and `.tmp/subscription-live-20261027/percentage-*.png`. No tokens, cookies, passwords or OTPs were extracted or persisted. Standard USB Chrome inspection was disconnected after use.

The broader source branch's existing `is_owner_or_staff` NameError was excluded by using the serving-image overlay; it was not silently released or fixed. Cashfree merchant acceptance and its separate code/configuration release remain pending; see `../SUBSCRIPTION_CASHFREE_SETUP.md`. Amount/percentage offers are now deployed and live-verified.
