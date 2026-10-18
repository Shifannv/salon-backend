# G02: Provider-fee reconciliation

**Design only; Approval required for implementation.** Review group G02.
Schema dependencies: G01. No Alembic revision ID or parent is assigned.
The filename is a historical locator, not execution order. Inherits the
[shared rules](README.md), [field treatments](ERASURE_CLASSIFICATION.md) and
[G09 concurrency contract](09-slot-hold-concurrency-support.md).

## Purpose and compatibility

C01-C03/C12 require actual costs separated from estimates, no customer surcharge,
zero completed-service commission and append-only corrections. Reuse
`booking_payments`, `payment_refunds`, `payment_webhook_events` and durable
idempotency. This adds an accounting subledger referencing those authorities,
not another way to declare a capture/refund successful.

0029 already provides nullable `provider_fee_amount`/`provider_tax_amount`;
0033's immutable `gateway_fee_percent`/`gateway_fee_amount` are intent estimates.
0037's `online_processing_charge`, generated `service_amount`, immutable
`checkout_policy_version` and proportional recomputation must retain historical
meaning. Do not rename/copy estimates into actuals, overwrite legacy commissions,
remove the generated column or rewrite historical surcharge orders. Later
versioned checkout/trigger/worker changes are required for C01/C02; this design
alone does not remove the current 5% charge or enforce new zero commission.

## Tables and columns

`financial_events` identity/envelope is owned by G01. This group adds postings
and accounting seals to that existing proposed parent; it does not recreate it.
G01 audit seals are distinct from the balanced accounting seals below. No event
can authorize a financial effect or payout before G02 finalization is installed.


The provider-independent `ProviderFees` value object now keeps the six requested
application fields independently nullable. Proposed durable mappings are
`gateway_fee` -> gateway_fee component, `gateway_fee_tax` -> gateway_fee_tax,
`easy_split_fee` -> easy_split_fee, `settlement_fee` -> settlement_fee,
`payout_fee` -> payout_fee and `refund_fee` -> refund_fee. Decimal strings in
mock records are not a backfill or proof of provider actuals. Extra tax components
in this design remain separate when reported; no GST percentage is assumed.
`FakeProvider` observations must remain tagged mock and must never satisfy the
real reconciliation finalization predicate below. The current code stores these
observations in memory only; database persistence awaits reviewed migration
implementation and execution. No existing provider-fee scalar is repurposed.

| New table | Proposed columns in addition to shared ID/timestamps |
| --- | --- |
| `provider_charge_identities` | `provider text`, `provider_account_scope uuid`, `provider_environment text`, `economic_charge_digest bytea`, `kind text` (component taxonomy below), `currency text`, `current_component_id uuid?` -> components; identity immutable, current pointer a guarded projection |
| `provider_charge_observations` | `provider text`, `provider_account_scope uuid` (internal namespace, not a FK to erasable provider accounts), `provider_environment text`, `provenance text` (mock/provider_observed), `verification_method text?`, `verification_authority_reference text?`, `source_digest bytea`, `source_version text`, `source_kind text` (statement/invoice/webhook/query), `source_total numeric(18,2)?` (fee-only total), `currency text`, `effective_at timestamptz`, `observed_at timestamptz`, `evidence_ciphertext bytea?`, `key_version text?`, `retention_class text`, `supersedes_id uuid?` -> same table |
| `provider_charge_components` | `charge_id uuid` -> identities, `version integer`, `observation_id uuid` -> primary observation, `component_key text`, `kind text` (gateway_fee/gateway_fee_tax/easy_split_fee/easy_split_tax/settlement_fee/settlement_tax/payout_fee/payout_tax/refund_fee/refund_tax/other_tax), `amount numeric(18,2)?`, `classification text` (unknown/estimated/provisional/reconciled/disputed/not_applicable), `parent_component_id uuid?` -> components, `included_in_parent boolean`, `effective_at timestamptz`, `corrects_component_id uuid?` -> same charge's previous component |
| `provider_charge_evidence_links` | `observation_id uuid` -> observations, `source_line_key text`, `component_id uuid` -> components; append-only corroboration, not another recognized expense |
| `provider_charge_allocations` | `component_id uuid` -> components, `payment_id uuid?` -> booking_payments, `refund_id uuid?` -> payment_refunds, `allocation_key text`, `amount numeric(18,2)`, `basis_code text`, `basis_version text`, `bearer text` (unresolved/platform/salon), `event_id uuid?` -> financial_events; payout target is added in G04 |
| `provider_charge_reconciliations` | `observation_id uuid` -> observations, `reconciliation_key text`, `evidence_links_digest bytea`, `components_digest bytea`, `allocations_digest bytea`, `reconciled_total numeric(18,2)`, `finalized_at timestamptz`, `finalized_by uuid?`; immutable completeness marker, inserted only when the finalization predicate passes |
| `financial_postings` | `event_id uuid` -> financial_events, `line_no integer`, `account_code text` (approved controlled chart), `counterparty_key uuid?` (detached internal subject), `direction text` (debit/credit), `amount numeric(18,2)` (positive), `component_id uuid?` -> components |
| `financial_event_finalizations` | `event_id uuid` -> events, `posting_count integer`, `postings_digest bytea`, `debit_total numeric(18,2)`, `credit_total numeric(18,2)`, `finalized_at timestamptz`, `finalized_by uuid?`; immutable accounting seal |

Observations/components/allocations and events/postings are immutable financial
facts; classification changes append a new observation/component. Unknown fees
have NULL amount. Evidence-backed zero/not-applicable is distinct from missing
evidence. Correcting an actual appends reversal/new postings referencing the
original; do not sum superseded observations as additional charges.

Observations describe evidence, whereas `provider_charge_identities` names the
economic fee/tax being evidenced. The canonical identity is the tuple
`(provider, provider_account_scope, provider_environment, economic_charge_digest)`;
its digest derives from the provider's stable charge identity and component kind.
If no stable provider ID exists, the approved mapping must identify the economic
operation, fee kind and billing interval without depending on delivery channel,
receipt time or invoice file hash. **Approval required** (P01/P05/Q14) for that
mapping. Ambiguous evidence remains unmatched; never guess a new economic charge.
An invoice and webhook proving the same fee add evidence links to the same
component. They do not create another allocation or expense. A genuine revised
amount creates the next component version and linked compensating postings;
corroboration alone cannot increment its financial version.

Ciphertext holds only the minimal approved provider-reference/evidence subset,
never a raw request or bank/KYC payload. Key selection and custody are unresolved
Q15; nullable evidence means missing evidence, not permission to reconcile without it.

## Indexes and constraints

- Unique charge identity on the canonical tuple above; unique components
  `(charge_id, version)`; one initial component and at most one successor to
  each corrected component. Chains are acyclic, remain within the same charge,
  and advance sequentially under the charge lock. `current_component_id` must
  select the unique validated lineage head and cannot be switched arbitrarily.
  Retain old versions; recognize only the effective version plus explicit
  compensating postings, never sums of successive full amounts.
- Unique observations `(provider, provider_account_scope, provider_environment, source_digest,
  source_version)`; unique components `(observation_id, component_key)`; unique
  evidence links `(observation_id, source_line_key, component_id)`; a source line
  cannot map to competing versions of the same economic charge. Scope, origin,
  kind, currency and parent-inclusion relationships must agree throughout.
  Parent-component links must be acyclic/non-self, with matching observation
  scope and no inclusive child independently allocated. Unique
  allocations `(component_id, allocation_key)`; unique reconciliations
  `observation_id` and `reconciliation_key`; unique `financial_events.event_key`;
  unique postings `(event_id, line_no)`. Non-null stable keys prevent NULL replay gaps.
- Index every FK, observations `(provider, effective_at)`, components
  `(classification, effective_at)` for unresolved reconciliation, financial events
  `(salon_id, effective_at, id)` and `(booking_id, effective_at, id)`, postings
  `(counterparty_key, event_id)` and `(account_code, event_id)`.
- Currency INR; bounded finite amounts; paired ciphertext/key-version presence;
  source digest length for the chosen keyed digest; bounded codes/version strings.
  Reconciled amounts require evidence; unknown amounts must be NULL. Explicit
  not-applicable zero needs an evidence/classification reason.
- Allocations select exactly one payment/refund target (G04 extends this to
  payout); validate currency, provider/account scope, salon and booking linkage.
  A refund allocation must match its payment's identity. Inclusive components
  are explanatory children, not an additional expense/allocation target.
- Deferred constraint triggers verify balanced event debits/credits per currency,
  nonempty events and complete observation/charge-allocation conservation when
  finalized. Finalized means an immutable `provider_charge_reconciliations` row
  exists: its insertion locks the observation/components and proves source total
  known, every billable component reconciled with evidence, no unknown/provisional/
  disputed component, inclusive components excluded from double counting, and
  complete per-component allocations with approved bearers and linked balanced
  postings. Evidence-backed zero/not-applicable components need no fictitious
  money posting. Reconciled total equals the deduplicated statement component
  total and source total; digests bind the exact components/allocations.
  Prevent further child insertion against that observation; corrections require
  a superseding observation, compensating postings and their own marker.
  Partial allocation has no marker and cannot claim final net.
- The component set for observation finalization is the exact source-line mapping
  through `provider_charge_evidence_links`, not merely components whose primary
  `observation_id` equals this observation. Primary observations also have these
  links. A later invoice/query corroborates already recognized versions by reusing
  their existing allocations and sealed postings; it cannot recreate the expense.
  Bind source-line mapping, canonical version IDs and reused allocation IDs in
  the reconciliation digests, including `evidence_links_digest`. Lock observation,
  charge lineage, components and financial parents in the shared order before
  sealing. A historical corroboration never rewinds the charge's current head.
  Allocation conservation is component-version-wide, not a fresh allowance per
  observation. Each canonical version/allocation has one recognized accounting
  source identity; a different receipt/event key cannot recognize it again.
  Subsequent versions post bounded compensating deltas/reversals against that
  lineage, never a second unreversed full charge. Implement these relationships
  with unique source keys and locked aggregate validation, not event-key uniqueness
  alone.
- Finalization is by authorized accounting operations only. A transaction that
  inserts an event must seal it with exactly one `financial_event_finalizations`
  row before commit. Under the event lock, the seal validates positive posting
  count, exact financial-line digest, balanced currency totals, source identity and relevant
  approved accounting rules. INSERT of any posting locks its parent event and
  fails once a seal exists; UPDATE/DELETE of events, postings or seals is denied
  except the shared narrow identity scrub. Even an additional balanced pair is
  forbidden after sealing. No consumer counts unsealed events. Corrections create
  and seal a new event; reversal amounts are bounded against the original lines.
  Digests exclude erasable actor/payload fields; permitted identity detachment
  cannot change the financial commitment or require rewriting a seal.
- Provider-actual charge reconciliation requires `provider_observed` evidence
  attested by a trusted verifier, matching account/environment and finalized
  source postings. Mock/unknown evidence cannot pass that predicate; sandbox
  proof never verifies live charges. The shared provenance contract applies to
  every event and evidence join. Labels/ciphertext alone are not verification.
  New tables may be created with nullable cyclic current-component links, then
  attach their FKs after both parents exist; no omitted constraint is accepted.
- Lock source payment/refund rows when posting their verified event. Unique
  source-event keys and correction limits prevent double posting/over-reversal.
  Estimates/disputed/unknown costs cannot authorize an available net. Explicit
  receivable/reserve postings expose deficits; no negative payout or hidden clamp.

## RLS/security impact

All eight new tables are backend-only with RLS/client revocations and the minimum-rights
contract in README. Charge and event locks follow its shared lock-order contract. Reuse
signature-verified webhook intake; no direct client actual-fee write. Existing
scalar provider-cost columns may later be read projections only after an approved
mapping distinguishes gateway-only versus total charges. Never sum both scalars
and components. Backend finance reads require authorization; no customer/provider
evidence leaks through owner earnings. G01 audit coverage precedes activation.

## Account-deletion behavior

Financial parent links RESTRICT preserve amounts/events on inert booking/salon
shells. No FK to `payment_provider_accounts`, which erasure deletes. Actor FK is
nullable/cleared by `erase_profile_references`; no customer identity is copied.
Erasure must scrub or lawfully restrict ciphertext, reference digests, explanation
and idempotency payloads under Q16/L05. A keyed digest is not anonymous. Add these
tables/columns to erasure classification and prove that update guards permit
only the reviewed scrub. Current erasure does not implement this coverage.

## Downgrade safety and rollback plan

An eventual downgrade must refuse if any observation, allocation or financial
event exists, if dependent revisions remain, or if a new writer is enabled.
Only an empty, unused additive schema can be dropped in reverse FK order. No
fallback to legacy estimated fees as confirmed net is safe. After data exists,
stop new reconciliation/checkout initiation, preserve evidence and old receipt
reads, reconcile in-flight operations, and forward-correct postings. Backups
support recovery review, not replay of external money movement.

## Unresolved approval and readiness

**Prepared for design review; not execution-ready.** Q04/Q08/Q15/Q16, P01/P05,
L02/L03/L05: exact fee categories/evidence, inclusion/deduplication, allocation
basis, bearers, unknown-cost reserve/true-up, old surcharge orders, encryption,
retention and chart-of-accounts recognition. No fixed percentage/GST rate/net
amount is seeded. A provider statement-to-fee mapping needs separate evidence.

Later verification: duplicate and out-of-order observations, inclusive taxes,
multi-payment fee allocation and paise residuals, unknown versus zero, correction
conservation, overcollection/refunds, unchanged legacy projections, cross-salon
rejection, erasure and forbidden data-bearing downgrade. None run in this phase.
