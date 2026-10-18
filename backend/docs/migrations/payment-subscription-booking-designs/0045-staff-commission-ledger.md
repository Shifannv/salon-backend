# G06: Staff commission ledger

**Design only; Approval required for implementation.** Review group G06.
Schema dependencies: G01, G02; existing refund authority and approved G03 bindings where applicable. No Alembic revision ID or parent is assigned.
The filename is a historical locator, not execution order. Inherits the
[shared rules](README.md), [field treatments](ERASURE_CLASSIFICATION.md) and
[G09 concurrency contract](09-slot-hold-concurrency-support.md).

## Purpose and compatibility

C09 creates an internal salon allocation ledger, distinct from platform
commission (C02) and platform payout. Reuse immutable `booking_services` prices
and durations and `staff` identities. `booking_services` has composite PK
`(booking_id, service_id)`, not a standalone line-item UUID. Existing bookings
currently identify one assigned staff member; no multi-staff booking engine or
automatic historical commission backfill is implied by supporting allocation rows.

## Tables and columns

| New table | Proposed columns in addition to shared ID/timestamps |
| --- | --- |
| `staff_commission_rule_versions` | `salon_id uuid` -> salons, `staff_id uuid?` -> staff (NULL means salon default), `service_id uuid?` -> services (NULL means service default scope), `version integer`, `effective_from timestamptz`, `effective_to timestamptz?`, `rule_type text` (percentage/fixed), `rate_percent numeric(7,4)?`, `fixed_amount numeric(18,2)?`, `basis_code text?`, `selection_event text?`, `earning_event text?`, `refund_rule_code text?`, `policy_version text?`, `approved_by uuid?`, `is_active boolean` |
| `booking_staff_commission_snapshots` | `booking_id uuid`, `service_id uuid` -> composite booking_services parent, `snapshot_version integer`, `rule_id uuid` -> rules, `booked_service_amount numeric(18,2)`, `basis_amount numeric(18,2)`, `pool_amount numeric(18,2)`, `currency text`, `selected_at timestamptz`, `effective_from_snapshot timestamptz`, `effective_to_snapshot timestamptz?`, `rule_type text`, `rate_percent numeric(7,4)?`, `fixed_amount numeric(18,2)?`, `basis_code text`, `earning_event text`, `refund_rule_code text`, `policy_version text`, `supersedes_id uuid?` -> snapshots |
| `booking_staff_commission_allocations` | `snapshot_id uuid` -> snapshots, `staff_id uuid` -> staff, `weight_basis_points integer`, `allocated_amount numeric(18,2)`, `assignment_version integer`, `assigned_at timestamptz` |
| `staff_commission_obligations` | `booking_id uuid`, `service_id uuid` -> composite booking_services parent, `staff_id uuid` -> staff, `earning_kind text` (service_commission), `completion_event_id uuid?` -> booking_audit_events; canonical identity across snapshot/allocation revisions, no second payment ledger |
| `staff_commission_entries` | `salon_id uuid` -> salons, `obligation_id uuid` -> obligations, `allocation_id uuid` -> allocations, `staff_id uuid` -> staff, `entry_type text` (earned/reversal/adjustment), `direction text` (credit/debit), `amount numeric(18,2)`, `currency text`, `effective_at timestamptz`, `event_key text`, `refund_id uuid?` -> payment_refunds, `reverses_entry_id uuid?` -> same table, `financial_event_id uuid?` -> sealed financial_events, `actor_id uuid?`, `reason_code text` |

Rules are effective configurations; closing/retiring a rule does not mutate its
financial parameters or snapshots. Snapshot revisions append rather than editing
historical staff assignment/rate/price. Financial entries append corrections.
There is no staff bank transfer, payroll or staff payout integration in this design.

## Indexes and constraints

- Unique rule `(salon_id, normalized_staff_scope, normalized_service_scope,
  version)` and GiST temporal exclusion on active rules for that same normalized
  scope. Normalize nullable scopes with a reserved non-user sentinel expression
  so NULL does not permit overlapping defaults. Exact normalization must be
  reviewed against UUID constraints; do not assume NULLS NOT DISTINCT syntax
  availability without target-version evidence.
- Unique snapshot `(booking_id, service_id, snapshot_version)`, allocation
  `(snapshot_id, staff_id)`, obligation `(booking_id, service_id, staff_id,
  earning_kind)`, entry event key and one initial earned entry per obligation.
  Supersession stays within one booking/service, has one root and at most one
  successor per snapshot, is acyclic and advances sequentially under the booking/
  service lock. A new snapshot never creates a new service earning identity.
  Index every FK, rules `(salon_id, effective_from)`, entries
  `(salon_id, staff_id, effective_at, id)` for daily/monthly timezone reports and
  `(refund_id, allocation_id)` for reversal reconciliation.
- Require positive versions, valid intervals, exactly one percentage/fixed
  amount, percentage in 0-100, finite nonnegative snapshot amounts and positive
  entry magnitudes. Composite booking/service FK RESTRICT preserves line facts.
  Validate staff, rule, service and booking all belong to the same salon.
- Different scopes can match the same service: Q10 must approve deterministic
  precedence. No rule selection until basis, selection time, earning event,
  multiple-staff weights and refund treatment are approved. No implicit 40% rule.
- Under a snapshot/booking lock, deferred constraints require positive allocation
  weights summing 10,000 and rounded allocation amounts summing exactly the pool.
  Use deterministic residual assignment under the approved rule. A changed service
  price or current staff rule cannot recompute an old snapshot.
- Earned entries require the approved completed-service event. D10's booking-time
  selection, gross basis, no-show treatment and proportional refund reversal
  remain **Approval required** Q10. The user's design-correction requirement
  forbids earned service commission for cancelled service; a cancellation cannot
  fabricate a completion event. Existing accidental earnings need an authorized
  append-only correction, never deletion or a second earned entry. Separate time compensation
  requires authority and its own category, not fabricated completion.
- Refund reversal locks original entries, authorized formula adjustments and
  refund, and bounds cumulative reversals to the unreversed recognized service
  entitlement described below. Multiple partial refunds use cumulative proportional
  rounding minus prior reversals, avoiding paise drift. Already-disbursed internal
  staff recovery needs separate authority; no silent negative bank payment.

## Canonical earning and formula enforcement

The selected rule's effective interval must contain the approved selection
instant, and the immutable snapshot must match that rule version's financial
parameters. **Approval required** Q10 for selection time, basis, precedence,
fixed-amount scope, multiple-staff distribution and recognition policy; no rule
executes until these are explicit. For an approved percentage rule,
`pool_amount = half_up_paise(basis_amount * rate_percent / 100)`; for an approved
fixed rule, pool equals its declared per-service-line fixed amount. Exactly one
formula applies. `basis_amount` must derive from the approved immutable booked
service price basis, never the current catalog price. Excess-over-basis fixed
compensation requires a separately approved funding/category policy, not a
silent negative salon share.

Allocations conserve the computed pool, not an arbitrary supplied pool. Staff,
obligation, allocation, snapshot, service, booking, completion audit and any
refund/reversal must share the same booking/service/salon identity and currency.
An initial earned entry equals its allocation and binds the unique completion
event. A completion replay or replacement snapshot cannot append a second earned
entry. Changing an already earned allocation posts linked reversal/delta entries
against the original obligation; replacing staff also adjusts the old obligation
before recognizing the newly authorized one. Under the booking/service lock,
define G as initial recognized service earnings plus signed authorized formula/
reassignment adjustments across the canonical obligations. For completed eligible
service, G equals the approved effective computed pool. Let K be cumulative
authorized refund/cancellation reversals against that recognized entitlement;
0 <= K <= G, and net service earnings = G - K. Never sum whole historical pools.
Example only: G=100 then an authorized +50 correction gives G=150; a full approved
refund can reverse 150, not only the original 100. Each reversal allocates to
unreversed recognized credit sources, with stable keys preventing duplicate
debits. A rule change today alone cannot change G or K.

Cancelled service has zero service earning entitlement. Existing wrong recognition
needs an authorized append-only reversal; an unapplied correction remains a
visible discrepancy and cannot fund a new earning. Time compensation is outside
this bounded design: the allowed obligation kind is `service_commission`, and
the entry type CHECK does not permit `time_compensation`. **Approval required**
Q10/L04 for a separately typed compensation obligation and recognition/funding
policy before that category can be introduced. Never attach compensation to a
cancelled-service commission obligation. Pending corrections and recovery after
internal disbursement remain **Approval required** Q10/Q13/L04.

All earning/reversal actions use the shared lock-order, sealed-event and
minimum-rights contracts. No staff/owner report permission grants platform payout
authority; mock payment evidence cannot establish real completed-service funds.

## RLS/security impact

All five tables are backend-only with RLS/client revocations. Owner rule/report
access is salon-scoped; staff read access, if approved, returns only that staff's
allocations without customer names, contact, booked notes or bank details.
Platform financial roles cannot be inferred from staff/owner access. Correction
and rule activation use G01 audit coverage before enablement.

## Account-deletion behavior

Staff IDs reference retained inactive staff shells, not new personal snapshots.
Before implementation verify current erasure scrubs all linked staff shells and
profile links; preserve no name/photo/contact in rule/snapshot/entry rows.
Approval/actor FKs null using reviewed erasure; preserve booking/service and
numeric allocation links, never cascading staff/booking deletion. If an erasure
path currently hard-deletes a staff row, it must retain an anonymized shell or
adopt an approved nullable-link design before these RESTRICT FKs are introduced.
Detached staff identifiers, employee history and correction evidence require
Q16/L04/L05 classification. No new indefinite personnel-record retention is granted.

## Downgrade safety and rollback plan

Only an unused, empty schema can be dropped after writers stop and later
dependencies are removed. Refuse downgrade once any snapshot/allocation/earned
entry exists. Stop new rule activation/posting, preserve history and required
refund reversal processing, then forward-correct errors. Existing customer
payment/payout totals remain separate; rolling back reports must not count
staff allocations as a second platform expense or second salon payout.

## Unresolved approval and readiness

**Prepared for design review; not execution-ready.** Q04/Q10/Q13/Q16 and L02/L04/L05:
gross/net basis, booking/completion rule selection, precedence, earning event,
multiple-staff split, charges borne internally, cancellation/time compensation,
refunds, internal disbursement recovery and retention. No rates or historic
earnings are seeded. Broader multi-staff scheduling is outside this small migration.

Later verification: effective interval overlap, default/specific precedence,
multi-staff conservation, changed historical prices/rules, duplicate completion,
multiple partial refunds and rounding, cross-salon/staff reads, erasure, and
data-bearing downgrade refusal. No SQL/test execution occurs here.
