# Per-salon trial configuration

Implemented locally on 29 October 2026. This feature has not been deployed and no real salon trial has been changed during implementation.

## Approval

`POST /v1/admin/salons/{salon_id}/approve` accepts an optional body:

```json
{"trial_days": 14, "trial_booking_limit": 75}
```

The existing verified super-admin/MFA gate applies. Empty or omitted configuration retains the existing trial policy; when a body is supplied its defaults are 60 days and 500 bookings. A custom allowance is applied inside the approval transaction, after the existing trigger initializes the trial. It is visible only once both writes commit. If either fails, approval and trial initialization roll back together.

Approval retries and re-approval preserve an already-started trial's dates, limit and usage, even if a different initial allowance is submitted. Later adjustments use the dedicated trial endpoint.

## Existing trials

- `GET /v1/admin/salons/{salon_id}/trial`: configured duration, booking allowance, start/end timestamps, counted usage, quota marker and server-derived state (`not_started`, `active`, `expired`, `quota_reached`). For an unstarted trial the response supplies the defaults for approval.
- `PUT /v1/admin/salons/{salon_id}/trial`: requires **both** `trial_days` and `trial_booking_limit`. Integers only, respectively 1–3,650 and 1–1,000,000. Extra fields, booleans, strings and fractions are rejected. A partial edit cannot reset the other allowance silently.

Duration always means total days from the original start, not extra days from the edit time. Changes preserve the original start and never reset counted bookings. Because exhausted counters can have stopped at an earlier quota, the update performs a bounded recount and preserves at least the old count. The existing quota/time exhaustion markers are updated consistently, allowing an extended trial to work with the current `salon_booking_eligible` rules. A smaller allowance can end a trial immediately. Subscription records, billing amounts, paid periods and payment verification are untouched.

The editor refuses inactive salons and trials that have not started. A pending salon's initial limits are chosen at approval; the subscription editor cannot start a trial or bypass salon approval. Every write targets the selected salon UUID and uses the verified actor for audit. Salon locks use `FOR NO KEY UPDATE`, compatible with the booking foreign key's key-share lock; access rows are locked against concurrent booking updates. Audit events use the existing subscription event store.

## Clients

The website super-admin approval dialog loads server defaults before enabling custom inputs. With an older backend that lacks trial settings, it shows that customization is unavailable and sends no custom limits; approval continues to use that server's existing policy. Transient errors block confirmation rather than guessing an allowance.

Under Subscriptions, the selected salon has a Trial allowance editor and a review/confirmation step explaining preserved usage and possible immediate expiry. Unstarted trials link to the salon approval page. Cache keys include the selected salon and authenticated admin.

Owner app and website continue reading their authenticated `GET /v1/salons/me/access-state`; they cannot submit trial limits. They display server-provided dates, booking usage and the assigned allowance. The app refreshes these reads on entering Subscription. Both clients correctly show restored trial access when a historical paid subscription has expired, while an active paid entitlement retains precedence. Limits remain in the salon's database record across owner sign-out/sign-in.

## Release and verification

No schema migration or function replacement is needed: the implementation reuses the existing `salon_access`, booking eligibility logic and event store. Do not change historical migration files, rerun 0049, upgrade Alembic to head, or deploy the unrelated dirty finance work to enable this feature.

Real disposable PostgreSQL coverage proves custom first approval, idempotent retries with preserved usage, rollback on a failed allowance write, quota recovery and tenant isolation, refusal to start a trial from the editor, paid-plan preservation and booking-lock compatibility. Unit/HTTP checks cover super-admin authorization, anonymous denial and strict input validation. Frontend tests cover approval payloads, confirmation, invalid limits, unstarted trials, custom owner display and restored-trial presentation. Deployment and live screen acceptance remain separate from these local tests.

Final checks: backend full unit suite **1,654 passed** and full Ruff clean; **six** real PostgreSQL integration tests passed (78 combined targeted tests including authorization/approval/MFA). Website **554 tests / 40 files** passed, scoped ESLint clean and production build/typecheck passed. Owner **29** focused logic/screen tests passed; its expired-paid-plan/restored-trial regression failed before the display fix and passed afterward. Owner typecheck/scoped lint passed. No new APK was installed: the app has unrelated ongoing finance changes that are outside this trial task.
