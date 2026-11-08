# Date of birth and guardian approval (migration 0065)

## Rules
- Customers give a date of birth once. It can be set once; a different date later needs a support correction, so a teenager cannot turn themselves into an adult.
- Under 13: refused (`under_minimum_age`), nothing is stored.
- 13 to 17: may use the app, but cannot create an app booking until a parent or guardian approves (`guardian_consent_required`).
- 18 and over: no extra step.
- No date of birth on file: app bookings are refused (`birth_date_required`).
- The age is worked out on the server from the date of birth, in Indian time, so approval ends by itself at 18.
- Owners, staff and the admin are not checked. QR walk-in and salon-entered walk-in bookings are not checked.

## Endpoints (all authenticated)
| Method and path | Purpose |
|---|---|
| `GET /v1/age/status` | age band, whether booking is allowed and why not, guardian state. Never returns the date of birth |
| `PUT /v1/age/birth-date` | save the date of birth once |
| `POST /v1/age/guardian` | text a 6-digit code to the guardian's phone (13 to 17 only) |
| `POST /v1/age/guardian/verify` | the guardian reads the code out; a correct one approves |
| `DELETE /v1/age/guardian` | withdraw the approval, or drop a pending request |

## How the guardian is checked
The backend makes its own 6-digit code, keeps only a keyed hash of it and of the guardian's number (plus the last 4 digits for display), and sends the code through the messaging gateway. Codes last 10 minutes, allow 5 wrong tries, and at most 5 are sent per person in 24 hours across all requests, with a 60 second gap. The guardian never gets an account.

This proves that someone controls a phone. It cannot prove that the person is the child's parent. If you need stronger proof later, add a step on top of this one.

## Switching it on safely
Old customer-app builds have no screen for these answers. Once the gate is on, an old build that tries to book gets a refusal it cannot act on. Roll out in this order:
1. Apply migrations 0064 and 0065.
2. Deploy the API with `AGE_GATE_ENFORCED=false`.
3. Ship the new customer app and wait for people to update.
4. Set `AGE_GATE_ENFORCED=true`.

## Sending codes
No SMS provider is connected yet (`MESSAGING_PROVIDER=none`), so real codes are not sent. The customer app then tells teenagers that approval is coming soon and bookings stay locked. Until MSG91 is connected you can test with fixed codes:

```
GUARDIAN_TEST_OTPS=+919999999999=123456
GUARDIAN_TEST_OTPS_UNTIL=2026-11-30T00:00:00+05:30
```
Test numbers are never texted. Outside local and test, the expiry setting is required and the codes stop working after it.

When MSG91 is ready, add an adapter under `app/infrastructure/messaging/` and register it in `app/infrastructure/messaging/resolver.py` and in the provider check in `app/core/config.py`.

## Erasure
`guardian_consents` rows are removed with the profile (`ON DELETE CASCADE`).
