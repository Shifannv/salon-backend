# Provider-independent payments: mock implementation

Date: 2026-10-18 (Asia/Calcutta). Branch: `thameem/provider-agnostic-payments`.
Scope: provider interfaces and isolated fake orchestration, not financial-policy
activation, production readiness or verified Cashfree settlement.

## Implemented with mock provider

- Five application ports: `PaymentProvider`, `RefundProvider`, `PayoutProvider`,
  `WebhookVerifier`, `ProviderFeeReconciler` in
  `app/application/ports/payment_provider.py`.
- Existing `PaymentGateway` composes collection/refund/webhook ports, retaining
  its established adapter/use-case contract and optional onboarding methods.
  Existing real adapters gain no payout or fee-reconciliation capability merely
  through payment support. Resolver capability access fails closed.
- `app/infrastructure/payments/fake.py` supplies a network-free `FakeProvider`:
  deterministic `fake_*` references, request-bound idempotency, explicit synthetic
  capture/refund/payout outcomes and timeout-after-accept reconciliation. Narrow
  payment/refund ports expose optional deterministic references and lookup; the
  payout port supports lookup by the original persisted idempotency key when no
  response/provider reference was received.
- Raw-byte HMAC authentication, strict mock event normalization and two checked-in
  deterministic webhook fixtures under `tests/fixtures/providers/fake/`.
  The signing key is public test material, not a provider credential. Fake signed
  events are accepted only under provider `fake`, never another provider's path.
- Independent nullable fee fields: `gateway_fee`, `gateway_fee_tax`,
  `easy_split_fee`, `settlement_fee`, `payout_fee`, `refund_fee`. Unknown is NULL;
  zero requires an explicit synthetic observation. No tariff or tax is estimated.
- Independent `provider_transfer_reference` and `provider_settlement_reference`
  in typed observations, hidden from repr. No reference is inferred from another.
  Mock observations have `evidence_source=mock`, and `provider_verified` cannot be
  set true. A missing observation has unknown evidence and NULL components.
- Existing payment/webhook use cases run against the shared fake provider and an
  in-memory test ledger. Tests cover creation/replay, authorized customer access,
  webhook/worker capture, pending refund, explicit processing and refund replay.
  Simulated payout acceptance is processing, never automatically successful.

No new public endpoint or API response contract is introduced. No database
repository claims durable storage of the new fee/payout observations. In-memory
fake idempotency is not database locking, durable eligibility/reservation, RLS,
encryption, audit compliance or account-erasure verification.

## Feature flags and isolation

Defaults remain `PAYMENT_PROVIDER=none`, `PAYMENT_FAKE_ENABLED=false`,
`CASHFREE_ENABLED=false`, `PAYMENT_ALLOW_LIVE=false`. No environment file is read
or edited by this work; actual runtime settings are not asserted.

Explicit local/test construction uses `PAYMENT_PROVIDER=fake`,
`PAYMENT_FAKE_ENABLED=true`, `ENVIRONMENT=test` (or isolated local), disabled
live/provider enablement and an explicit approved commission configuration.
Tests supply zero commission for synthetic service examples. Setting fake in
staging/production, mixing live/provider flags or omitting opt-in fails validation;
the factory repeats the guard for settings copied without validation. Fake
payment configuration does not activate the existing Cashfree adapter.

Even a local fake API must be isolated from shared data: never point it at Mumbai
or another persistent database. Tests override repositories and use no sockets
to reach providers. No Cashfree credentials are created, requested or used by the
new mock implementation. Existing adapter unit tests retain their historical
MockTransport-only fixtures; they are not provider-account evidence.

## Migrations prepared

The [eight migration designs](../migrations/payment-subscription-booking-designs/README.md)
remain provisional 0041-0048, not executable revisions. 0041 now maps the six
application fee fields to separate evidence components and explicitly rejects
mock observations as real reconciliation proof. 0043 now specifies distinct
encrypted transfer/settlement reference columns, separate from operation IDs.
The other designs preserve cancellation, schedule, staff, subscription, closure
and audit approval gates. No new table, SQL sidecar, Alembic revision or migration
policy exception is implemented. Repository head remains 0040; portable SQL CI
target remains 0037. Existing baseline/revision/sealed-review files are untouched.

## Blocked pending Cashfree account / requiring provider verification

| Work | Status and dependency |
| --- | --- |
| Real authentication, sandbox checkout/refund, signed delivery samples | Blocked pending Cashfree account; requiring provider verification |
| Actual six fee categories, GST/additional taxes, inclusive fees and invoice/statement allocation | Blocked pending account pricing/statements; requiring provider verification; no assumed percentage |
| Easy Split entitlement, vendor/KYC lifecycle and hold-until-completion/dispute eligibility | Blocked pending account/product capabilities; requiring provider verification; mock advertises no such capabilities |
| Provider-funded settlement versus separate payout, manual funding and cross-method duplicate transfer identity | Blocked pending account/product selection; requiring provider verification; no real payout executor enabled |
| Daily/weekly/monthly schedules, cutoffs, calendars and weekend availability | Blocked pending account-specific capabilities; requiring provider verification; no schedule defaults |
| Final transfer/refund status, failure/reversal/unknown outcomes, webhook replay semantics | Implemented with mock provider for local orchestration only; requiring provider verification before real integration |
| Provider-reference retention, destination encryption/tokenization, rotation and erasure | Requires Q15/Q16, provider capability and legal/security review; mock storage does not resolve it |

Account access does not choose business policy. Refund formula/base and cutoff
equality, fee bearers/reserves, dispute hold, payout authority/limits, trial cap,
grace/expired receipts, renewal/consent, staff rules and closure/reschedule policy
remain the specification's Q01-Q16 approvals. No 48-hour hold, seven-day grace,
Easy Split schedule or exact fee becomes active through this mock implementation.
Existing legacy surcharge/commission behavior is preserved pending its reviewed
versioned migration; this interface work does not claim to implement all C01-C16.

## Verification

The focused mock tests exercise in-process component integration only, not a
real database. Database/Redis opt-in targets are removed from the test subprocess
environment; runtime `.env` loading is disabled and dormant provider defaults
are supplied explicitly. No migration, stamp or SQL execution is authorized.

Verification results:

- 34 new fake-provider checks pass (unit and in-process integration).
- 124 focused mock/provider compatibility checks pass, including existing null,
  reference-adapter and provider-isolation tests.
- Full suite: 1,016 passed, 82 skipped, one pre-existing failure. Database/Redis
  opt-in suites were disabled; skipped SQL tests are not migration evidence.
- `python -m ruff check --no-cache app tests migrations`: all checks passed.
  `--no-cache` avoids an existing local Ruff cache permission error.
- Local `alembic heads`: unchanged single head `0040_fastapi_only_access`.
- One existing Starlette/AnyIO deprecation warning remains.

The full-suite failure is
`tests/unit/test_migration_tool_paths.py::test_offline_bundle_matches_sealed_files`.
The sealed-bundle CSV comparison reproduces a CRLF/LF mismatch using
unchanged HEAD tooling. Normalizing newlines makes the generated/sealed bytes
equal; sealed evidence is deliberately not edited or regenerated in place.

Security review found no exploitable blocker within isolated local/test scope.
Extra signed-invalid payload cases cover provider identity, currency, unsupported
settlement events, reference shape/presence and float amounts. Mock tests and this
review establish no provider settlement verification or migration execution readiness.
