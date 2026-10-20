# G04: Payout/dispute records

**Design only; Approval required for implementation.** Review group G04.
Schema dependencies: G01, G02, G03. No Alembic revision ID or parent is assigned.
The filename is a historical locator, not execution order. Inherits the
[shared rules](README.md), [field treatments](ERASURE_CLASSIFICATION.md) and
[G09 concurrency contract](09-slot-hold-concurrency-support.md).

## Purpose and compatibility

C05/C06 require one eligibility/reservation path for manual and automatic
execution and verified transfer outcome before paid status. A vendor registration,
settlement webhook or current earnings `online_net` is not a payout entitlement.
Reuse existing payment/refund evidence, provider-account onboarding generation,
G02 postings and G03 cancellation outcomes. Existing scalar commission and
provider anomalies remain historical; no automatic payout/backfill is proposed.

## Tables and columns

G01 already defines commands, authorities, approval contexts/decisions, event
identities and audit seals. This group installs the payout/destination/dispute
FK extensions on those parents only after its own tables exist, including
same-command/execution-generation composite bindings. No future payout FK is
required to install the initial G01 foundation. New-mode transfers remain blocked
until all cyclic approval/generation links and G02 accounting seals are validated.

| New table | Proposed columns in addition to shared ID/timestamps |
| --- | --- |
| `payout_destination_versions` | `salon_id uuid` -> salons, `version integer`, `provider text`, `provider_account_scope uuid`, `provider_environment text`, `provenance text`, `registration_generation integer`, `destination_ciphertext bytea?`, `provider_token_ciphertext bytea?`, `key_version text?`, `destination_digest bytea`, `verification_state text` (unverified/verified/revoked), `verified_at timestamptz?`, `evidence_digest bytea?`, `is_active boolean`; versioned facts plus revocation projection |
| `salon_financial_entitlements` | `salon_id uuid` -> salons, `booking_id uuid` -> bookings, `salon_counterparty_key uuid`, `source_event_id uuid` -> sealed financial_events, `source_posting_id uuid` -> financial_postings, `provider text`, `provider_account_scope uuid`, `provider_environment text`, `provenance text`, `kind text` (completed_service/cancellation_compensation/reversal_recovery), `amount numeric(18,2)`, `currency text`, `completed_at timestamptz?`, `hold_policy_version text?`, `hold_until timestamptz?`, `funding_channel text` (provider_settlement/manual_bank), `eligibility_version integer`, `is_blocked boolean`; amount/source immutable, eligibility a revocable projection |
| `booking_financial_disputes` | `salon_id uuid` -> salons, `booking_id uuid` -> bookings, `payment_id uuid?` -> booking_payments, `scope_code text`, `disputed_amount numeric(18,2)?`, `currency text`, `status text` (open/under_review/resolved_customer/resolved_salon/dismissed), `opened_at timestamptz`, `resolved_at timestamptz?`, `opened_by uuid?`, `version integer` |
| `booking_financial_dispute_events` | `dispute_id uuid` -> disputes, `event_key text`, `event_type text`, `from_state text?`, `to_state text`, `effective_at timestamptz`, `actor_id uuid?`, `reason_code text`, `evidence_ciphertext bytea?`, `key_version text?`, `financial_event_id uuid?` -> financial_events; `command_audit_event_id uuid` -> G01 sealed audit event for new-mode commands |
| `salon_payouts` | `salon_id uuid` -> salons, `destination_version_id uuid` -> destinations, `amount numeric(18,2)`, `currency text`, `method text` (provider_settlement/manual_bank), `status text` (eligible/approved/scheduled/processing/paid/failed/reversed), `eligibility_digest bytea`, `current_execution_generation integer?`, `scheduled_for timestamptz?`, `idempotency_digest bytea`, `correlation_id uuid`, `requested_by uuid?`, `paid_at timestamptz?`, `version integer`; no mutable approval pointer is historical authority |
| `salon_payout_generations` | `payout_id uuid` -> payouts, `execution_generation integer`, `command_id uuid` -> G01 commands, `amount numeric(18,2)`, `currency text`, `destination_version_id uuid` -> destinations, `provider text`, `provider_account_scope uuid`, `provider_environment text`, `provenance text`, `reservation_set_digest bytea`, `approval_generation_id uuid?` -> G01 approval generations (indexed FK installed here); immutable execution instruction |
| `salon_payout_reservations` | `payout_id uuid` -> payouts, `entitlement_id uuid` -> entitlements, `reservation_generation integer`, `amount numeric(18,2)`, `state text` (held/consumed/released), `reserved_at timestamptz`, `finalized_at timestamptz?`; amount/source immutable, state is a guarded projection |
| `salon_payout_attempts` | `payout_id uuid` -> payouts, `execution_generation integer` -> matching payout generation by composite FK, `attempt_no integer`, `provider text?`, `provider_account_scope uuid`, `external_operation_digest bytea`, `confirmed_transfer_digest bytea?`, `external_reference_ciphertext bytea?` (operation identity only), `provider_transfer_reference_ciphertext bytea?`, `provider_settlement_reference_ciphertext bytea?`, `key_version text?`, `status text` (prepared/submitted/unknown/confirmed/failed/reversed), `submitted_at timestamptz?`, `effective_at timestamptz?`, `observed_at timestamptz?`, `transfer_evidence_ciphertext bytea?`, `verified_by uuid?`, `version integer` |
| `salon_payout_events` | `payout_id uuid` -> payouts, `attempt_id uuid?` -> attempts, `event_key text`, `event_type text`, `from_state text?`, `to_state text`, `effective_at timestamptz`, `observed_at timestamptz`, `actor_id uuid?`, `reason_code text`, `financial_event_id uuid?` -> financial_events, `correlation_id uuid`; `command_audit_event_id uuid` -> G01 sealed audit event for new-mode commands |

Extend G02 `provider_charge_allocations` with nullable indexed `payout_id` FK
to payouts, widening exactly-one-target validation to payment/refund/payout.
Transfer/evidence material is encrypted separately from immutable event amounts;
no bank account number or UTR is copied to audit text. Key/retention design is
not approved by proposing these columns.

The application fields `provider_transfer_reference` and
`provider_settlement_reference` map to distinct encrypted columns above. Neither
is inferred from an order/vendor/other reference. A reference alone proves no
final settlement. Local `FakeProvider` observations are explicitly mock evidence,
not provider confirmation, and cannot populate verified production outcomes.

## Indexes and constraints

- Unique destination `(salon_id, version)`, entitlement source posting (one
  entitlement per approved salon-payable posting), payout idempotency digest,
  payout generation `(payout_id, execution_generation)` and generation command ID,
  reservation `(payout_id, entitlement_id, reservation_generation)`, attempt `(payout_id, attempt_no)`,
  external operation `(provider_account_scope, external_operation_digest)` and
  event keys. A partial unique index on non-NULL `confirmed_transfer_digest`
  prevents attaching the same confirmed transfer to multiple payouts/attempts.
  Its approved canonical identity must include actual funding-account namespace,
  bank rail and final transfer reference across provider/manual observations;
  method-specific digests cannot prove cross-method deduplication. P06/Q13 must
  establish this mapping before either method is enabled. Missing final identity
  cannot authorize paid status; replay updates the same attempt observation.
- Index every FK; entitlements `(salon_id, hold_until)` where not blocked,
  disputes `(booking_id, status)` for active states, payouts `(salon_id, created_at)`
  and `(scheduled_for)` for approved/scheduled states, attempts `(updated_at)` for
  submitted/unknown, reservations `(entitlement_id, state)`, events by parent/time.
- Finite positive amounts, INR, valid state/timestamp combinations, paired
  ciphertext/key versions, positive sequence numbers and cross-salon/currency
  relationships. An entitlement's source posting must be salon payable,
  gateway-funded and not already provider-settled; direct cash/UPI is excluded.
- The source event must be exactly `source_posting_id.event_id`, be sealed and
  match the entitlement's booking, salon, currency, account/environment and
  provenance. The posting must be a positive credit in the approved salon-payable
  account for exactly `salon_counterparty_key`; its magnitude equals entitlement
  amount. Thus amount cannot exceed the source posting. A partial transfer uses
  a smaller reservation, not a larger/repriced entitlement. Composite source
  posting/event keys and same-parent validators enforce these relationships.
  Corrections/reversals create compensating sealed events and separately sourced
  entitlements only for newly recoverable funds. A reversed or superseded source
  cannot authorize another entitlement without this funding proof.
- Use the shared lock-order contract before locking entitlements/payouts; no
  repository may lock a payout first and then acquire booking/subscription gates.
  Common eligibility checks approved activation, current verified KYC,
  destination generation, applicable completed-service or separately
  finalized cancellation entitlement, bound elapsed hold, active disputes,
  fee/refund reserves, funding product and available actual funds. NULL hold
  policy/time is blocked, not zero hours. Scheduling/approval never shortens it.
- Locking/deferred triggers enforce a lifetime invariant: held + consumed amounts
  per entitlement cannot exceed its immutable `amount` from the original eligible
  source posting. Separately derive signed current funding balance from G02
  posted captures, charges, refund/dispute obligations, actual payouts and
  recoveries for that funding scope. New spendable funds equal that balance
  minus still-held reservations; consumed payouts already lower the posted
  balance and are not subtracted twice. Only new reservations require sufficient
  current spendable funds. Payout amount equals its held/consumed reservation sum
  while approved/processing/paid; released reservations cannot fund a transfer.
  Partial reservations obey both lifetime and current-funding checks. Unique
  keys alone cannot enforce aggregate conservation; account mapping and reserve
  recognition remain explicit Q04/Q13/Q16 approval gates.
- Require positive reservation generations and at most one held reservation per
  `(payout_id, entitlement_id)`. A retry retains released reservation rows and
  creates the next generation only after verified nonmovement/reconciliation and
  renewed approval. Lifetime/funding checks aggregate held/consumed reservations
  across every generation; released rows remain historical evidence rather than
  spent funds. Consumed generations cannot be reused, hidden or released.
- Every reservation's `reservation_generation` is its payout's execution
  generation, with composite FK to `salon_payout_generations`. All reservations
  in an execution set share payout, currency, destination and funding scope;
  individual amounts may be partial. The sealed set digest is immutable.
  Sum reservations equals generation
  amount and payout amount. No active set may mix generations. Install the
  payout's nullable current-generation FK after both tables exist; it selects
  a projection, never changes the generation's instruction or approval history.
- One external operation identity per execution generation; one generation per
  `(payout_id, execution_generation)` and one nonterminal attempt per payout.
  An attempt binds the exact generation/command, reservation digest and G01
  approval generation. Unique `(payout_id, execution_generation)` on attempts
  means a network retry reuses the same attempt/reference rather than creating
  a second submission record. A new generation requires verified nonmovement,
  re-evaluated funds and a new approved command; old generations/approvals remain.
  No generation lacking mandatory G01 approval/audit linkage may be submitted.
  Construct cyclic generation/approval links in one guarded transaction: a NULL
  approval link may be assigned exactly once to its matching context before the
  instruction is usable. After that binding, neither link nor instruction may
  change; a later approval context requires a new execution generation.
- At most one prepared/submitted/unknown attempt per payout. Commit the intent
  and reservations before external I/O. A timeout is unknown/processing with
  reservations held; retry reconciles the same reference. Failed only releases
  funds after verified nonmovement and an explicit release event. Consumed is
  never reset to released. Verified reversal appends accounting evidence and,
  only if funds are actually recoverable, a separately sourced entitlement.
- Paid requires amount/currency/destination-matched final provider confirmation,
  or independently verified manual evidence under approved controls. Approval
  alone is insufficient; a canonical confirmed-transfer digest is mandatory.
  A newly opened dispute and transfer initiation serialize
  on the same booking/entitlement locks; later disputes become explicit recovery
  obligations. Partial reversals are ledger events; whole-row reversed requires
  the full confirmed amount, never silently discarding the paid event.
- U02 selects cancellation settlement as a separate admin-controlled entitlement,
  never completed-service eligibility. Ordinary U01 hold is 48 elapsed hours
  after service completion under the recorded U01 policy. For cancellation, U06
  selects the base and recipients (70% salon / 30% platform of the retained pool
  after provider costs, with the cost order) and U07 selects the hold formulas.
  The flat amount Q25, dispute scope/release Q19, roles Q20 and legal terms Q23
  remain unresolved; no fabricated completed_at or implicit zero cancellation hold.
  If fees arrive after payout, append a deficit/receivable and reviewed recovery;
  never backdate a negative payout or assume a bank debit is permitted.

The consumed source entitlement is historical and cannot shrink retroactively
when a later refund/fee arrives. Freeze further spending and append the new
refund reserve or deficit/receivable instead; signed funding balance may be
negative, although payout amounts cannot. Before any external submission, block
or explicitly release underfunded held reservations under lock and append an
event. Once submitted/unknown, retain the reservation, stop additional execution
and reconcile the same operation; do not free possibly transferred funds.
Record a verified outcome and corresponding deficit even when funds are now
insufficient. Do not reject a historical transfer/correction to make net fit.
Any renewed attempt after verified failure retains its payout identity, uses a
new attempt sequence and reservation generation with renewed approval, retains
the released old reservation, and must prove the old external operation cannot
still move money. Unknown operations never qualify for this retry path.

## RLS/security impact

All nine tables are backend-only with RLS/client revocations and the shared
minimum-rights/provenance contracts. Only approved finance authority approves;
the executor can submit/reconcile the frozen instruction, never approve it.
Mock or wrong-environment sources cannot fund a real entitlement or confirm a
real outcome. Finance authority,
MFA, dual review, limits and manual evidence are Q13 gates implemented through
G01, not a new role enum/JWT claim. Owner reads are sanitized projections.
Provider observations use the existing signature/replay gate and preserve
effective versus received times. Plaintext destinations already in
`salon_payout_accounts` are a release blocker: no enablement until a separately
reviewed Q15 encryption/tokenization/backfill plan also addresses old copies.
P02/P06 must prove upstream automatic settlement cannot bypass the hold or cause
a second bank transfer; a local pending row cannot stop unsupported provider behavior.

## U03 cancellation and no-show payout boundary

U03 customer cancellation uses flat-fee band at 48 hours or more, 5% at 12 to
less than 48, 35% at 4 to less than 12, zero refund below 4 hours. Exactly
48/12/4 hours belongs respectively to flat/5%/35%. These rates describe customer
penalty, not beneficiary income or authority to transfer. U06 selects the
percentage base (captured amount before provider costs), the recipients (70% salon /
30% platform of the retained pool after actual provider costs) and the cost order;
U07 selects the holds. The exact flat amount Q25 and dispute scope/release Q19 are
unresolved. The historical U02 split creates no entitlement; only a committed
cancellation under its bound policy version does. While provider costs are unknown,
the retained pool is unresolved accounting, not available salon/platform money.

No-show requires appointment start passed, full ten-minute grace, explicit
authorized owner/staff confirmation, actual actor/time/reason and customer
notification; no timer silently cancels or marks no-show. Attendance confirmation
is not a cancellation refund rule, completed service or payout entitlement.
U03 does not select no-show money; U06 selects the under-4-hour treatment (refund zero, provider costs deducted, 70/30 split) and U07 the hold. Preserve
audit and notification intent in later design with durable delivery retries;
revalidate concurrent arrival/check-in/correction before confirmation. Confirmers
have no finance approval/execution powers merely from attendance authority.

Admin control/timing remains subject to Q20 scoped authority and the U07 hold; common
manual/automatic KYC, dispute, funding, reservation and finality checks remain.
U01's historical ordinary 48-hour completion clock cannot be reused as the
cancellation/no-show hold (U07) or a fabricated completed_at. Old policy
bindings/financial facts never change. See [U03 approval record](APPROVAL_REGISTER.md#policy-approval-record-u03)
and [current bands](../../verification/payment-subscription-booking-spec.md#41-u03-approved-cancellation-bands-and-no-show-process).

Admin target capabilities include pending cancellation payouts, salon-level
payout history, payout status and audit history; report scope includes daily,
weekly/monthly sales, online/cash, completed/cancelled/no-show and separate
subscription revenue. Metric/event-time/recognition and scoped export contracts
need review; direct cash/UPI is not provider-funded payout balance. No reporting
endpoint or data aggregation is implemented by this design.

Owner sees no platform percentage or internal allocation formula. Candidate
projection is eligible amount/status/date/admin message only; Q21 approves exact
fields, scheduled versus actual date and sanitized text. Keep internal allocation
out of responses, reports/exports, replay/cache, notifications and errors.
Amounts may still permit inference from independently known prices; do not claim
mathematical secrecy merely because internal fields are withheld. See
[admin/report contract](../../verification/payment-subscription-booking-spec.md#81-admin-capabilities-and-reporting-scope-u02)
and [current U03 decisions](APPROVAL_REGISTER.md#policy-approval-record-u03).

## Account-deletion behavior

Retain booking/salon monetary shells and event/source links; never cascade-delete
obligations. No FK to erasable `payment_provider_accounts` or payout-account
history: capture internal scope/version/generation, not dependent live mappings.
Actor/opener/verifier FKs null through reviewed erasure. Destination secrets and
dispute evidence require scrubbing/key destruction or explicitly restricted lawful
retention under Q15/Q16/L05; digest pseudonymization is not anonymization.

The current erasure worker deletes provider mappings and does not transfer open
payout/dispute reconciliation work. Before activation, extend its durable handoff
to restricted obligation processing without restoring account access or waiting
indefinitely for financial settlement. Test reference/secret cleanup, including
unknown transfers, staff-associated identities and retained refund obligations.

## Downgrade safety and rollback plan

Only an empty schema with no reservations, dispute, destination evidence, payout,
attempt or fee-allocation link is structurally reversible. Refuse downgrade after
any externally submitted/unknown attempt even if current projections say failed.
Stop new approvals/scheduling/transfers, preserve existing reservations and poll
outcomes, then forward-repair. An application rollback must keep compatible
reconciliation and encrypted destination/evidence reads. Never retry a new
transfer ID because the previous release cannot read the current schema.

## Unresolved approval and readiness

**Prepared for design review; not execution-ready.** Q04/Q05/Q13-Q16, P01-P06,
L01-L03/L05 and Q17-Q26: ordinary 48-hour completion hold is preserved as U01 evidence;
U06/U07 select the penalty base, recipients, cost order, no-show treatment and holds.
Still unresolved: flat amount Q25, dispute scope/release Q19, tax components,
reserve/true-up for unknown fees, authorities/limits, provider
product and fund custody, fee reserves,
manual evidence/independent reviewer, destination security and retention.

Later verification: concurrent manual/automatic reservation, dispute/initiation
race, partial reserves, unknown timeout, duplicate/manual-versus-settlement
transfer, reversals and later refunds, post-payout fee deficits, destination
change/KYC revocation, expiry access, erasure and downgrade refusal. No SQL or
provider request is executed here.
