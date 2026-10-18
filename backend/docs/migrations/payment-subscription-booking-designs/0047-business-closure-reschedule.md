# G08: Closure/reschedule support

**Design only; Approval required for implementation.** Review group G08.
Schema dependencies: G01, G03, G07; G02/G04 for applicable financial effects. No Alembic revision ID or parent is assigned.
The filename is a historical locator, not execution order. Inherits the
[shared rules](README.md), [field treatments](ERASURE_CLASSIFICATION.md) and
[G09 concurrency contract](09-slot-hold-concurrency-support.md).

## Purpose and compatibility

C10/C11 require PostgreSQL-authoritative availability and overlap protection.
Reuse `salons.accepting_bookings`, soft-deletable `salon_holidays`, `blocked_slots`,
existing closure preview/apply, booking/action-request audit and notification
outbox. Pausing new business continues to preserve existing appointments.
No permanent Redis-hold table is proposed; five-minute Redis holds never commit
a booking or bypass PostgreSQL. U05 selects SQL-only Redis-outage fallback; Q12 healthy mandatory-hold/limit
details remain pending.

## Tables and columns

| New table | Proposed columns in addition to shared ID/timestamps |
| --- | --- |
| `business_closure_operations` | `salon_id uuid` -> salons, `staff_id uuid?` -> staff, `start_datetime timestamptz`, `end_datetime timestamptz`, `salon_timezone text`, `scope_code text` (salon/staff), `closure_kind text` (interval/holiday), `holiday_id uuid?` -> salon_holidays, `blocked_slot_id uuid?` -> blocked_slots, `status text` (previewed/confirmed/applied/withdrawn/expired), `affected_set_digest bytea`, `preview_expires_at timestamptz`, `requested_by uuid?`, `confirmed_by uuid?`, `reason_code text`, `idempotency_digest bytea`, `version integer` |
| `business_closure_booking_actions` | `closure_id uuid` -> operations, `booking_id uuid` -> bookings, `expected_schedule_revision integer`, `expected_booking_state text`, `original_staff_id uuid` -> staff, `original_start timestamptz`, `original_end timestamptz`, `resolution text` (cancel/reschedule), `status text` (pending/applied/conflict), `cancellation_outcome_id uuid?` -> booking_cancellation_outcomes, `reschedule_request_id uuid?` -> booking_reschedule_requests, `reason_code text` |
| `booking_reschedule_requests` | `booking_id uuid` -> bookings, `expected_schedule_revision integer`, `original_staff_id uuid` -> staff, `requested_staff_id uuid` -> staff, `booked_duration_minutes integer`, `booked_services_digest bytea`, `original_start timestamptz`, `original_end timestamptz`, `requested_start timestamptz`, `requested_end timestamptz` (SQL-derived), `salon_timezone text`, `status text` (requested/approved/declined/withdrawn/expired), `expires_at timestamptz`, `requested_by uuid?`, `decided_by uuid?`, `decided_at timestamptz?`, `reason_code text`, `idempotency_digest bytea`, `version integer` |
| `booking_schedule_events` | `booking_id uuid` -> bookings, `reschedule_request_id uuid?` -> requests, `closure_id uuid?` -> operations, `schedule_revision integer`, `old_staff_id uuid` -> staff, `new_staff_id uuid` -> staff, `old_start timestamptz`, `old_end timestamptz`, `new_start timestamptz`, `new_end timestamptz`, `old_terms_id uuid?` -> booking_cancellation_terms, `new_terms_id uuid?` -> terms, `actor_id uuid?`, `event_key text`, `reason_code text`, `effective_at timestamptz`, `correlation_id uuid`; `command_audit_event_id uuid` -> G01 sealed audit event for new-mode commands |

Add `bookings.schedule_revision integer NOT NULL DEFAULT 0`, a metadata version
with nonnegative check. Zero denotes pre-reschedule history, not a fabricated
original-schedule event. Nullable cyclic closure/request links are installed
after both tables exist. Immutable schedule events preserve old intervals.

## Indexes and constraints

- Unique operation/request idempotency digests, action `(closure_id, booking_id)`,
  event key and event `(booking_id, schedule_revision)`. At most one requested
  reschedule per booking via partial unique index. Index all FKs, closures
  `(salon_id, start_datetime, end_datetime)`, pending actions `(closure_id, status)`,
  requests `(expires_at)` where requested and schedule events by booking/revision.
- Positive intervals; nonnegative expected/revision values; terminal requests
  require decision timestamps. Staff and canonical closure rows must match the
  operation's salon. Salon closures have no staff scope; staff closures require
  staff. A canonical holiday or block, when materialized, matches closure kind.
- SQL snapshots `booked_duration_minutes` from the booking's immutable duration
  and verifies it against booked service-line durations, with a digest of those
  lines. Require requested_end = requested_start + that duration. Client-supplied
  end time or today's staff/catalog duration cannot shorten/extend it. A legacy
  duration inconsistency blocks automatic reschedule pending an audited repair;
  never rewrite booked snapshots to make it fit. Buffer occupancy, if later
  approved, is separately governed and cannot reduce the booked service duration.
- Original staff, replacement staff, booking, closure and all booked services
  must belong to the same salon. At approval, replacement staff must be active
  and currently authorized to offer every booked service through active
  staff/service mappings. Apply the approved treatment of retired services; if
  unavailable or undecided, block automatic reassignment rather than substitute
  services/prices. No cross-salon move is supported by this operation.
- Exact affected-set proof compares IDs **and** schedule revision, current state,
  interval and assignments under the salon advisory lock, not just a client list.
  A stale preview requires a new preview/confirmation. Store no customer PII in
  the digest input or action rows. No partially hidden existing bookings.
- Confirmation of a new-policy closure requires an explicit resolution for every
  affected booking. If a reschedule still awaits customer/salon approval, do not
  mark its action resolved or silently cancel it; keep the operation un-applied
  until all required resolutions can be validated atomically. Recurring/long
  closures need separately approved bounded expansion; no RRULE execution here.

## PostgreSQL function and concurrency design

This migration's later implementation must review the **current** 0035 function
bodies and amend canonical `create_booking`, `get_available_slots` and
`guard_booking_against_closure` only through reviewed SQL. The existing closure
guard is insert-oriented; equivalent protection is needed on schedule updates.
No Python slot calculation or direct Python booking/service insertion is allowed.

Introduce a backend-only invoker `reschedule_booking` SQL operation, not a
second creation path. It takes a trusted request ID, locks the salon and booking,
checks current state/revision/authority inputs, checks the canonical availability
rules for the new interval and updates the existing booking in that transaction.
Availability alone is insufficient: creation's service-compatibility checks are
not automatically inherited by `get_available_slots`. The reschedule operation
must separately validate the frozen service set, staff compatibility and derived
end/duration before using canonical availability, all in the locked transaction.
For its own occupied slot, an internal availability helper may exclude only the
locked booking; never expose a client-controlled arbitrary exclusion ID. Public
availability continues to include that booking until a reschedule commits.

Serialize create/closure/reschedule on the same salon advisory-lock convention
before availability evaluation; lock affected bookings and both old/new staff
resources in deterministic order. Preserve 0035's `bookings_no_overlap` exclusion
(pending/confirmed/checked_in) and all approval/trial/daily/no-show/collection
guards. Reschedule cannot re-open a terminal booking or bypass unpaid limits.
Update closure action, schedule revision, old/new policy terms and sanitized
notification/outbox intent atomically. Provider refund calls run after commit.

Use the shared lock-order contract, acquiring affected profile/customer gates,
salon/subscription gates and any financial scope before ordered row locks. Recheck
staff mapping and hours after locking; concurrent mapping/deactivation mutations
must participate too. The original slot stays occupied until commit. PostgreSQL
exclusion constraints enforce the final interval even after a prior availability
result. Any failure leaves original staff, duration, interval, price and policy
binding unchanged. Approval increments schedule_revision exactly once with its
unique event. Duplicate requests replay the committed result, not a fresh move.

Full salon/staff-hours intersection, buffers, notice, cutoff and expiry policy
need Q11 values and current-function review. This small design adds closure/
reschedule persistence and required guards; it does **not** claim to complete
every missing C10 availability feature. G09 owns the bounded concurrency/hold
support review and any proposed resource/buffer policy or exclusion-range
extension after Q11. Neither group
chooses numeric defaults. G08 cannot activate schedule updates until G09's common
SQL lock and eligibility contract is implemented and verified.

## U04 availability integration after cancellation

There is no separate availability-only design; this group and G09 define its
existing SQL guards. U04 approves immediate removal of a valid committed
cancelled booking from canonical availability, allowing another eligible
customer to book without waiting for refund delivery, Redis/cache TTL or
notifications. Invalidate related Redis slot/cache keys after commit. PostgreSQL
still revalidates current availability inside each booking transaction, with
unique/exclusion constraints as final duplicate-overlap protection.

A cancelled row is excluded from blocking bookings even when its refund is
pending/failed. Preserve active pending/confirmed/checked_in exclusion and all
independent salon/staff/service/hours/closure/access constraints. A closure and
its cancellation may commit together: the cancelled booking ceases to block,
but the independently closed interval remains unavailable. Never advertise
unconditional free availability merely because an occupancy audit exists.

Create/cancel/reschedule/closure share profile/customer/salon/subscription/funding
then ranked-row locks, with fresh authoritative revalidation after shared gates.
Cancellation first permits subsequent eligible create; create seeing old active
booking may conflict and retry fresh after cancellation. Rollback preserves old
occupancy; two racers for the released interval admit at most one overlapping
commit. Concurrent reschedule/closure/cancellation compare current state/schedule
revision and affected set; a stale preview needs renewed confirmation. No late
inversion or external Redis/provider/message I/O inside the locked transaction.

Cancellation states/replay and one logical slot-release audit plus durable
post-commit notification/invalidation intents follow
[specification section 4.4](../../verification/payment-subscription-booking-spec.md#44-u04-immediate-slot-release-after-committed-cancellation).
A cancellation request alone is nonbinding; completed/no_show/rejected cannot
be silently cancelled, and U05 checked-in cancellation forbids customers while requiring scoped
owner/admin reason and audit. Concrete scopes/monetary remedy remain Q20/Q29. Preserve
U03 explicit no-show grace/confirmation. Repeated committed cancellation cannot
emit new refunds/release markers/messages; outstanding original delivery retries
are safe and do not restore old reservation.

[G09 recovery](09-slot-hold-concurrency-support.md#u04-committed-cancellation-and-cache-recovery)
requires canonical fresh window coverage when cache is stale/unverified, durable
invalidation retry, protection against pre-cancellation refill resurrection and
old-hold cleanup that never removes a newer valid hold. A stale empty/busy cache
cannot hide the newly released candidate; a stale free cache cannot bypass
booking checks. Exact storage/ranks/reader rollout remain Q28/RP07/RC06, not
implementation evidence. Notifications describe cancellation/refund status
separately, dispatch after commit and retry without reversing slot release.

## U05 checked-in and outage race review

Customer cannot cancel checked-in work. Current salon owner/scoped admin may
cancel with mandatory cause/reason and atomic actor/time/state/revision audit;
no new staff permission is inferred. Completion/no-show/reschedule/cancellation
share booking/version gates; one conflicting final state wins and stale work
conflicts/replays without overwriting it. Closure previews must revalidate the
actual committed state/schedule/affected set, not cached availability. Monetary
remedy for operator cancellation is distinct from U03 customer timing bands;
known approved refund is reserved/asynchronous, unknown remedy produces durable
financial review and restricted retained funds, never fabricated completion,
refund paid, payout entitlement or automatic bank debit (Q29).

Redis failure cannot delay a valid database cancellation commit. Cancellation
atomically records database outbox invalidation, audit, financial planning and
notification intents; required database persistence failure rolls back, while
Redis/network delivery occurs only afterward. Fresh primary PostgreSQL availability
and SQL-only booking admission are selected U05 fallback; earlier Q12 undecided
outage admission is superseded. Healthy-hold/limit policy remains open. Stale
busy/free cache cannot block/create bookings; no PostgreSQL freshness means
truthful retryable failure rather than cache-only acceptance. Independent closure
or valid healthy new hold still has its normal meaning.

Cancel versus new booking uses shared discovery/profile/customer/salon/
subscription/funding then ranked-row order and fresh SQL revalidation; exclusion
allows at most one new overlapping active commit. Cancel versus Redis hold
acquisition has no distributed atomic commit: acquire advisory hold outside DB
row locks, validate canonical state/revision afterward and compare-release stale
tentative proof. Later booking always rechecks PostgreSQL. Cleanup never deletes
a newer actor's valid hold. Cancel versus payment confirmation applies to the
same booking/payment under shared order: record capture once regardless of
cancelled state; never reopen old booking or attach money to a replacement.
Durable webhook receipt may precede separate guarded application, without
holding payment-first business locks awaiting earlier gates.

Outbox leased retry, bounded backoff/jitter, dead-letter alerting and targeted
audited operator repair follow
[G09 recovery](09-slot-hold-concurrency-support.md#u05-durable-outbox-retry-dead-letter-and-repair).
Dead-letter is unresolved delivery, not completed cleanup or permission to
restore occupancy. Primary fallback stays active until current-state freshness
is proved; old job success cannot certify newer mutation. Repair cannot flush
unrelated Redis state, erase audit/source, reverse cancellation or issue money.
Exact lease/attempt/age/alert/repair access settings remain Q30. Exactly one final
outcome means no duplicate conflicting terminal state or overlap, not guaranteed
success of any contender or exactly-once network delivery. No race test runs here.

## Final technical approval defaults - recommendations only

The [TP01 technical approval register](APPROVAL_REGISTER.md#final-technical-approval-defaults---recommendations-only)
and [specification section 13.5](../../verification/payment-subscription-booking-spec.md#135-final-technical-approval-defaults---recommendations-only)
contain the final candidate package. Every TA01-TA10 choice is **Approval required**.
No proposal overrides final database availability, valid committed cancellation
release, original money obligations, or historical policy/price snapshots.

Recommended authority is customer after-check-in cancellation forbidden, owner
request requiring admin approval, and admin reason/audit. The owner-to-admin
stage is an unapproved extra gate: a pending request keeps the existing booking
occupied and must participate in closure/reschedule state/revision checks.
Checked-in monetary remedy remains finance/legal review, never automatic U03
penalty, refund amount or payout. Only actual valid cancellation commit releases.

Recovery candidates are five retries after initial dispatch at successive delays
1m/5m/30m/2h/12h, five-minute lease, retained dead-letter with Sentry plus admin
email, and scoped two-person finance/admin repair. No retry/alert may redo a
closure, cancellation, notification intent or financial effect. Ninety-day
resolved outbox retention is proposed separately from unresolved-job/dedup and
financial audit schedules, which need explicit lawful approval. Managed encryption/
separate KMS and secret-store proposal still needs concrete access/region/rotation
and old-copy review. These notes provision no service, key, grant or runtime value.

## RLS/security impact

All four tables are backend-only with RLS/client revocations; SQL entry points
are not callable by client roles. Owners can manage only their salon and
customers only their eligible booking requests through authorized use cases.
Staff/admin powers are explicit, not assumed. Financial consequences use G02-G04
and G01 audit coverage, never a settings endpoint bypass. Cache invalidation
occurs after commit and durable replay returns the original outcome. No runtime
cache, frontend or notification worker behavior is changed by these documents.

## Account-deletion behavior

No names/contact/reason free text are copied. Requester/confirmer/decider/actor
FKs clear before profile erasure. Use **ON DELETE SET NULL** for `holiday_id` and
`blocked_slot_id` because owner erasure explicitly deletes those operational
rows; keep closure/schedule history on inert salon/booking shells. Other financial
links RESTRICT. Current account erasure must invalidate pending reschedules and
closure work and retain no arbitrary old messages; test races with deletion,
future-booking cancellation and refund handoff. Q16 governs retained metadata.

## Downgrade safety and rollback plan

Empty tables, all booking revisions zero and no new function consumers permit a
reviewed structural downgrade; restore exact parent function bodies without
losing 0039/0040 hardening or any historical guard. Refuse after any applied
closure/reschedule/event, pending request or external notification/refund effect.
Stop new requests/closure applications, preserve current schedules and financial
reconciliation, expire/resolve pending work explicitly and repair forward.
Rollback never moves bookings back into their original occupied/closed slots.

## Unresolved approval and readiness

**Prepared for design review; not execution-ready.** Q02/Q03/Q07/Q08/Q11-Q13/Q16,
L01/L05: closure refund treatment, governing cancellation start/policy after
reschedule, post-expiry rescheduling, customer consent, repricing, overnight/
recurring closures, buffer/notice/cutoff values, hold fallback and authorities.
Preserve historical service snapshots; price/service changes need a separately
approved adjustment workflow, not edits to booked service rows.

Later verification: stale previews, new booking between preview/apply, concurrent
reschedule/booking/closure, overlapping new staff, unchanged original reservation
on failed approval, checked-in conflicts, idempotent notifications/refunds,
privacy/erasure and refusal to downgrade used schedule history. No SQL runs here.
