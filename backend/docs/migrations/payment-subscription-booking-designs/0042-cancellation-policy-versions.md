# G03: Cancellation policy and refund obligations

**Design only; Approval required for implementation.** Review group G03.
Schema dependencies: G01, G02. No Alembic revision ID or parent is assigned.
The filename is a historical locator, not execution order. Inherits the
[shared rules](README.md), [field treatments](ERASURE_CLASSIFICATION.md) and
[G09 concurrency contract](09-slot-hold-concurrency-support.md).

## Purpose and compatibility

U03 selects prospective customer cancellation bands: at least 48 hours flat-fee
band (amount open), 12 to less than 48 hours 5%, 4 to less than 12 hours 35%,
below 4 hours zero refund. Exactly 48/12/4 hours goes respectively to flat/5%/35%.
Every penalty recipient remains open Q26; no new U03 70/30 allocation is selected.
Provider costs Q17 and dispute hold Q19 are explicitly unresolved; Q25 supplies
flat amount and percentage-base/refund mechanics only after approval.

U03 no-show requires appointment start passed and a full ten-minute grace,
explicit authorized owner/staff confirmation, actual actor/timestamp/reason and
customer notification. Never silently cancel or infer no-show from time alone.
No no-show financial penalty/payout is selected. Prior U01/U02 and legacy rules
remain historical evidence for their bound policy; never rewrite old snapshots.
Reuse current cancellation action requests, attendance audit, notification intent
and payment_refunds authority, without implementing code or executable artifacts.

## U03 monetary and attendance design gates

| Remaining elapsed time | Approved customer-cancellation band | Outstanding financial design |
| --- | --- | --- |
| At least 48 hours | Flat cancellation-fee band | Exact flat amount/caps Q25, recipient Q26, provider fees Q17 and hold Q19. |
| 12 to less than 48 hours | 5% penalty | Base/rounding/caps/refund Q25; recipient, fees and hold remain open. |
| 4 to less than 12 hours | 35% penalty | Exactly four hours included; base/refund Q25/Q18, recipient, fees and hold open. |
| Below 4 hours, before start | Zero refund | Full eligible captured retained funds do not establish any beneficiary or spendable payout; Q26/Q17/Q19 unresolved. |

The proposed single-cutoff/U02 columns below do not fully represent the U03
bands. Later review must bind immutable band boundaries, rate/flat amount/base,
recipient/cost/hold policy and source authority; no table/column/revision is
assigned or SQL authored by this update. Do not hard-code U02 3000/7000 or
use current catalog/fee projections as missing snapshot values. Unknown flat
amount is not zero; unknown costs/beneficiaries cannot finalize a monetary quote.
Retain refund caps, cumulative reservations and prior obligations below. Never
spend refundable/uncertain funds twice or reassign old fulfilled refunds.

No-show confirmation later must revalidate bound start/grace, authorization,
attendance/current booking state and concurrent arrival/check-in/completion.
Record confirming actor, server timestamp and reason with attendance event and
customer notification intent; dispatch/retry delivery without repeating the
state change. No unconditional timer/scheduler cancellation and no claim of
customer notification without delivery state. Reason content needs minimized,
sanitized storage under Q24/L05. Scoped confirmer/correction/appeal and delivery
failure rules remain Q02 review. No no-show financial allocation, zero refund,
service completion or staff commission is inferred from attendance confirmation.

## U04 immediate slot release and cancellation command

**Approved:** valid cancellation commit sets status cancelled and immediately
removes this booking's occupancy from database availability. Next eligible
customer may book. Redis slot/cache invalidation follows commit; refund delivery
is a separate asynchronous workflow. Refund delay/failure never reoccupies a
cancelled slot. PostgreSQL canonical availability, booking revalidation and
unique/exclusion constraints remain authority, independent of Redis/cache.

The proposed state matrix and full transaction/replay/audit/notification contract
are in [specification section 4.4](../../verification/payment-subscription-booking-spec.md#44-u04-immediate-slot-release-after-committed-cancellation).
Pending/confirmed may cancel only with current ownership/role/policy/consent;
U05 forbids customer cancellation after checked_in. Only current salon owner/
scoped admin may cancel checked-in work with mandatory reason and atomic audit;
no staff grant is inferred. Concrete scopes and monetary treatment remain Q20/Q29.
Completed/no_show/rejected cannot become cancelled via this command. Already
cancelled is authorized replay/no-op, not another transition or financial allowance.
A cancellation request/preview alone leaves occupancy intact; U03 no-show remains
its separately confirmed workflow, never a timer cancellation.

Discover all profile/customer/salon/subscription/funding identities before locks;
follow G09/shared advisory gates, then booking/payment/cancellation/financial and
later audit rows by published rank. Revalidate actor/state/schedule/policy and
idempotency under locks. Atomically record cancelled status, cancellation fact,
applicable known refund obligation/reservation or permitted planning intent,
one logical slot-release audit marker, durable scoped invalidation and notification
intents. Required financial policy/consent still determines whether cancellation
is valid before commit; never guess an unknown fee/recipient/amount. Finalizing
money is separate from acknowledging an already committed cancellation. No
provider/Redis/message call occurs inside row locks or before committed release.

Rollback leaves old occupancy and no emitted release. Unknown commit result
reconciles original key. Same key/payload returns original cancellation; changed
payload conflicts. New key after cancelled returns original reference/no-op,
with no extra refund/reserve, release marker or customer message. Authorization
precedes replay; outstanding original side effects may be re-dispatched. Cancellation
response does not promise still-free availability if a new customer booked later.

Proposed audit marker booking.slot_released binds one cancellation revision to
old interval/resources, old/new state, actor, recorded transaction time,
policy/reason and correlation/idempotency. It means only old booking occupancy
removed, not refund success or unconditional free-slot status. Storage/enum is
unimplemented and Q28-reviewed. Financial facts and privacy classification remain.
Customer/authorized salon notification intent commits with cancellation and
sends afterward; sanitized message separates cancelled from refund-pending/paid.
Delivery failures retry original logical notification, never rollback or repeat
cancellation, change money, or reoccupy slot. No old customer data is broadcast
to another customer seeking availability.

G09's [post-commit recovery](09-slot-hold-concurrency-support.md#u04-committed-cancellation-and-cache-recovery)
requires fresh canonical availability regardless of stale negative caches,
durable invalidation retries, refills guarded against old generations, and
compare-bound cleanup of the old hold without deleting any newer actor's hold.
Closure/staff/access rules still apply; cancellation cannot open a closed interval.
Q27/Q28/Q29/Q30 and RP07/RC06 retain unresolved scope/storage/numeric/monetary
review; U05 selects checked-in actor restrictions, reason/audit, durable outbox
and PostgreSQL outage fallback. No executable authorization is implied.

## U05 checked-in money treatment and duplicate action review

Customer cancellation after check-in is forbidden, including new-key or
owner-style request attempts. Owner must control the salon; admin needs current
scoped authority. Both require cause/reason, actor, trusted time, prior/new state,
schedule/policy and permission basis in the cancellation audit transaction.
No raw personal/provider text enters immutable financial facts. Completed,
no_show and rejected remain forbidden ordinary cancellation states; independently
confirmed no-show is not an alternative customer cancellation permission.

Treat checked-in operator cancellation as its own cause, never automatically
U03 pre-start customer penalty or historical U02 70/30. Partial-service remedy,
customer refund, fees, recipient, dispute hold and recovery remain Q29 with
Q17/Q19/Q25/Q26/L01-L03. This review defines safe treatment while those values
are unset, not a refund percentage:

- Without verified capture, create no fictitious provider refund/payable.
- With an approved remedy and verified capture, bind one root/source refund
  obligation, reserve still-owed funds under capture/cumulative caps and dispatch
  asynchronously after commit. Preserve previous fulfilled/uncertain reservations.
- Where monetary remedy is unresolved, commit permitted operational cancellation
  with one durable financial-review obligation and restrict affected retained
  funds from new payout. Do not finalize a guessed refund/allocation or report
  refund paid. Required legal/consent preconditions still gate validity before
  commit, not Redis/refund delivery. Existing slot release remains immediate.
- Direct cash/UPI remedy is with the accountable direct recipient; it is not
  platform provider funding. Already confirmed/unknown payout remains evidence
  and reservation; recovery/deficit requires separate authority, no assumed debit.

All cancellation causes/keys serialize on booking/current revision and canonical
cancellation source, not only caller idempotency key. Two distinct owner/admin
keys yield one transition/root, one release marker, one logical financial-review/
refund obligation and one notification intent; loser replays/no-ops or conflicts
on stale revision. Source guards prevent a worker/callback from planning the
same refund again. Late correction appends evidence with authorized delta; it
cannot issue another cancellation allowance. Unknown commit reconciles original
operation before submission, and delivery retries retain external identity.

Cancellation and payment-confirmation application acquire shared gates then
booking before payment/source rows in published order. A signed receipt may
be durably ingested before business processing, but no payment-first business
lock waits on earlier salon/booking gates. Capture winning first is included
in cancellation planning; cancellation winning first keeps state cancelled
when capture arrives. Record that capture once on its original booking and
route to refund/remedy review; never revive the slot or assign it to replacement
booking. Cash receipts/capture evidence and booking final state are distinct.

U05 chooses durable database outbox invalidation in the cancellation commit,
independent of Redis availability. Required outbox persistence failure rolls
back the database transaction; Redis connectivity cannot be a precommit gate.
Outage uses fresh PostgreSQL and SQL-only booking fallback. Retry/dead-letter/
operator repair must not rerun cancellation or mutate money; see
[U05 recovery](09-slot-hold-concurrency-support.md#u05-durable-outbox-retry-dead-letter-and-repair)
and [reviewed race contract](../../verification/payment-subscription-booking-spec.md#45-u05-resolved-cancellation-and-slot-release-risk-review).
Q30 operational numbers and scoped repair authority remain open. No executable
artifact, role grant, provider/database call or runtime safety proof is created.

## Final technical approval defaults - recommendations only

TP01 recommendations are recorded in
[specification section 13.5](../../verification/payment-subscription-booking-spec.md#135-final-technical-approval-defaults---recommendations-only)
and the [technical approval register](APPROVAL_REGISTER.md#final-technical-approval-defaults---recommendations-only).
Every TA01-TA10 item is **Approval required**, not a new selected rule.

TA01 recommends manual finance/legal remedy review with affected captured funds
restricted, no guessed refund/partial-service or beneficiary amount, and only
approved capture-capped asynchronous delivery. TA02 recommends customer after-
check-in cancellation forbidden, owner request requiring scoped admin approval,
and admin reason/audit. The additional owner-to-admin gate is unapproved; if
later selected, the request alone leaves status checked_in and slot occupied
until valid approved cancellation commits. Earlier U05 scope evidence is not
approval of this extra gate. No staff/finance right is inferred from a role label.

TA03-TA07 propose five retries after the initial dispatch with delays 1m, 5m,
30m, 2h, 12h, five-minute fenced lease, durable dead-letter, Sentry plus admin
email and scoped finance/admin repair with two-person approval. These do not
execute cancellation/refund again or weaken immediate committed release.
TA08 proposes 90 days from resolved delivery only, with lawful reviewed open-job
exceptions; TA09 supplies no numerical financial-audit period. TA10 proposes
separate managed KMS/secret storage and encrypted/tokenized payout data; products,
access, rotation and cleanup remain pending. No new financial-row hard delete,
key/credential operation, outbox cleanup or runtime configuration is authorized.

## Tables and columns

| New table | Proposed columns in addition to shared ID/timestamps |
| --- | --- |
| `cancellation_policy_versions` | `policy_code text`, `version integer`, `cutoff_seconds integer`, `boundary_mode text?`, `allocation_model text?` (legacy A/B; U02 cost-aware discriminator requires review), `refund_formula_code text?`, `refund_formula_version text?`, `split_base_code text?`, `platform_basis_points integer`, `salon_basis_points integer`, `fee_bearer_policy_version text?`, `owner_decision_required boolean?`, `no_show_policy_version text?`, `approval_reference text?` (nonpersonal internal reference), `is_active boolean` |
| `cancellation_policy_activations` | `policy_id uuid` -> versions, `scope_code text` (initial proposal: platform policy only), `effective_from timestamptz`, `effective_to timestamptz?`, `approved_by uuid?`, `approved_at timestamptz?`, `is_active boolean`; mutable scheduling metadata, policy content stays immutable |
| `booking_cancellation_terms` | `booking_id uuid` -> bookings, `terms_version integer`, `policy_id uuid` -> versions, `appointment_start timestamptz`, `salon_timezone text`, `service_amount numeric(18,2)`, `bound_at timestamptz`, `supersedes_terms_id uuid?` -> same table, `binding_cause text` (creation/reschedule/approved_legacy_adoption) |
| `booking_cancellation_outcomes` | `booking_id uuid` -> bookings, `terms_id uuid` -> terms, `root_outcome_id uuid` -> same table (root points to itself), `action_request_id uuid?` -> booking_action_requests, `initiator text`, `cause_code text`, `request_received_at timestamptz`, `decided_at timestamptz`, `collected_amount numeric(18,2)`, `customer_refund_due numeric(18,2)`, `split_base_amount numeric(18,2)`, `platform_allocation numeric(18,2)`, `salon_gross_allocation numeric(18,2)`, `rounding_rule_code text`, `quote_digest bytea`, `event_id uuid` -> sealed financial_events, `actor_id uuid?`, `idempotency_digest bytea`, `supersedes_outcome_id uuid?` -> same table |
| `cancellation_refund_obligations` | `root_outcome_id uuid` -> root outcome, `origin_outcome_id uuid` -> authorizing outcome version, `payment_id uuid` -> booking_payments, `obligation_key text`, `amount numeric(18,2)`, `currency text`, `event_id uuid` -> sealed refund-reserve financial event; immutable logical portion of the outcome's refund, not another payment/refund-success ledger |

Extend `payment_refunds` with nullable `cancellation_outcome_id uuid` and
`cancellation_refund_obligation_id uuid` FKs (RESTRICT), plus nullable
`cancellation_delivery_generation integer`. All three are present together for
new-mode cancellation deliveries; indexes cover both FKs. One outcome can be
funded by several payment-specific obligations. Existing refund rows remain the
authority for delivery status; their failure never cancels the logical obligation.
Corrections release/reallocate a logical obligation only through sealed linked
postings and an authorized append-only outcome correction, never by deleting it.

## Indexes and constraints

- Unique policy `(policy_code, version)` and positive version. U03 needs a
  reviewed immutable multi-band representation with exact 48/12/4-hour boundaries;
  flat fee, percentage base, beneficiaries, fees and holds remain unresolved.
  Prior U02 3,000/7,000 allocation is historical only, not a U03 constraint/default.
  Existing bound policies keep their parameters. No policy row is inserted and
  no incomplete configuration may activate or silently substitute a default.
- Exclude overlapping active activation ranges per `scope_code`, `[from,to)`;
  require end greater than start. An approved rollover can close activation
  metadata without altering policy facts or existing booking bindings. Log it.
- Unique terms `(booking_id, terms_version)` and outcome idempotency digest;
  unique outcome `event_id`; one initial finalization per booking and one direct
  correction per superseded outcome. Validate acyclic correction chains under
  booking lock. Index all FKs, activation `(scope_code, effective_from)`, outcome
  `(booking_id, request_received_at)` and terms `(booking_id, bound_at)`.
- Terms must reference the same booking throughout the supersession chain;
  confirm current booking/version under lock. Validate salon timezone by the
  reviewed timezone source, not an arbitrary text CHECK.
- Finite nonnegative amounts; the explicit cumulative arithmetic below binds
  each outcome's refund and allocation to its policy and eligible capture basis.
  Do not subtract previously processed refunds from P and then subtract them
  again as R. Excess captures and historically inapplicable surcharge money have
  separately classified obligations, not an unapproved new-policy split base.
- Finalization rejects incomplete policy, stale quote, changed funds, request or
  schedule. Record trusted request receipt, not later salon approval time.
  U03 exact bands/rates are selected; monetary base/refund mechanics and
  ingress/reschedule/legacy details remain Q03/Q18/Q25. Historic A/B/U02 checks
  cannot be imposed on new U03 outcomes without an approved per-band policy.
  Charge allocation is separate through G02; no duplicate deduction from refund.
- The transaction locks booking, relevant payments/refunds and funds in a stable
  order; commits booking cancellation, outcome, refund reserve, audit and
  notification and durable cache-invalidation intents together. U04 also records
  one logical slot-release audit marker. After commit cancelled occupancy is
  nonblocking immediately; provider refund execution/invalidation dispatch happen
  independently afterward. Required policy guards precede a valid commit; no
  refund completion/worker/cache-TTL delay retains the old reservation.
  Corrections append delta/reversal postings; they cannot promise a second refund
  for an already fulfilled obligation.

## Historical U02 split and shared refund-cap invariants

Use immutable cumulative snapshots, not a fresh independent refund allowance
for each payment or corrected outcome. `P = collected_amount` is the policy's
verified eligible capture pool; `R = customer_refund_due` is its total refund
entitlement, including any prior fulfillment once classified against this root.
`S = split_base_amount`, `U = platform_allocation`, `V = salon_gross_allocation`.

- Historical U02 late outcome (not a U03 recipient selection): R=0; full eligible P enters settlement handling.
  Provider costs C are deduplicated approved actuals linked to G02, never estimates
  silently treated as actual or deducted twice. Q17 must select cost/base branch.
- Requested net-pool branch, **Approval required** Q17: S=P-C;
  U=half-up-paise(S*3000/10000); V=S-U; P=R+C+U+V.
- Platform-absorbed branch, **Approval required** Q17: S=P;
  U=half-up-paise(P*3000/10000); V=P-U; platform net=U-C;
  P=R+V+C+platform net. Any platform fee deficit needs approved funding.
- All calculations use integer paise or Decimal, never binary floats. The
  platform-first rounded residual convention above is a proposal for explicit
  Q17 review; exact rounding version must be bound before finalization.
- Unknown C or unsupported/underfunded pool blocks finalization; no invented zero,
  negative payout or hidden clamp. Later cost true-up appends adjustment evidence,
  never reprices original financial facts. Final transfers remain Q19/Q20 gated.
- Existing A/B and 20/80 policies retain their exact historic formulas and
  outcomes. Never alter a bound policy, refund allowance or prior fulfillment to
  match U02; prospective version/effective date/open-operation adoption is unresolved.
- Proposed columns above are not yet a complete executable specification for
  U02: exact cost-approval/version snapshot, G02 source binding and branch/net
  facts require further reviewed persistence/constraint design after Q17. Do not
  infer missing fields from mutable current fee projections or authorize schema
  preparation here. Financial lineage must bind the precise approved cost set.
- U03 equality at four hours belongs to the 35% penalty band; actual refund
  requires approved base/fees, never U02 arbitrary full/zero refund. U03 no-show
  operational confirmation is selected but its finances remain separate. Salon-caused cancellation and duplicate/excess capture
  remain distinct; U02 zero refund cannot cancel an already fulfilled/uncertain
  refund obligation. Any incompatible legacy fulfillment blocks automatic adoption.

For the unique current outcome in a root lineage, define F as confirmed refund
delivery and H as still-reserved delivery amounts across **all** linked payments.
New or enlarged delivery reservations require F + H <= R, and each payment's
own capture/refund cap must also pass. Unique obligations `(root_outcome_id,
obligation_key)` and unique deliveries `(cancellation_refund_obligation_id,
cancellation_delivery_generation)` bind retries to one logical obligation. Sum
of logical outstanding portions plus F must also stay <= R; a failed call frees
no outcome allowance for a second logical refund. Do not count the logical
reserve and its execution reservation as two separate deductions from funds.
Every refund initiator for a newly governed cancellation, including owner/admin,
closure and erasure workers, must use this binding/cap path. An unlabelled legacy
refund path cannot bypass the outcome cap. Unrelated/excess refund categories
remain separately classified and conserve their own original capture funding.

An obligation's fulfilled amount plus its open delivery reservations cannot
exceed its amount. At most one open/unknown delivery generation per obligation;
existing `created` represents unresolved delivery where necessary. A new retry
generation requires confirmed nonmovement of the old attempt. Unknown/timeout
remains reserved, irrespective of an unreliable failure label. Releasing an
execution reservation does not release the unresolved customer entitlement.
Incoming verified unexpected movement is recorded once with an anomaly/deficit;
planning caps must never reject evidence of money already moved.

Under the shared lock order, lock the root/current outcome, all relevant payments,
obligations and deliveries before evaluating these aggregates. Require outcome,
terms, action request, obligation, payment and refund to agree on booking, salon
and currency; each origin/current outcome must share the same root. Add explicit
same-parent composite keys/FKs or locking validators, not existence-only FKs.
There is one initial root per booking and one acyclic successor per outcome.
An approval cannot lower R below fulfilled/uncertain commitments without an
explicit approved recovery/adjustment plan; previous fulfilled facts stay intact.

Extend the refund immutability guard to freeze the outcome, logical obligation,
delivery generation and payment binding once assigned, including after failure
or processing. Never move a processed refund to a different outcome. Associating
an unbound legacy refund requires **Approval required** historical reconciliation,
an audited one-time binding and validated prior fulfillment; no automatic backfill.

## RLS/security impact

All five new tables and the added refund relationships remain backend-only with
RLS/client revocations. Customers may receive authorized sanitized quote/outcome
responses only through future use cases. Neither customer nor owner may submit
trusted money, rates, policy IDs or receipt timestamps unchecked. No new finance
permission is inferred. G01 auditing is mandatory before new finalization.
The shared minimum-rights, provenance and lock-order contracts apply; only the
approved refund workflow reserves/delivers funds, and finance corrections need
their named authority. Mock delivery never fulfills a real refund obligation.
No create_booking/get_available_slots body is changed in this documentation;
later booking binding must be written inside the canonical creation transaction.

## Admin and owner projection boundary under U03

Admin reviews pending cancellation payouts, salon payout history and restricted
allocation/audit data under Q20 scoped authority. Admin approval/timing cannot
bypass reserves, KYC, active disputes or final transfer confirmation. Cancellation
hold/origin is unset; ordinary service completion plus 48 hours cannot substitute.
Owner projection may expose eligible amount, payout status, payout date and a
sanitized admin message only after Q21 field review. It must exclude platform
percentage/internal formula in APIs, reports, exports, cache/replay and messages.
Customer legal terms/consent for zero refund remain Q23/L01; Q24/L05 covers
financial evidence/actor/payload retention and erasure. See
[current specification](../../verification/payment-subscription-booking-spec.md#4-cancellation-allocation-and-refunds-decision-gate)
and [U03 register](APPROVAL_REGISTER.md#policy-approval-record-u03).

## Account-deletion behavior

Keep numeric policy/booking/outcome facts on retained booking shells. Nullable
approval/actor FKs clear before profile deletion. The optional
`action_request_id` must not cause deletion of outcomes if old requests are
removed: use **ON DELETE SET NULL** for this operational link, preserving the
financial event and request-received time. No names or free-form cancellation
text enter immutable outcomes. Existing `cancellation_reason*` scrubbing remains.
Quote/idempotency digests and any provider evidence require Q16 classification;
new tables and refund link enter erasure inventories/tests.

## Downgrade safety and rollback plan

Empty-schema downgrade only, after later dependencies are removed and writers
disabled; refuse if any booking is bound, outcome/refund link exists, or new
policy has governed a quote/obligation. Never restore a historical policy by
rewriting a binding. Data-bearing rollback disables new activation/finalization,
keeps old and new historical policy evaluators/refund reconciliation available,
and repairs forward. A failed refund remains reserved through rollback.

## Unresolved approval and readiness

**Prepared for design review; not execution-ready.** Q01-Q05/Q08/Q11/Q13/Q16,
L01-L03/L05 and P01/P05, plus Q17-Q28: U03 bands/rates and confirmed no-show
process are selected; flat amount/base/refund mechanics, every penalty recipient,
provider fees, dispute hold, trusted ingress, admin scope, no-show finances,
correction/notification handling, legacy/open-order transition and retention
remain unresolved. U04 immediate release is selected; Q27/Q28 state/actor and
cache/audit/notification mechanics require review. Cancellation settlement is a distinct U02 admin-controlled path; its
hold/origin and roles remain Q19/Q20. Never fabricate completed service.

Later verification: before/equal/after cutoff, delayed decisions, U03 exact boundaries and no-show grace/confirmation, legacy A/B and U02 cost-branch
conservation, multiple captures/refunds, duplicate cancellation/correction,
failed-refund reservation, policy rollover, erasure and old pending-request
compatibility. These are plans, not executed checks.
