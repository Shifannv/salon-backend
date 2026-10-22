# G09: Slot-hold and concurrency support

**Design only; Approval required for implementation.** Ninth provisional review
group, with a cross-cutting activation gate on G01-G08. No Alembic revision ID or
parent is assigned. Inherits the [shared rules](README.md) and
[43-field treatments](ERASURE_CLASSIFICATION.md).

## Purpose and compatibility

C10/C11 require PostgreSQL-authoritative availability and conflict prevention,
with five-minute Redis holds providing temporary coordination. The
[reconciliation report](../MUMBAI_SCHEMA_HISTORY_RECONCILIATION_2026-10-18.md)
observed duration-stepped slots, staff-hours coalescing rather than intersection,
an insert-only closure guard, checked-in overlap protection and distinct existing
customer/salon/subscription lock paths. This is retained evidence, not fresh SQL
inspection or a tested deadlock.

G09 completes the bounded design for holds, common locking and SQL guard
integration; it creates no second booking authority, permanent Redis-hold table,
new payment ledger or assumed provider capability. No Python slot calculation
or direct booking/booking_services insertion is allowed.

Review order is not an interim operating order. The shared lock contract applies
to every earlier group. Its implementation may need separately reviewed early
primitives plus final G09 integration; no new finance or schedule writer may
activate while legacy writers can bypass or invert required locks. Final artifact
split/ordering and exact table ranks remain **Approval required** engineering
review. No executable IDs are chosen.

## Tables and columns

No new permanent hold table or hold-specific SQL column is proposed. Reuse
bookings/booking_services, salon/staff/service mappings, holidays/blocked slots,
G03 cancellation terms and G08 schedule revisions/requests/events. Existing
payment, audit, notification and durable booking-idempotency stores keep their
own responsibilities. A Redis hold ID is not a booking, consent or money fact.

Proposed ephemeral hold attributes: opaque random token, internal hold ID,
actor scope, salon/staff/resource set, requested service IDs, SQL-derived
interval/occupied range, eligibility/quote-policy versions where applicable and
absolute server expiry. Minimize data; no name, phone, provider reference,
credential or raw request/response. Do not log/put tokens in URLs or audit facts.
Return proof only to its authorized caller; compare a safe token verifier for
consume/release. Key/namespace/privacy treatment is **Approval required** Q15/Q16
where keyed identity digests are used.

Any buffer/extra-resource policy storage or exclusion-range expansion is a
separate bounded extension after Q11; no numeric default or speculative column
is hidden in this group.

## Atomic hold protocol and conflict behavior

1. Obtain candidate intervals only from the canonical PostgreSQL availability
   path. SQL validates current salon/staff/service/access state and derives
   duration/occupied interval under approved policy. Redis can annotate/filter
   returned slots; it cannot invent slots, shorten duration or promise booking.
2. A hold-acquisition operation atomically removes expired entries, checks all
   conflicting intervals/resources, verifies actor limit and inserts the new
   scoped hold with a five-minute server expiry. Matching only an exact start
   key does not prevent overlapping starts or differing service lengths.
   All affected keys/resources must share one atomic execution boundary
   (for example one salon Redis hash slot); no independent per-resource writes.
   Exact atomic data structure, resource scope, memory bounds and cluster
   behavior require implementation review, not a claim that SET NX alone works.
3. Key/container TTL and per-entry expiry must agree; stale interval indexes
   cannot preserve expired reservations. Bounded cleanup must fail safely on
   backlog rather than return false acquisition success. Atomic acquisition
   also checks limits for multiple holds by one actor under approved Q12.
4. A duplicate hold request returns its existing unexpired scoped hold only
   after token/actor/payload verification; a conflicting payload is not silently
   retargeted. Renewal, multiple-hold limits and reschedule-hold transfer are
   **Approval required** Q11/Q12. No implicit rolling renewal.
5. Consume/release atomically compare hold ID, actor, token and payload/resource
   binding before deletion. A delayed release cannot remove a newer hold.
   Expiry/release affects Redis coordination only; neither cancels a booking.
6. Booking creation still calls create_booking and rechecks SQL under the shared
   lock order; final exclusion is authoritative. Durable same-key replay returns
   the original booking even after its hold expires or was consumed. Concurrent
   different actors/keys cannot commit overlapping active bookings.
7. Commit PostgreSQL before any hold cleanup/cache invalidation. U05 requires
   durable outbox tracking for cancellation invalidation; an immediate attempt
   does not replace it. A crash
   after commit may leave a hold until expiry but cannot lose/duplicate the
   booking. Reconcile/replay the original command instead of a new booking key.
   No Redis network I/O or provider call is held inside PostgreSQL row locks.
8. U05 selects PostgreSQL-only booking fallback on unavailable Redis/partition,
   with truthful hold-unavailable reporting and fresh canonical availability.
   Booking still enforces all current database guards and final overlap protection.
   Q12 now retains only healthy-hold/limit/renewal details. Lost holds may allow
   competing attempts but never two overlapping committed database bookings.
   No Redis/provider/message I/O is held inside PostgreSQL business row locks.

## Shared SQL lock and eligibility integration

Use the index's exact namespace/order contract: discover the full affected
identity set without locking business rows; sorted profile gates; sorted existing
customer guards; sorted salon then subscription gates; sorted funding-scope
gates; existing-row locks by category/table/PK; then revalidate and write.
If discovery misses an earlier-ranked key, roll back/re-discover, not a late
out-of-order lock. A claimed worker row is not a substitute for early gates:
claim a separately committed queue lease, then enter the shared order.

Before executable review, publish an exhaustive table-to-rank map and examine
implicit FK, uniqueness, exclusion and trigger locks as well as explicit locks.
Cover API/worker creation, reschedule, closure, payments/refunds, subscription
application/sweep, authority retirement and erasure. The current salon_access/
customer locks taken in late booking triggers and subscription-only locking
must be coordinated at the earliest mutation entry, not documented away.
No ad hoc second lock namespace or arbitrary skipped deadlock retry. U04 adds
valid cancellation/slot release to this shared integration contract.

G08 owns reschedule persistence and its invoker operation. G09 specifies the
common guards it must use:

- Intersect salon and staff schedules; NULL staff hours inherit salon hours,
  explicit closed days remain closed. Include approved breaks, holidays, leave,
  closure/access state, service compatibility, SQL-derived duration, buffer,
  notice and same-day cutoff. Values, overnight/recurrence rules and resources
  remain **Approval required** Q11; the five-minute hold is the only fixed hold
  duration confirmed by C11.
- Recheck approval/activation/trial/paid access at quote, hold attempt and booking/
  payment initiation as applicable. Preserve existing appointments, receipt/
  completion permissions and separate renewal under Q06-Q09; never globally
  disable verified webhooks/refunds/dispute/payout reconciliation on expiry.
- Preserve GiST bookings_no_overlap for pending/confirmed/checked_in.
  Apply closure/approval/schedule/access guards on relevant schedule UPDATE as
  well as INSERT. Updating an interval cannot bypass the canonical rules.
- Reschedule only the locked same-salon booking; the internal availability
  helper may exclude that one booking and no arbitrary caller-selected ID.
  Revalidate frozen service duration, replacement staff compatibility, schedule
  revision and cancellation-policy snapshot. Failure leaves the original slot
  and all financial/notification facts unchanged.
- Concurrent hours/staff/service/access/authority/deletion changes participate
  in the same gates. Owner closure needs the exact current affected set and
  confirmation; no Redis hold hides booked work or supplies closure consent.
- Commit intent, schedule mutation, G01 audit, G03 policy consequences and durable
  notification/outbox facts atomically where applicable. External effects follow
  commit with stable identities; unknown outcomes stay reserved/reconciled.

## U04 committed cancellation and cache recovery

**Approved target:** a valid committed cancellation sets booking status to
cancelled and immediately removes that booking's occupancy from PostgreSQL
availability. A next eligible customer may book; payment refund is asynchronous
and cannot continue to block the old slot. Invalidate Redis slot/cache keys only
after database commit. PostgreSQL availability and booking revalidation, with
unique/exclusion constraints, remain final protection against duplicate booking.
This is a business invariant, not a verified current implementation.

The proposed protocol below implements that invariant and is subject to Q27/Q28,
RP07 and RC06 review before code/schema preparation. There is no standalone
availability design in this bundle; G08 owns closure/reschedule integration and
this group owns the shared availability/cache concurrency protocol.

### Authoritative availability and booking races

Canonical get_available_slots must exclude cancelled bookings from blocking
occupancy, consistent with the final active-state exclusion covering pending,
confirmed and checked_in. Refund/payment pending status must not reintroduce a
cancelled row into the blocking set. Other active bookings, independent closures,
resource/hours/service/notice/access constraints and legitimate new holds still
apply. Cancellation of a booking inside a newly closed interval does not open
the closed salon. No arbitrary client exclusion ID or Python slot calculation.

Cancellation, create_booking, reschedule and closure share the existing global
order: discover complete identities, sorted profile gates, sorted customer
guards, sorted salon then subscription gates, applicable funding scopes, ranked
rows by category/table/primary key, then revalidate and mutate. Never take a late
profile/customer/funding gate after a business row. If discovery missed an early
key, rollback/retry. Exact table ranks and implicit trigger/FK/exclusion locks
remain RP07; no ad hoc new namespace is chosen. All legacy writers participate.

Booking creation must re-read current availability in a fresh authoritative
snapshot after shared gates and before insert. A snapshot opened before waiting
for cancellation cannot be treated as post-commit truth; restart/retry where
needed. A pre-commit read may report busy, not reserve a future release. After
cancellation commits, fresh primary reads see its nonblocking state without
waiting for refund, cache TTL or worker. Existing SQL active-state exclusion
and unique booking/command identities remain final commit protection for two
customers racing overlapping intervals with different starts or keys. Neither
Redis holds nor an old positive availability result can bypass revalidation.
Rollback preserves old occupancy. Completion/no-show/reschedule winning first
forces cancellation to revalidate state/revision rather than overwrite history.

### Commit, durable intent and idempotent invalidation

Proposed cancellation transaction atomically records status, cancellation facts,
required financial planning, one slot-release audit identity, durable scoped
invalidation intent and notification intent. Choose a reviewed extension/reuse
of existing audit/outbox authority under Q28, not a new permanent hold table.
Commit before any Redis/provider/message network I/O. Rollback emits no release
or external invalidation; commit uncertainty reconciles original command.

After commit attempt immediate invalidation and deliver durable retry on failure
or crash. Scope includes every cached availability window/negative result,
staff/resource/date variant, booking detail and local-process/query cache that
derives occupancy, not merely one exact start key. Include cross-process API/
worker caches and old cancellation-response availability claims. Delayed retry
must be idempotent and monotonic: invalidate/mark suspect, never write an old
free-slot snapshot over current state. Exact key inventory, dispatch/ack,
backoff/alert threshold and worker lease are Q28/RC06 review; no numeric retry
policy is invented. Failed delivery stays pending/alertable, not falsely complete.
TTL is fallback memory cleanup only, never the immediate-release mechanism.

Cancellation invalidation must not blindly delete all interval holds. Only
consume/remove a leftover hold proven bound to the cancelled booking's old
command, token/actor and hold generation; compare identity atomically. A valid
new customer's hold survives even if it occupies the same interval. Missing
binding means do not delete; resolve against authoritative booking/command and
approved hold recovery, or return truthful coordination-unavailable. An orphan
hold from the cancelled generation cannot be treated as a valid reservation of
that interval until TTL. Exact binding/proof storage remains Q28/RC05 review.

### Stale-cache prevention and degraded reads

Required safe baseline under U05: authoritative availability always obtains full canonical
PostgreSQL coverage of the requested time window; Redis may accelerate hints,
but a cached busy/empty result cannot suppress freshly released SQL candidates,
and a cached free result cannot authorize booking. Checking only cached positive
slots misses newly free intervals and is insufficient. Readers do not depend on
successful invalidation, a Redis-only dirty flag or a functioning worker to know
whether cached occupancy is current. Lagging replicas cannot supply immediate
post-cancellation authoritative availability without a proved freshness barrier.

Optional later cache-serving design needs an independently readable,
commit-coupled database availability generation or equivalent reviewed fence.
Compare it against cached generation using a coherent fresh primary snapshot;
if absent, mismatched, unverified, or recovery is pending, bypass cached
occupancy and query canonical availability. Redis-only version numbers cannot
prove coherence through outage/restart. Exact durable generation representation
and any new columns/storage are unassigned and Q28 approval required.

Cache refill cannot race back to old occupancy: validate generation before
publishing, reject old fills after a mutation, and validate again on consumption
or bypass cache. In safe baseline mode old fills remain hints only and cannot
hide released slots. Refresh current PostgreSQL state after any invalidation;
never restore a cancellation-time free result after someone else booked it.
Booking must still revalidate even with a matching cache generation.

During Redis outage/lost invalidation, database release remains valid; U05
selects fresh canonical primary availability and PostgreSQL-only booking attempts
with truthful coordination-unavailable status. Healthy-hold policy remains Q12,
but a mandatory healthy hold cannot require an unavailable Redis before fallback.
Stale busy/free cache is not authority and cannot block/create bookings; legitimate
healthy new holds are distinct from stale entries. If PostgreSQL is unavailable
or fresh truth cannot be obtained, return retryable unavailability, never fabricate
success from cache. In partial partitions, SQL-only attempts may contend with
healthy held attempts; temporary holds never promise final booking entitlement.
All contenders revalidate SQL and final active-state exclusion resolves overlap.

### Release audit and notification contract

Use proposed logical event booking.slot_released from the
[U04 specification](../../verification/payment-subscription-booking-spec.md#44-u04-immediate-slot-release-after-committed-cancellation),
with one stable marker per booking/cancellation revision and immutable links to
actor, original interval/resources, old/new state, policy/reason, transaction
recorded time and command/correlation identity. It records removal of that
booking's occupancy, not current free-slot guarantee or financial success.
Actual enum/storage/commit-time representation remains Q28 review. Invalidation
attempt/delivery and notification attempt/outcome are separate observations,
not a second release/financial event. No raw token/contact/internal allocation.

Authorized same-key cancellation replay returns original safe outcome; changed
payload conflicts. Already-cancelled new-key request is no-op/original reference,
with no second marker/refund/notification. Outstanding original delivery may
retry. Current availability is obtained separately; a replayed cancellation
cannot promise the slot is still free. Authorization is checked before replay.
Notification intent commits with cancellation and dispatches after commit to
customer/authorized salon recipients; retries neither re-cancel nor re-reserve.
Channel/recipient policy, delivery retries and sanitized payload remain Q28.
No waiting for customer message/refund outcome to release database occupancy.

Future separately authorized evidence must cover: cancel then immediate fresh
read/rebook, rollback, concurrent different-key overlapping bookings, terminal
state races, Redis outage, worker crash after commit, failed/delayed invalidation,
stale-negative cache and old refill resurrection, independent API workers,
expired/orphan old hold versus new hold, replay and notification retry. None
runs here. No activation until legacy readers/writers satisfy this contract.

## U05 durable outbox retry, dead-letter and repair

The latest review selects database-independent-from-Redis cancellation commit,
durable **database outbox** invalidation and PostgreSQL-only outage fallback.
These replace earlier open D13 fallback alternatives and optional best-effort-only
invalidation. Exact storage adaptation and numeric recovery budgets remain
Q28/Q30 implementation review; no table/column or executable artifact is chosen.

### Atomic intent and delivery identity

Persist cancellation, one release audit and scoped invalidation/notification
intents together in the database transaction. Missing required outbox durability
causes transaction rollback, not a falsely successful cancellation. Redis/network
failure does not abort a valid database commit. An immediate postcommit delivery
attempt is an optimization of the same outbox job; it cannot create a second job
identity, bypass durable tracking or require Redis connectivity before commit.

Use a stable logical key bound to cancellation source/revision and action/scope;
cache cleanup and customer notification are separate delivery responsibilities,
not repeated financial commands. Outbox carries minimal internal references,
original occupancy/hold generation and action version, never raw credentials,
PII bodies or live tokens in logs. Authorization, historical booking state and
financial source cannot be modified through outbox retry. Source identity
survives worker restart and key rotation under existing Q15/Q16 constraints.

### Retry and dead-letter lifecycle

These are conceptual delivery states, not new implemented enums:

| Delivery state/event | Required behavior |
| --- | --- |
| pending | Committed durable obligation becomes claimable after transaction success only. |
| leased | Worker obtains bounded database lease and fencing identity in an independent short transaction; do not hold booking/payment rows during Redis I/O. |
| success | Acknowledge only after exact idempotent scoped action succeeds under current lease. Recheck job/fence on acknowledgement; a superseded worker cannot declare another generation complete. |
| transient failure, timeout or lost acknowledgement | Record sanitized category/attempt/time, retain original job and retry after capped exponential backoff with jitter. Unknown Redis result is safe to retry by same idempotent invalidation identity; never re-cancel or retry money with new reference. |
| worker crash/lease expiry | Another worker reclaims through durable fencing, retains attempt history and safely repeats original action. At-least-once delivery, not exactly-once network execution, is the assumption. |
| permanent validation error or exhausted configured attempt/age budget | Persist dead-letter state, reason code and original source; alert designated operators. Stop automatic retry of this poison action, not canonical availability/fallback or financial reconciliation. |
| repaired and requeued | Authorized audited repair resumes same logical obligation with new delivery attempt/fence; immutable original source/history remains. No duplicate release/refund/notification intent. |

Retry delay/cap/jitter, lease, attempt/age budget, alert threshold/response owner
and escalation service levels must be explicit bounded configuration under Q30
before enablement; section 13.5 now lists unapproved numeric candidates,
not selected defaults. Redis rate limiting
or overload uses bounded work/backpressure, not unbounded parallel replay. Track
pending age, attempts, expired leases, dead-letter backlog and sanitized failure
categories. Notification delivery has separate backoff/acknowledgement and may
also dead-letter; it never holds the slot or financial finality hostage.

### Safe invalidation and stale-state recovery

Delete/mark stale all dependent availability windows, negative/positive cache,
booking details and per-process projections via reviewed scope inventory. Do not
write cached free availability from cancellation-time snapshot. Validate/reload
from fresh primary data, preserving a later booking/closure or valid new hold.
A delayed retry compares source/hold generation before any hold removal; it may
invalidate a generic derived cache key again safely but cannot erase a newer
actor's live hold or roll back its booking. Outbox delivery does not use Redis
as proof that the underlying cancellation committed.

Full primary PostgreSQL window coverage is the required safe baseline while
cache freshness is unproved; cached negative results cannot hide released slots.
Any optional later serving of cache as an availability answer requires a reviewed
commit-coupled database revision/freshness fence, checked on refill and read.
Redis-only dirty flags, notifications or TTL are insufficient through outage.
Dead-letter or lease expiry does not clear a pending freshness barrier. Mark a
scope current only after validating the latest database revision and no later
undelivered relevant mutation; an old successful job cannot certify new scope.
If no such verification exists, continue primary reads permanently rather than
silently re-enable cache authority. Booking rechecks SQL even with a fresh fence.

### Audited operator repair

Designated engineering/operations repair authority (exact principals/scopes Q30)
inspects source audit, committed cancellation/revision, current booking/resource
state, outbox attempts and minimal scoped key inventory. Determine retryable
connectivity, poison action mapping, old lease or obsolete hold generation.
Repair is targeted invalidation/rebuild from canonical current data and safe
compare-bound old-hold cleanup; no global Redis flush, financial edits, cancellation
rollback, provider call, or deletion of another user's hold. An obsolete intent
may be resolved only with recorded proof its effect is already satisfied by
newer scope/revision and no relevant stale state remains; this is audited
supersession, not dropping dead letters.

Record repair actor, reason, job/source, prior failure, action/version and
verification evidence. If payload correction is necessary, preserve original
immutable source and append a reviewed linked corrective delivery, not alter
financial or audit facts. Requeue/reconcile acknowledgement under current fence;
leave the event unresolved/alerted if correctness cannot be established. Cache
recovery never changes a paid/refund/booking final outcome. Return to optional
cache use only after current-primary validation, scoped cleanup and consumer
compatibility verification; until then SQL fallback remains the safe path.

## U05 cancellation, hold and payment race review

All PostgreSQL mutators share discovery then sorted profile, customer, salon,
subscription, funding gates and ranked booking/payment/cancellation/audit rows.
Fresh revalidation after waiting is required; no payment row may be held while
waiting to acquire earlier booking/salon gates. Durable signed webhook receipt
may commit separately before ordered business application; actual provider facts
are recorded once even if the booking is cancelled. Redis calls and signature/
provider I/O do not hold these business row locks. RP07 retains exhaustive
per-table/implicit trigger-lock review, not a claim of current enforcement.

| Race | Required invariant |
| --- | --- |
| Cancel versus new booking | Old active occupancy blocks precommit attempts; cancellation first lets fresh revalidation proceed. Two released-slot contenders admit at most one overlapping SQL commit. Neither cache nor hold creates a booking; rollback leaves original occupancy. |
| Cancel versus tentative hold acquisition | SQL candidate read and atomic Redis acquisition are separate phases. Acquire outside database row locks, then validate current PostgreSQL booking/resource/policy revision. If stale, compare-release only that tentative hold, or return truthful coordination failure. A later change after validation still cannot authorize booking without a fresh SQL recheck. Cancellation cleanup preserves any newer valid hold. |
| Cancel versus payment confirmation | Verify/deduplicate receipt, then ordered booking/payment application. Payment first updates capture facts that cancellation reads; cancellation first leaves booking cancelled while later capture is recorded for original obligation and routed to refund/review. Never reopen cancelled or rebind money to a replacement customer. |
| Two cancellation keys or cancel versus completion/check-in | Guarded state/version update and booking-root source uniqueness permit one conflicting final transition and one cancellation side-effect set. Loser conflicts/no-ops; customer loses eligibility once check-in commits. Scoped owner/admin cancellation requires reason/audit, never customer override. |

A hold has no atomic commit with PostgreSQL. Revalidation minimizes stale Redis
entries but cannot prove a globally linearizable distributed hold; final SQL
constraints supply booking safety. Stale/uncertain cache or hold proofs cannot
block canonical availability or fabricate outcome. Legitimate healthy holds may
still supply approved temporary coordination. Exactly one final booking outcome
means one conflicting terminal winner per booking revision and at most one
active overlapping commit; zero winners is valid when both fail eligibility.
Duplicate payment receipt/outbox delivery is at-least-once and requires durable
source dedup, not an unsupported exactly-once network claim.

Future separately authorized evidence must exercise independent DB connections
and API workers, cancellation versus capture/hold phases, expired worker leases,
Redis timeout/restart/partition, cache refill races, dead-letter and repair,
late capture after replacement booking and different-key repeat cancellation.
Only Markdown checks run now; design reasoning does not establish race safety.

## Indexes and constraints

Reuse existing booking staff/time GiST exclusion, FK indexes, customer daily
guard index, access/subscription-eligibility and idempotency indexes. No duplicate
indexes or speculative constraint names. Evaluate new actual queries after Q11;
large index changes need a separate bounded concurrent build/validation plan.

A Redis interval check cannot replace a SQL constraint. If approved buffers
change occupied ranges, separately review exclusion representation, old bookings,
backfill/conflict scan, locks and mixed-writer compatibility before any change.
No use of NOT VALID for unique/exclusion constraints is implied.

## Final technical approval defaults - recommendations only

TP01/TA01-TA10 remain **Approval required**; see
[specification section 13.5](../../verification/payment-subscription-booking-spec.md#135-final-technical-approval-defaults---recommendations-only)
and [technical approval register](APPROVAL_REGISTER.md#final-technical-approval-defaults---recommendations-only).
No TA value is adopted by existing worker/Redis settings in this review.

| Candidate | Recommended default, not approved |
| --- | --- |
| Retries | Five retries after initial dispatch, proposed maximum six dispatches; successive failure delays 1m, 5m, 30m, 2h, 12h. Counting, jitter and age cap need Q30 selection. |
| Lease | Five minutes, database time/fencing; timeouts, renewal/heartbeat and reclaim need review. Expired worker may still complete network work, so side-effect idempotency and fenced acknowledgement remain necessary. |
| Dead-letter | Permanent error or exhausted selected budget retains job/source/attempt history, alerts operators and waits for audited repair; no loss of intent or false successful cleanup. |
| Alerts | Sentry plus admin email, sanitized internal IDs/error class only; recipients, response targets, dedup/escalation and channel retention remain pending. No service/address configured. |
| Repair | U06: a single super-admin with `aal2`, with a reason, an approval record and a complete audit trail; no two-person approval. Targeted invalidation/canonical rebuild/original-job requeue only; no global flush or money/state rewrite. Named permissions and the approval-record format remain open. |
| Operational retention | 90 days after delivered/verified superseded resolution, not creation. Unresolved/dead-letter/held evidence needs lawful exception/review, no automatic expiry or indefinite exemption. Preserve necessary minimal dedup linkage under its separate approved schedule. |
| Financial audit | Separate finite lawful schedule with per-field scrub/holds/access; no numeric duration and no inherited 90-day window. |
| Encryption/keys | Ciphertext/version reference in database; wrapping keys in separately managed KMS, secrets in managed secret store, or adequate provider tokenization. No plaintext secrets in database/Git/logs/outbox/cache/replay/backups; concrete services, region, access and rotation unchosen. |

The discrete delay proposal is not an approved exponential/jitter formula. Crash,
lease expiry or lost acknowledgement retains original logical identity and
recorded attempt budget; manual repair does not start an unbounded fresh cycle.
Primary fallback, final PostgreSQL revalidation and new-hold-safe cleanup stay
required regardless of alert outage, dead-letter or proposed 90-day retention.
TA01 monetary review remains a proposal; U06 rejected the TA02 extra owner-admin
gate. If any approval request state is ever introduced, it does not itself cancel
or release a checked-in slot.
No backend/SQL/schema/monitoring/key changes or runtime proof are produced.

## RLS/security impact

No client SQL grant or new Data API function access. Keep availability/booking/
reschedule behind authorized FastAPI use cases with existing function privileges,
pinned paths and current profile role/ownership. Rate-limit hold churn without
logging token or actor/contact input. Prevent cross-actor release, cross-salon
reuse, arbitrary interval shortening and service/payload substitution.

The report's service_role/owner bypass and creator-default ACL risks remain.
Neither Redis proof nor a custom GUC is financial authority. G01 audit and
minimum privileges, G02 sealed accounting and G04 reservations remain required.
No new SECURITY DEFINER shortcut, realtime financial publication or role mutation.

## Account-deletion behavior

Invalidate scoped active holds and related cache/replay payloads through a
reviewed erasure step; actor namespace must support cleanup without storing
plaintext contact in keys. TTL is fallback cleanup, not proof of erasure.
Profile gates prevent a deleting actor from committing new business. If Redis
cleanup cannot be confirmed, follow the approved durable retry/fallback policy;
do not falsely complete the erasure step or resurrect actor access.

Preserve already committed booking/financial shells and open obligations.
No hold survives as an immutable personal audit payload. Any necessary
abuse/dedup evidence is a separate Q16/L05-reviewed minimal digest, not automatic
retention of all Redis content.

## Downgrade safety and rollback plan

There is no SQL hold table to drop. Stop new acquisition/coordination consumers
only under a reviewed Q12-safe mode; do not flush unrelated Redis data or remove
SQL exclusion/guards. Existing bookings, G08 revisions and external obligations
require compatible reads/reconciliation and forward repair. Expiring a hold
does not roll back a committed booking; no financial or schedule history is
deleted to return to an earlier release.

## Unresolved approval and readiness

**Prepared for design review; not execution-ready.** Q06-Q09/Q11-Q13/Q15/Q16,
L01/L05 where relevant: hours/resources/buffers/notice/cutoff, expiry/reschedule
handling, healthy mandatory-hold behavior, actor limits/renewal, privilege/lock-rank
review, token/digest privacy and deletion handling. P01-P06 remain separate for
any dependent money/provider behavior; this group establishes none.

Q27/Q28/Q29/Q30 retain exact checked-in monetary/scoped authority, outbox
storage/fencing, numeric retry/dead-letter/repair and stale-cache evidence. U05
selects no customer cancellation after check-in, reason/audit for scoped owner/
admin, durable outbox and primary SQL fallback; no implementation is authorized.

Future separately authorized verification: independent concurrent booking/
reschedule/closure, different starts/durations/resources, stale service/hours/
access changes, same-key replay and different-key conflict, expired-token release
race, Redis outage/failover/multiple-worker cleanup, crash-after-commit,
profile-deletion race and no mixed-writer lock inversion. Expected booking
conflict contract is subject to API review; no application, Redis, SQL, Alembic,
provider or deployment action runs in this design phase.
