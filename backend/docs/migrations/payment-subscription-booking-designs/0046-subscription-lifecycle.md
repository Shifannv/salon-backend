# G07: Subscription lifecycle

**Design only; Approval required for implementation.** Review group G07.
Schema dependencies: G01; existing subscription purchase authority and G02 where accounting postings are used. No Alembic revision ID or parent is assigned.
The filename is a historical locator, not execution order. Inherits the
[shared rules](README.md), [field treatments](ERASURE_CLASSIFICATION.md) and
[G09 concurrency contract](09-slot-hold-concurrency-support.md).

## Purpose and compatibility

C07/C08/C15 require one trial after approved activation, two calendar months,
expiry blocking new booking/payment initiation, preserved existing obligations and
separate subscription purchases. Reuse `salon_access`, `salon_subscriptions`,
`subscription_plans`, `subscription_billing_records`, `subscription_events`,
subscription audit/anomaly tables and the existing verified-purchase activation
function. Do not create a second subscription payment ledger or reseed plans.

Existing enum `pending/trialing/active/past_due/cancelled/expired/suspended` stays.
Proposed public `trial` and `grace_period` are policy-derived presentation states,
not enum renames. Pending/suspended keep their operational meaning. Reuse
`current_period_start/end`, `grace_period_end`, `cancelled_at` and `expires_at`;
do not introduce conflicting `paid_through` or grace timestamps.

## Tables and columns

| New table | Proposed columns in addition to shared ID/timestamps |
| --- | --- |
| `subscription_lifecycle_policies` | `policy_code text`, `version integer`, `trial_months integer`, `trial_cap_mode text` (unresolved/limited/unlimited), `trial_booking_cap integer?`, `activation_event_code text?`, `calendar_rule_code text?`, `paid_grace_days integer?`, `trial_grace_mode text?`, `grace_privileges_code text?`, `existing_receipt_mode text?`, `late_capture_rule_code text?`, `cancellation_access_rule_code text?`, `renewal_mode text?` (one_time_manual/explicit_consent_required), `approval_reference text?`, `is_active boolean` |
| `subscription_lifecycle_events` | `salon_id uuid` -> salons, `subscription_id uuid?` -> salon_subscriptions, `billing_record_id uuid?` -> subscription_billing_records, `policy_id uuid?` -> policies, `event_type text`, `event_key text`, `from_state text?`, `to_state text`, `effective_at timestamptz`, `observed_at timestamptz`, `actor_id uuid?`, `reason_code text`, `correlation_id uuid`, `consent_reference uuid?` (internal restricted evidence reference), `consent_terms_version text?`, `revokes_consent_event_id uuid?` -> same table; consent/revocation is evidence, never an implicit recurring mandate; `command_audit_event_id uuid` -> G01 sealed audit event for new-mode commands |

| Existing table | Additive columns |
| --- | --- |
| `salon_access` | `lifecycle_policy_id uuid?` -> policies, `trial_timezone text?`, `trial_activation_event_id uuid?` -> lifecycle_events |
| `salon_subscriptions` | `lifecycle_policy_id uuid?` -> policies, `renewal_mode text?`, `renewal_consent_event_id uuid?` -> lifecycle_events |
| `subscription_billing_records` | `lifecycle_policy_id uuid?` -> policies, `purchase_timezone text?`; existing amount/tax/benefits/interval snapshots remain authoritative |

Trial start/end already exist and are not reset or backfilled to current time.
Cycles between events and projections are introduced as nullable links after
creating the tables, with explicit RESTRICT FKs and ordered inserts in one command.

## Indexes and constraints

- Unique policy `(policy_code, version)`; trial months exactly 2 for the new
  policy, positive versions; no active policy unless all decisions it uses are
  resolved. Trial cap mode limited requires a positive cap; unlimited has NULL
  cap; unresolved has no executable entitlement. U01 selects unlimited for the new target trial; no legacy cap/data change
  or automatic executable policy insertion is authorized.
- Unique lifecycle event key and one `trial_started` event per salon. Index all
  FKs, events `(salon_id, effective_at, id)`, and subscriptions
  `(current_period_end, id)` for currently active/cancelled rows if existing
  indexes do not cover the authorized sweep. Do not duplicate 0030's open-order,
  unapplied-purchase or existing subscription uniqueness indexes.
- Every event's non-NULL subscription and billing references must belong to its
  `salon_id`; a referenced billing record must identify that subscription when
  both are present, with matching policy/currency and original purchase facts.
  Add parent composite unique keys and same-salon FKs where valid; use a locking
  relationship validator for nullable/event-type relationships. Simple UUID FK
  existence is not sufficient. Cyclic FKs are installed after all parents exist
  and validated before any new writer is enabled.
- `salon_access.trial_activation_event_id` must reference that salon's unique
  `trial_started` event, with matching policy and first activation facts. Renewal
  consent pointers must reference a same-salon consent-granted event for the
  applicable subscription/policy/terms version. A revocation references only a
  prior same-salon, same-subscription consent, cannot target itself/another
  revocation, and must have effective time no earlier than its grant. Unique
  revocation identity prevents duplicated effects; consent history is append-only.
- Grace days, when approved, nonnegative; existing grace end must be >= period
  end. Trial timezone validated from an approved source and snapshotted once.
  Immutable trial activation binding prevents reapproval/timezone changes from
  restarting/extending the trial. New activation uses salon lock + unique event.
- The trial calendar routine preserves approved local anniversary time,
  month-end clamp and exclusive end only after Q06 approves those details.
  Never convert the approved two calendar months to a 60-day interval.
- Verified purchase events bind provider order/payment, amount, currency and
  original plan snapshots through 0030's existing idempotent application path.
  Duplicate or late captures are recorded even after local order expiry; no
  second entitlement period is applied by a replay.
- Manual renewal versus consent-required modes cannot authorize automatic
  recurring orders. Any future automatic mode requires explicit current consent
  reference and separately implemented provider mandate semantics; no mandate
  storage/activation is part of this design. Consent events require both consent
  reference and terms version; revocations bind a same-salon consent event.
  No external mandate identifier or raw personal consent payload is stored here.
- The subscription's snapshotted renewal mode must equal its bound approved
  lifecycle policy mode. A different mode requires a newly approved policy/consent
  event, not an edit of purchase or old consent facts. `one_time_manual` cannot
  authorize recurring collection; `explicit_consent_required` without an active,
  matching, unrevoked consent fails closed. Consent never supplies provider
  mandate capability. Mock/sandbox purchases follow shared provenance isolation
  and cannot activate a live paid period.

## RLS/security impact

Both tables and added references remain backend-only with RLS/client revocations.
No role-enum or JWT claim change. Owner renewal checkout remains a separate
purchase from booking-payment initiation and vendor payout. Admin lifecycle
actions require approved authority, MFA and G01 audit coverage.
Trial, activation, purchase, expiry and deletion commands follow the shared
lock-order contract, including the exact subscription/salon namespaces. Role
ceilings in the minimum-rights contract apply; renewal entitlement is not a
permission to finalize accounting or approve a payout.

## Account-deletion behavior

Lifecycle events retain nonpersonal billing/period facts; actor FKs clear.
No FK to `subscription_provider_accounts`, which current erasure deletes.
Consent/provider evidence must be restricted/scrubbed per Q16; no raw consent
text, contact or token goes into immutable events. Preserve the current owner
active-subscription deletion blocker and cancellation/unused-period anomaly
handling until an explicitly approved policy changes it. Erasure must not
reactivate expired purchases or attach prior history to a re-registered profile.

## Existing-schema compatibility and rollout

0035 already uses two-calendar-month trial calculation and retains a 120-booking
cap. Keep legacy cap columns/values and history intact. Proposed policy-specific
ignoring that cap is selected by U01 for new policy; Q06 still blocks unapproved
calendar/activation/grandfathering implementation. Do not weaken existing NOT NULL
constraints or rewrite old cap history just because new policy is unlimited.

0035 `salon_booking_eligible`, trial routines/triggers, current subscription
application/sweep/promotion logic and API access-state reads must share the
approved mapping before new policy activation. Promotion eligibility is not
automatically booking entitlement. 0039's pinned-search-path hardening must
survive any replacement; 0040 client-access restrictions must remain.

Q07 must resolve collection-before-completion versus expired receipt permissions,
grace calendar/applicability and late capture handling. U01 selects seven-day
restricted renewal grace and existing completion; it is no deployment approval. NULL
policy means no new workflow activation. Existing appointments remain visible
and services/refunds/disputes/payout obligations accessible under their proper
authorization. A new migration cannot by itself make old use-case guards comply.
Do not globally reject payment webhooks, refunds or subscription renewal on expiry.

**Partially approved** Q06: two-calendar-month no-cap target selected; exact
activation/calendar and legacy transition remain open. **Partially approved**
Q07: seven-day grace blocks new booking/payment initiation, preserves existing
completion and subscription renewal; calendar/start/trial scope and receipt
permissions remain open. No trial clock is restarted or old invoice repriced.
Keep pending/suspended/expired reasons distinct and test existing appointment
visibility/completion, authorized receipts and renewal separately from new
booking/online-order eligibility. These corrections do not activate those choices.

## U02 salon-specific offers and admin revenue visibility

Default plans/prices remain unchanged. Custom offers are salon-specific and must
preserve original price, discounted price, currency, effective dates, admin actor
and reason. Old invoices/subscriptions retain original recorded price; no
retroactive price changes. Quote/order/purchase binds immutable selected terms,
not the plan/offer's current value at report or webhook time. Expired offer/late
capture cannot silently reprice old orders or lose verified money evidence.

Owner sees only final payable offer price; original/discount breakdown, internal
platform margin and restricted admin reason/evidence remain excluded from owner
API/report/export/cache/replay/message surfaces. Internal snapshots remain for
scoped admin/accounting review. Q20 defines offer roles/stages; Q22 duration,
timezone/expiration, overlap/revocation and quote/order locking remain open.
Q09/L02 still govern tax, benefits and recognition; Q24/L05 covers actor/reason,
price and consent evidence retention and safe erasure.

This is a required future persistence capability, not a finalized table/column
proposal or executable migration. Review offer version identity, salon/plan scope,
immutability, non-overlap/precedence, current authority and purchase snapshot
binding before assigning artifacts. No new table count or revision is asserted.
Reuse purchase authority and G01 audit; do not create another payment ledger.
Admin subscription revenue reports must distinguish sale, discount, tax/refund,
recognition time and cash receipt; metrics/timezone rules need explicit review.
See [offer contract](../../verification/payment-subscription-booking-spec.md#82-salon-specific-subscription-offers-u02)
and [U02 register](APPROVAL_REGISTER.md#policy-approval-record-u02).

## Downgrade safety and rollback plan

All new references NULL and no policy/event usage permits an empty additive
downgrade after dependency removal. Refuse once a trial/purchase/consent used a
new policy, even if its period has ended. For data-bearing rollback, stop new
policy activation/renewal initiation as needed while preserving prior paid/trial
dates, existing appointment permissions and capture/refund reconciliation;
forward-repair lifecycle projections. Never reset trial clocks, remove evidence
of purchased periods or grant a new trial as compensation for rollback.

## Unresolved approval and readiness

**Prepared for design review; not execution-ready.** Q06-Q09/Q13/Q16,
L01/L02/L05: activation versus approval, month-end/timezone details, selected no-cap legacy
transition, grace calendar/applicability and receipt permissions, late
captures, full/advance purchase treatment, cancellation/paid-through access,
taxes, one-time renewal mode and retention. Existing plan amounts are reused;
monthly equivalents are display calculations, never billing amounts.

Later verification: month-end/leap/DST calendar cases, reapproval, cap compatibility,
period-end/grace boundaries, existing-booking receipts/completion, separate renewal,
duplicate/late verified purchases, cancelled/suspended mapping, deletion and
forbidden downgrade. No SQL or provider tests run here.
