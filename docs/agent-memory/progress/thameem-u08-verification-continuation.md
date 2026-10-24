# Progress: thameem/u08-verification-continuation

## Goal
Continue U08 booking logic with immutable checkout selection while Cashfree setup and production release remain held.

## Status
In progress. Atomic booking changes and terminal finance foundations are implemented locally; provider-bound execution, reconciliation resolution and production release remain unfinished.

## Done
- Final backend-first verification:1466 passed/36 skipped, one dependency deprecation warning,110 seconds; full Ruff and whitespace checks passed. No real dotenv/provider credentials used by isolated runner.
- 2026-10-24 backend-first continuation: prepared0045 SQL-owned availability/quote/atomic change commands with accepted quote fingerprint, version/idempotency checks, closure and slot races, preserved time-only price snapshots and two committed reschedule limit. Unpaid cheaper repricing and prepaid retained value work; expensive prepaid commits fail closed pending verified additional capture binding.
- Prepared0046 immutable terminal money snapshots, policy cancellation bands, provider-cost allocation, refund/reconciliation queues and MFA-protected manual finance commands. Owner payout projection omits internal split/costs. Late captures/over-refunds freeze payout; owner self-booking salon cancellation retains full-refund treatment. No provider refund/transfer is executed.
- Added separate owner can_record_payment capability for checked-in collection. U08 completion requires full payment; direct U08 customer cancellation inside four hours applies zero refund. Legacy rules remain unchanged. Thirty-three focused PostgreSQL/HTTP tests pass; full verification recorded in assessment section26.
- 2026-10-24 post-release device verification passed: user supplied QR phone ready; restarted the existing signed-in owner app without data clearing, opened Menu/QR Code and decoded its actual screenshot. Correct public customer-web /s/ destination replaced the malformed cached payload. Chrome on the same phone showed the intended salon and service with no not-found text. No booking/payment writes or native rebuild. Manual OEM camera capture was not exercised. Phone control returned; evidence owner-qr-device-result.json and owner-qr-after-release files in existing private artifacts.
- 2026-10-24 approved QR cache release executed: exact local candidate pushed, deployed at zero traffic, health/real PNG decode/website destination/anonymous401 checks passed, OpenAPI identical119paths, promoted salon-api-production-qr-cache-20261024 to100%. Public-domain checks passed after promotion. Service min0/max1 verified; inherited revision max3 remains below a service-wide cap1, with no revision minimum override. Rollback salon-api-production-qr-20261023 retained. Runtime image manifest03d755dfc70d32726c5e9eae0166774ef5f29baba69be7c73b5a30b741072044. No migration/payment/web/app/billing/VM release. Requested exclusive phone-ready reply for post-release owner QR inspection; not received at this checkpoint.
- 2026-10-24 checkpoint: full backend1431 passed/36 skipped, Ruff/diff checks passed; isolated web Playwright90 passed/2 optional visual skips; owner12 targeted tests/typecheck passed; customer18 attendance/auth/storage tests, full typecheck and focused API/storage lint passed. Two pre-existing customer UI lint errors and two warnings were proven in HEAD and remain.
- Approved production QR environment-only release completed: exact prior image, WALKIN_BASE_URL single customer-web /s URL, serving revision salon-api-production-qr-20261023, min0/max1 preserved. No other source, migration, VM or billing release. Public PNG decode/site200 and live prebooking reached OTP gate without writes.
- Actual phone owner-modal screenshot still decoded the old malformed JSON-list QR despite corrected live PNG. Corrected URL opened Mentrex/Buzz cut in Chrome on the same phone. Prepared deterministic destination-versioned QR image URL; regression failed before/pass after. Local exact-serving-image candidate salon-qr-cache-review:20261024 contains only owner.py change and passed offline runtime checks. Separate production approval requested and pending; camera re-scan remains unverified. Old malformed print/download artifacts require replacement.
- Prepared backend JWKS fetch cooldown/lock, fail-closed atomic Redis OTP send/verify limits, single-URL config validation and SALON_ENV_FILE class-level test isolation. Security source review found no remaining blocker; these patches are not in the deployed QR image.
- Prepared customer native SecureStore session migration, chunked serialized persistence, backup disabled, malformed-manifest logout recovery; reviewer rechecked recovery fix. No rebuilt native APK installed. Owner/client source now handles checked-in/no-show API states explicitly.
- Approved dependency audit metadata export executed. Owner36 findings/customer19 remain for triage; website Next16.4.3 prepared, production advisory audit0 and Playwright green, not deployed. Customer TypeScript6/openapi-typescript peer conflict remains a clean-install gate.
- Existing assessment section25 and API reference updated in place; no duplicate handoff created. Phone control returned after browser check; do not interact again without re-establishing exclusivity.
- Resumed after automatic approval review's stated retry time; approval review worked again. Preserved the user's commit 0b6ece4 and created this focused branch without committing or pushing.
- Full backend suite: 1404 passed,36 skipped,one dependency deprecation warning;194 seconds. Ruff app/tests/migrations and diff whitespace checks passed.
- Latest continuation:1416 passed,36 skipped,one dependency warning;191 seconds. Ruff passed. New prepared0044 follows0043, preserving existing snapshots and client privileges. No remote migration or provider activation.
- New server policy setting defaults to customer_processing_v1; U08 selection stamps new app/QR/manual bookings only. API creation verifies the stored version and rolls back503 if migration is missing. Reused-connection transaction-local reset and pre-migration snapshot preservation tested.
- U08 quote has no customer surcharge and reports selected version. Public/config/new-booking gates hide online payment; stored U08 intent guard blocks legacy automatic split even with provider credentials. Legacy intent pricing remains based on its stored policy.61 focused checkout/payment tests passed before the full run.
- Six HTTP-to-real-PostgreSQL E2E tests passed, including app/QR/manual booking, check-in, collection/completion and concurrent same-key completion retry with one notice. Auth extraction uses synthetic actors; no real provider or Android UI exercised.
- 47 financial-policy unit tests passed, including unpaid cheaper changes and retained prepaid funds; these helpers remain unwired.
- Fresh live health200; OpenAPI119 paths, no required no-show body, no booking-change routes. Read-only Mumbai metadata:0 Alembic rows, category/descriptions still present, no new attendance guard.
- Updated existing assessment section24, payment specification and migration policy; corrected durable U08 rules rather than creating another handoff/report.

## In progress
- Verified additional capture binding, provider refund dispatch, reconciliation resolution and coordinated customer/owner UI acceptance. Existing refund jobs record obligations only; manual payout recording does not move money.
- Remote migration history reconciliation. Scoped0043 review/test evidence does not authorize execution of the restored database's whole chain.

## Next steps
0. QR cache release and post-release owner-image/browser verification are complete. Phone control returned; re-establish exclusivity before further native checks. Preserve rollback salon-api-production-qr-20261023 and replace old malformed print/download artifacts. No additional release scope is authorized.
1. Continue expected-head/catalog/ownership/ACL proof in backend/docs/migrations/MUMBAI_FORWARD_RECONCILIATION.md using an isolated reference; do not weaken backend/app/core/migration_policy.py or stamp remote history.
2. Finish the remaining provider-bound execution and reconciliation commands following backend/docs/verification/payment-subscription-booking-spec.md. Prepared0045/0046 already implement atomic changes and terminal financial records; preserve legacy obligations and keep online providers disabled.
3. Bind verified additional captures to the exact booking/change version; test slot races, retries, failed/late payment reconciliation and reschedule counts before client wiring.
4. Coordinate tested source/API/client release with explicit production approval only after the migration/release package is concrete. Re-establish exclusive phone control before native interaction; it was returned to the user earlier.

## Decisions
- 2026-10-23: All three change-flow questions are answered: unpaid salon collection uses the new price; service changes require available time without renewed salon approval; prepaid upgrades require verified extra payment before commit.
- Existing manual/advance collections are outside the helper's unpaid path; no undocumented repricing of already-collected money.
- Local E2E coverage is backend HTTP/database evidence, not Playwright/native UI or provider sandbox acceptance.
- 2026-10-23: Cashfree account setup is still in progress. User will report secure configuration status when ready; do not ask for credentials in chat. Continue local logic independently.

## Files touched
- backend/docs/verification/CLOUD_RUN_DEPLOYMENT_ASSESSMENT_2026-10-22.md
- backend/docs/verification/payment-subscription-booking-spec.md
- backend/docs/migrations/MIGRATION_POLICY.md
- docs/agent-memory/shared/domain-rules.md
- This branch's progress file and SESSIONS index.
- Checkout domain/use case, payment use case/config/routes/schemas, repository transaction setting; prepared0044 SQL/Python; test_u08_policy_sql.py, test_u08_checkout_activation.py and migration-head tests; existing API reference.

## Blockers and open questions
- Scoped QR cache release and actual owner-device image/browser verification are complete. Full native builds/session migration, store signing, dependency triage and checked-in owner receipt capability still need completion. Cashfree and source/migration constraints below remain.
- Restored Mumbai database has empty Alembic history; no whole-chain expected-head equivalence proof or remote execution approval. Held0041 through0046 remain unapplied; portable0037/Mumbai0040 boundaries remain unchanged.
- Atomic service/time changes are prepared. Verified additional captures, refund dispatch/reconciliation resolution, provider settlement hold evidence and native financial screens remain unfinished. Local implementation does not complete U08 activation.
- No new user product question is pending from the three latest answers. Do not ask them again.
- Cashfree sandbox readiness question is answered: not set up yet. No dependent provider tests or activation can be claimed, and no credential question needs repeating now.

## Review findings
- Fixed:0045 quote-consent drift, closure lock ordering and service-role history mutation;0046 exact refund reconciliation, booking-before-outcome locks, late-capture holds and owner self-booking cancellation provenance. Migration/security review found no remaining concrete scoped blocker; neither review establishes provider execution.
- Fixed: scoped attendance guard blocks checked-in absence through both native and legacy paths; API reference explains the new required body.
- Fixed: completion replay does not schedule duplicate customer notices; completion delivery remains post-commit background work, not a proven atomic outbox guarantee.
- Read-only migration/security reviewers found no remaining concrete blocker in the scoped foundation; final service-change quote review also found none. Reviews are not remote release approvals or independent runtime tests.
- 0044 migration/security reviews found no blocker. Critical release constraint: never roll back to an API lacking the stored-U08 intent guard while collection is enabled. Keep a compatible rollback or disable collection.

## Session log
- 2026-10-24: continued backend first while Cashfree setup is incomplete; implemented/reviewed/tested0045 atomic booking changes and0046 terminal finance foundations, updated existing API handoff/report. No remote migration, provider call, production release, frontend edit, commit or push.
- 2026-10-24: verified deployed cache fix on connected phone: actual owner QR decoded correctly and its destination loaded the intended salon/service in Chrome; no data-clearing/rebuild/booking writes. Returned phone control and updated the existing assessment.
- 2026-10-24: executed explicitly approved one-file QR cache release; zero-traffic and public-domain checks passed,100%traffic/min0max1 verified, rollback retained. Phone verification requested and pending. Existing assessment/API reference updated; no source commit or unrelated release.
- 2026-10-24: continued release audit; executed approved QR URL-only release, reproduced stale QR bytes on actual owner screen, prepared isolated one-file cache fix and requested separate release approval; security/client tests green as above. No financial migration or online provider activation, commit or push.
- 2026-10-23: resumed local verification, confirmed live/source mismatch, saved all three change decisions; no remote mutation, build/install, commit or push.
- 2026-10-23: Cashfree setup deferred by user; added/reviewed/tested immutable checkout binding and no-surcharge U08 quotes with collection blocked. Full1416pass/36skip; no remote mutation or release.
