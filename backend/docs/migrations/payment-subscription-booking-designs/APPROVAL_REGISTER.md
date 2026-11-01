# Approval decision register

Revised: 2026-10-19 (Asia/Calcutta). **Prior policy approvals recorded; U06 and U07 added; owner finance F01-F12 added (2026-10-29); unaccepted TP01 technical defaults remain Approval required. Implementation/execution held.**

This file records explicit user policy approvals and remaining choices; it grants
no implementation, provider-access or execution authorization. C01-C26 in the
[specification](../../verification/payment-subscription-booking-spec.md#21-owner-approved-rules)
are confirmed target requirements, not approval of unresolved Q/P/L decisions,
field treatments, runtime rights, migration history or Redis implementation.
Recommendations, examples, silence and mock passes never supply a selected value.
Unset policy blocks dependent new workflows; existing financial and erasure
obligations remain owned and reconciled under their applicable historical policy.

Exact Q questions are copied from specification sections 13 through 13.4. P/L entries preserve
their exact source review prompt as the question. RP, MH, RC and L05-F identifiers
are register-local questions derived from the designs/report, not approved rules
or executable revision IDs. Alternatives below remain review options only for
unresolved portions; selected scopes below supersede incompatible alternatives.
All choices must satisfy confirmed requirements. No rejected proposal implies a replacement.

Decision-owner functions are proposed accountable owners, awaiting named assignment.
Finance cannot replace product consent, legal sign-off, security approval or
provider evidence. Entries explicitly marked **Partially approved** record only
the selected scope from user instructions U01-U05 below. Other entries remain
**Approval required; no selected option or sign-off recorded**. Policy approval
is not evidence of provider feasibility, legal sign-off or runtime implementation.

Cashfree account: **No** means local policy/design review needs no account;
**Yes** means account-specific evidence is required to resolve the provider claim;
**Conditional** means the local decision needs no account but the named branch
needs later account evidence. None authorizes access now. Mock evidence cannot
verify pricing, KYC, custody or finality; sandbox proof is limited to sandbox.
Blocking groups are direct affected workflows; downstream dependencies inherit
blocks. All groups inherit applicable shared security/privacy/concurrency gates.

Sources and revised group mapping:

| Group | Design |
| --- | --- |
| G01 | [Audit and authority foundation](0048-admin-financial-audit.md) |
| G02 | [Provider-fee reconciliation](0041-provider-fee-reconciliation.md) |
| G03 | [Cancellation policy and refund obligations](0042-cancellation-policy-versions.md) |
| G04 | [Payout/dispute records](0043-payout-dispute-records.md) |
| G05 | [Payout schedules](0044-payout-schedules.md) |
| G06 | [Staff commission ledger](0045-staff-commission-ledger.md) |
| G07 | [Subscription lifecycle](0046-subscription-lifecycle.md) |
| G08 | [Closure/reschedule support](0047-business-closure-reschedule.md) |
| G09 | [Slot-hold and concurrency support](09-slot-hold-concurrency-support.md) |

Shared sources: [design index](README.md),
[field classification](ERASURE_CLASSIFICATION.md),
[specification](../../verification/payment-subscription-booking-spec.md) and
[Mumbai reconciliation report](../MUMBAI_SCHEMA_HISTORY_RECONCILIATION_2026-10-18.md).
Report observations are historical evidence, not fresh inspection here. Its
43-table proposal predates the revised 45-table bundle; nine review groups are
not an executable chain. Numeric filenames assign no IDs, parents or deploy order.

**Precedence of later records.** U01-U05 are kept as dated history. Where U06 or U07
selects a value for the same scope, the later record governs. An older "unresolved"
statement in a decision entry below is history unless the later record's "still open"
column repeats it. Items that no record selects stay **Approval required**.

## Historical policy approval record U01

- **Evidence:** explicit user instruction in this conversation, received
  2026-10-18 (Asia/Calcutta), immediately following creation of this register.
- **Approver:** requesting user; personal identity/title not supplied. Recorded
  as product/business policy direction, not a named finance/legal/security reviewer.
- **Record version/date:** U01 / 2026-10-18. Policy rollout/effective date,
  environment and treatment of legacy/open operations are not specified;
  no retroactive rewrite, configuration change or activation is authorized.
- **Approval extent:** the exact selections below only. The late-cancellation
  refund-first 20/80 scope is superseded prospectively by U02 below; it remains
  historical evidence, not the current new-policy formula. Remaining subquestions,
  evidence dependencies and distinct execution approvals remain open.

| Selected scope from user instruction | Decision mapping | Remaining boundary |
| --- | --- | --- |
| Completed online service: customer pays service total; platform commission INR 0; actual provider charges reduce salon payout. | C01-C03 reaffirmed; Q04 completion fee bearer and Q08 service-total amount selected. | Other cancellation fee bearers, tax/recognition, reserve/true-up, deposits, direct receipts and legacy orders remain open. |
| Cancellation within four hours: refund customer first, then allocate retained amount 20% platform / 80% salon. | Q01 option B and retained base selected; C04 ratio reaffirmed. | Exact refund amount/formula R, exactly-four-hour equality, no-show/early/salon-caused policy and reschedule snapshot remain open. |
| Payout: 48-hour hold after service completion, no active dispute; manual and automatic use the same checks. | Q05 ordinary-service hold duration/origin selected; C05/C06 reaffirmed. | Dispute scope/release/later recovery, cancellation exception, approval stages and provider withholding/finality remain open. |
| Subscription: two calendar months trial; no booking cap. | C07 reaffirmed; Q06 no-cap trial selected. | Activation versus approval, timezone/month-end/exclusive boundary and existing-salon transition remain open. |
| Subscription: seven-day renewal grace; no new bookings/payments during grace; existing bookings can finish. | Q07 seven-day renewal grace, booking/payment-initiation restrictions and completion permission selected. | Day-count/timezone/start/end, trial applicability, direct-receipt permission, late captures and consent/legacy handling remain open. |
| Staff: no cancelled-booking commission; commission uses immutable booking snapshot. | Q10 cancellation exclusion and immutable booked snapshot selected; C09 reaffirmed. | Gross/net basis, rule selection, rates/weights, no-show treatment, refund reversals, time compensation and correction/recovery remain open. |
| Security: encrypt/tokenize payout data; never store raw payout credentials in plaintext. | Q15 encryption/tokenization requirement selected; C14 reaffirmed. | Concrete solution, provider support, keys/authority, rotation, backfill/replicas/backups and retention remain open. |

For Q07, the existing C08 requirement to preserve subscription renewal checkout
continues to apply. The grace restriction is recorded against new bookings and
new booking-payment initiation; it does not discard incoming money evidence or
stop refunds/disputes/payout reconciliation. No approval is inferred for a new
recurring mandate, paid-access grace, collection-before-completion bypass, or
post-expiry direct-receipt API. Existing bookings may finish subject to applicable
collection evidence; that receipt-permission compatibility detail remains open.

## Policy approval record U02

- **Evidence/approver:** latest explicit user task in this conversation,
  recorded in this 2026-10-19 (Asia/Calcutta) documentation revision; requesting
  user identity/title not supplied. Product direction is not legal/provider or
  security implementation proof.
- **Version and effect:** U02 supersedes U01 late-cancellation direction for
  newly governed policy only. Rollout date/environment and open-operation
  adoption are unselected. Historical bindings, amounts, prices and invoices
  never change; no executable preparation/activation is authorized.

| Explicit approved scope | Mapping | Still open |
| --- | --- | --- |
| Late is strictly less than four hours before appointment start; exactly four hours is on-time unless explicitly marked otherwise. | C04; Q03 | Equality refund Q18, explicit exception authority/notice, trusted ingress and reschedule start/policy. |
| Late customer refund is zero; full eligible captured amount enters cancellation settlement; salon receives 70% and platform 30% of distributable amount. | C04; Q01 | Requested pool is captured less approved provider costs, but fee reduction versus platform absorption is explicitly left for Q17. No unknown fee is guessed zero. |
| Provider costs remain separate; all financial calculations use integer paise or Decimal; history is immutable. | C03/C21; Q04/Q17 | Actual costs/tax, rounding residual, true-up, deficits, legal terms and transition. |
| Admin controls cancellation payout approval/timing. | C17; Q05/Q13/Q20 | Cancellation hold origin/duration Q19, roles/stages/limits Q20 and verified transfer evidence. No fabricated completion or bypass of common checks. |
| Owner must not see platform percentage or internal allocation formula; may see eligible amount, status, payout date and admin message. | C18; Q21 | Exact allowlist, scheduled/actual date semantics, sanitized message and report/export/replay filtering. |
| Admin capabilities: pending cancellation payout list, salon payout history, daily/weekly/monthly sales, online/cash totals, completed/cancelled/no-show totals, subscription revenue, payout status/audit history, custom subscription offers. | C19; Q13/Q20 | Scoped authority and metric/timezone/recognition/filter definitions; capabilities are not implemented endpoints. |
| Default plan unchanged; salon offer keeps original/discounted price, effective dates, admin actor/reason; old invoices/subscriptions retain original price; no retroactive repricing. | C20; Q09/Q22 | Offer duration/expiration, overlap/revocation, quote/order binding, tax/accounting and legacy mapping. |
| Owner sees only final offer payable price, not internal platform margin. | C20; Q09/Q21/Q22 | Exact owner projection must exclude internal original/discount/margin and admin evidence through every response surface. |

U01 selections for completed-service costs/zero commission, 48-hour completion
hold, uncapped two-calendar-month trial, restricted seven-day grace, immutable
staff snapshots/cancellation exclusion and payout-data encryption remain in force
as business scopes. Q19 asks cancellation hold and whether a prospective ordinary
hold change is wanted; it does not silently revoke the 48-hour ordinary-service
selection. A cancellation is not completed service. Legal wording and lawful
retention remain Q23/Q24, not approved by product instruction.

## Policy approval record U03

- **Evidence/approver:** latest explicit user instruction, recorded 2026-10-19
  (Asia/Calcutta); requesting user identity/title not supplied. Documentation-only
  business approval, not provider evidence or legal/implementation sign-off.
- **Precedence:** U03 supplies the current new customer-cancellation bands and
  no-show process. Every band's recipient is explicitly unresolved, including
  below-four-hour retained funds. Do not inherit U02 70/30; retain earlier records
  only for history/already-bound policy. No policy rollout/effective date or
  legacy/open-order adoption is selected; historical rules never change.

| Explicit approved scope | Mapping | Remaining approval |
| --- | --- | --- |
| Exactly 48 hours or more: flat cancellation-fee band. | C04; Q01/Q25 | Exact flat amount, caps/base and refund accounting; no default zero fee. |
| 12 to less than 48 hours: 5% penalty; exactly 12 hours included. | C04; Q01/Q03 | Percentage base, rounding/caps and actual refund balance Q25. |
| 4 to less than 12 hours: 35% penalty; exactly 4 hours included. | C04; Q01/Q03/Q18 | Base, refund balance and provider fees; no separate full-refund equality rule. |
| Less than 4 hours before start: zero refund. | C04; Q01 | Every recipient Q26, dispute hold Q19 and provider fees Q17 unresolved. **Later selected:** recipients and fee order by U06, hold by U07; dispute scope and release remain open. |
| Appointment start passes; ten-minute grace must elapse; owner/staff confirmation required. | C22; Q02 | Scoped authority, race handling and correction/appeal design; no automatic no-show or silent cancellation. |
| Record confirming actor, timestamp and reason; notify customer. | C22; Q02/Q24 | Sanitized/classified reason, notification retries/availability and retention review. |

No-show is an attendance fact, not proof of completed service, refund decision,
penalty or payout eligibility. No-show financial policy remains unresolved.
The explicit open list is exact flat-fee amount, recipient of each cancellation
penalty, dispute-hold duration and provider-fee treatment. No base, numeric fee,
recipient or release clock is invented. Existing U01 ordinary completed-service
48-hour record is preserved historically; it does not select cancellation or
no-show dispute timing. Only four requested Markdown files change in this task.

## Policy approval record U04

- **Evidence/approver:** explicit user instruction in this conversation recorded
  2026-10-19 (Asia/Calcutta); requesting user identity/title not supplied.
  Approved release invariant is business direction, not runtime proof.
- **Selected scope:** valid cancellation commit sets booking status cancelled;
  that cancelled booking immediately ceases to block slot availability, allowing
  the next eligible customer to book. Redis slot/cache invalidation occurs after
  database commit; refund delivery is a separate asynchronous workflow.
  PostgreSQL stays final authority, excludes cancelled bookings from blocking
  occupancy, revalidates availability inside booking and retains unique/exclusion
  constraints to prevent duplicate overlapping booking races (C23).
- **Conditions preserved:** other active bookings, independent closures,
  salon/staff/service/access/notice/resource constraints and valid new holds
  still apply. Immediate release requires fresh authoritative post-commit reads;
  a previously rendered client/old transaction snapshot is not instant truth.
- **Design extent:** proposed state/actor matrix, lock/race/replay/audit/
  notification contract and durable cache recovery are documented in
  [specification section 4.4](../../verification/payment-subscription-booking-spec.md#44-u04-immediate-slot-release-after-committed-cancellation)
  and [G09](09-slot-hold-concurrency-support.md#u04-committed-cancellation-and-cache-recovery).
  Q27/Q28/RP07/RC06 retain review of concrete authority, storage, ranks,
  retry/escalation, reader rollout and enforcement. User approval of immediate
  release does not silently grant a checked-in cancellation actor or choose
  exact Redis/outbox implementation, numeric retry limits or new schema.
- **No financial change:** U03 bands and unresolved flat fee, beneficiary, fees
  and dispute hold remain unchanged. An invalid/unapproved cancellation cannot
  bypass precommit policy/consent checks. Once a valid cancellation commits,
  refund failure, cache/message outage or unknown settlement cannot reoccupy it.
- **No execution:** only specification, register, cancellation, G09 and existing
  G08 closure/reschedule availability design are updated. No standalone
  availability design was found; none is created. No code, SQL, migrations,
  database/provider/Redis access, deployment, commit or push authorized.

## Policy review record U05

- **Evidence/approver:** latest explicit user review instruction recorded
  2026-10-19 (Asia/Calcutta), requesting user identity/title not supplied.
  Selected instructions below are design requirements, not runtime proof,
  permission grants, provider evidence or approval of monetary amounts.
- **Checked-in scope selected:** customer cannot cancel after check-in;
  authorized salon owner/scoped admin cancellation requires reason and atomic
  actor/time/state/policy audit. No new staff cancellation grant. One canonical
  cancellation source/revision protects against different-key duplicate actions.
- **Money review disposition:** checked-in operator cause does not inherit
  pre-start customer penalties or historical 70/30. Known approved refunds are
  capture-capped/reserved and asynchronous; unknown remedy creates one durable
  financial-review obligation and restricts affected retained funds from new
  payout. No capture means no fictitious refund; direct salon receipts are not
  platform funds. Preserve confirmed/unknown transfer evidence and reservations;
  do not guess bank-debit recovery. Exact remedies/beneficiaries/fees/holds still
  require Q29 and prior financial/legal approvals.
- **Redis scope selected:** database cancellation commits independently of Redis
  with durable database outbox invalidation intent; required outbox persistence
  failure rolls back the database transaction, while Redis failure cannot do so.
  Fresh primary PostgreSQL availability and SQL-only booking fallback replace
  the earlier unselected outage branch. Stale busy/free cache cannot block/create
  booking; no fresh PostgreSQL means truthful retryable failure, never cached
  acceptance. Healthy mandatory-hold and actor-limit rules remain Q12.
- **Resolved recovery contract:** stable job/source identity, independent worker
  leases/fencing, bounded jittered retries, retained attempt history, durable
  dead-letter alerting and targeted audited repair. Dead-letter is unresolved
  cleanup, not success or restored occupancy. Numeric retry/lease/alert budgets,
  exact storage and repair principal remain Q28/Q30 review.
- **Race requirements:** shared ordered database gates/rows, fresh state/revision
  revalidation and source uniqueness; Redis acquisition is outside SQL row locks
  with subsequent primary validation and safe compare-release. Payment facts
  persist once on the original cancelled booking without reopening it or rebinding
  capture to replacement booking. At most one conflicting terminal winner/active
  overlapping commit; no exactly-once network or guaranteed-winner claim.
- **Scope boundary:** review updates only the same five Markdown files. All
  original financial/legal/history/privilege gates remain; no code, SQL, migrations,
  database/Cashfree/Redis access, deployment, commit or push occurs. Proposed
  storage and operational specifics remain unimplemented and require review.

## Policy approval record U06

- **Evidence/approver:** explicit user instructions in this conversation, recorded
  2026-10-19 (Asia/Calcutta), answering [PHASE1_DECISION_SHEET.md](PHASE1_DECISION_SHEET.md).
  Requesting user identity/title not supplied. Product and technical-design direction
  only; not legal, accounting, provider or security sign-off, and not runtime proof.
- **Version and effect:** U06 supplies the penalty base, recipients and fee order for the
  U03 bands and no-show, and the owner-cancellation and reschedule rules below. It
  supersedes the "every recipient unresolved" statements in U03 only for the scopes
  listed here. Rollout/effective date and open-operation adoption are unselected;
  historical bindings, amounts, prices and invoices never change. No executable
  preparation or activation is authorized.

| Explicit approved scope | Mapping | Still open |
| --- | --- | --- |
| A1: owner cancellation needs no advance admin approval; reason and customer notification required; admin reviews afterwards. TA02's owner-to-admin gate is not adopted. | C24; Q27; TA02 rejected | Exact owner/admin scopes, review queue ownership and consent enforcement (Q20/Q27). |
| A2: customer may reschedule the same booking at most two times; the count never resets. Only committed reschedules count; a failed reschedule does not. | New rule C27; Q11 | Whether the limit applies across all services, admin-initiated changes, and legacy open bookings. |
| A3: new slot is secured before the old slot is released; a failed reschedule leaves the original booking unchanged; every change audited. | C27; G08/G09 | Lock ranks and exact atomic implementation (RP07). |
| A2b: cancellation eligibility after a reschedule uses the new appointment start time. | C27; Q03 | Receipt-time ingress and legacy bookings (Q03). |
| A4: owner/admin cancellation before check-in gives the customer a full refund, started asynchronously; the platform bears non-recoverable provider fees. | C24/C28; Q29 | Fee recovery from the salon is not authorized; refund timing target; provider evidence (P01/P05). |
| Q25 base: the percentage penalty base is the captured amount before provider fees. The flat fee stays configurable with no default. | C28; Q25 | **Exact flat fee in INR remains open.** Caps and partial/unpaid captures. |
| Q26: retained pool is split 70% salon / 30% platform for all cancellation bands (5%, 35%, under-4-hour zero refund, and the flat-fee band once its amount is set). Integer paise; platform share rounded half-up; residual paise go to the salon so the two shares equal the pool exactly. | C28; Q26 | None for the split mechanics. |
| Q17 / accounting: `customer_refund = captured_amount - cancellation_penalty`; `retained_pool = cancellation_penalty - nonrefundable_provider_costs`. Provider costs never reduce the customer's promised refund. If costs exceed the pool, the salon payout is zero, the platform absorbs the shortfall and the customer refund is unchanged. | C28; Q17 | Tax components, reserve/true-up for unknown fees (an unknown fee keeps payout pending, never treated as zero). |
| Q19 (hold start superseded by U07): payout stays blocked during a dispute or provider-fee uncertainty. The first U06 wording, 48 hours after cancellation and 48 hours after start plus grace, is replaced by the U07 formulas. | C05/C28; Q19 | Dispute scope, release and later-dispute handling; admin cannot shorten the hold. |
| TA07: a single super-admin with `aal2` may perform emergency repair; it requires a reason, an approval record and a complete audit trail; no two-person approval. | TA07; Q20/Q30 | Exact permitted repair operations and approval-record format. |
| Q02: a confirmed no-show follows the under-4-hour treatment: customer refund zero, provider costs deducted, remainder split 70/30. | C22/C28; Q02 | Correction/appeal of a wrongly confirmed no-show; owner-visible projection. |
| TA03: five retries after the first dispatch with delays 1m/5m/30m/2h/12h (six dispatches in total). | TA03; Q30 | Jitter, age budget and timeout classification. |
| TA04: five-minute fenced lease. | TA04; Q30 | Renewal/heartbeat and clock rules. |
| TA05: dead-letter after a permanent error or exhausted retries; audited requeue by original identity. | TA05; Q30 | Error classification and requeue bound. |
| TA08: 90-day retention for resolved operational outbox rows, counted from resolution. | TA08; Q16/Q24 | Unresolved-job and legal-hold exceptions; does not set audit retention. |
| TA10: Google Cloud KMS and Secret Manager are the key-management design. | TA10; Q15 | Design only. Creating any resource, region choice, access grants and rotation need separate approval. |

The following stay **unresolved**: exact flat cancellation fee in INR (Q25; the value
stays configurable with no default); TA06 admin email address and Sentry project; TA09
financial audit retention period (needs accountant/legal); the monetary remedy for
cancellation after check-in (Q29); and all Cashfree/provider evidence (P01-P06).

Because U06 selects 70/30 for the cancellation bands, 70/30 applies to newly governed
policy, but only under U06's order (retained pool is the penalty less nonrefundable
provider costs, then split) and not by inheritance from U02.

**U06 settlement arithmetic (integer paise).** For a cancellation with captured amount
`C` and penalty `P` (`0 <= P <= C`): `customer_refund = C - P`;
`retained_pool = P - nonrefundable_provider_costs`. Provider costs never reduce the
customer refund. If `retained_pool <= 0`: salon share is 0, the platform absorbs the
shortfall, and the customer refund is unchanged. If `retained_pool > 0`:
`platform_share = round_half_up(retained_pool * 30 / 100)` and
`salon_share = retained_pool - platform_share`, so the shares equal the pool exactly and
any residual paise goes to the salon. For under-4-hour cancellation and confirmed
no-show, `P = C` and `customer_refund = 0`.

## Policy approval record U07

- **Evidence/approver:** explicit owner approval message, recorded 2026-10-19
  (Asia/Calcutta): "I explicitly approve U07 hold formulas" for the customer-cancellation
  formula and the confirmed no-show formula below, plus "no salon payout unless
  separately approved" for owner/admin cancellation and "Checked-in monetary remedy
  remains Approval required". It follows the earlier correction-task message that
  listed the same formulas conditionally ("only if approved"). Requesting user
  identity/title not supplied.
  Product direction only; not legal, accounting or provider sign-off, and not runtime
  proof. It refines the Q19 hold start recorded in U06 and supersedes that wording.
- **Why:** a hold counted from cancellation time alone can end before the appointment,
  and a no-show hold counted from appointment start can already have elapsed when the
  owner confirms the no-show days later, leaving the customer no dispute window.

| Explicit approved scope | Mapping | Still open |
| --- | --- | --- |
| Customer cancellation: `hold_until = max(cancellation_time + 48 hours, appointment_start)`. After a reschedule, `appointment_start` is the current governing start (U06 A2b). | C05/C28; Q19 | Time source (database time is the proposed source) and display rules for the owner. |
| Confirmed no-show: `hold_until = max(no_show_confirmation_time, appointment_start + 10 minutes) + 48 hours`. | C22/C28; Q19; Q02 | Correction or appeal of a wrongly confirmed no-show. |
| Owner/admin cancellation: no salon payout unless separately approved. | C28; Q29 | Any salon compensation needs its own approval record. |
| Checked-in cancellation monetary remedy remains pending review; affected funds stay restricted. | C24; Q29; TA01 | Entire remedy (Q29). |
| Payout remains blocked during a dispute or provider-fee uncertainty (unchanged from U06). | C05/C06 | Dispute scope, release and later disputes. |

Admin approval or scheduling cannot shorten a hold (Q05/Q19). The ordinary
completed-service hold (48 elapsed hours after completion, U01) is unchanged.

U06 and U07 do not close these, which stay **Approval required**: the exact flat
cancellation fee in INR (Q25), TA06 alert targets, TA09 financial audit retention,
the checked-in cancellation monetary remedy (Q29) and dispute scope and release (Q19).
All Cashfree and provider behaviour (fees, KYC, settlement, schedules, webhooks) remains
**unverified**: mock-provider results prove local logic only, and no account evidence
exists.

## 1. Business decisions Q01-Q30

### Q01 - Approved cancellation bands; monetary finalization open

- **Decision ID:** Q01
- **Exact question:** **Partially approved U03**: Record flat-fee band at 48 hours or more, 5% at 12 to less than 48, 35% at 4 to less than 12, and zero refund below 4 hours. Resolve flat amount/base/caps under Q25, penalty recipients Q26, provider fees Q17, hold Q19 and legacy adoption without rewriting historic policy.
- **Current proposed default / approved scope:** U03: at least 48 hours flat-fee band; 12 to less than 48 hours 5%; 4 to less than 12 hours 35%; below 4 hours zero refund. U02 70/30 does not supply U03 beneficiaries. **Updated by U06:** recipients are 70% salon / 30% platform of the retained pool after actual provider costs.
- **Alternatives and consequence of each choice:** Selected bands/rates are fixed business scopes. Flat amount and percentage base/caps choices affect refund balance; beneficiary choices change entitlement; provider-fee choice changes funding. Defer incomplete monetary policy: no guessed quote/finalization or payout. Preserve old bound terms.
- **Recommendation:** Retain bands and exact boundaries; resolve Q25 amount/base, Q26 recipients, Q17 provider costs and Q19 hold before finalization.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G02, G03, G04, G08.
- **Cashfree account required:** No for band approval; provider evidence separately P01/P05.
- **Approval status:** Partially approved U03: bands/rates and zero late refund selected; flat amount, recipients, hold, fees, monetary mechanics and rollout unresolved.

### Q02 - Confirmed no-show process and remaining financial scope

- **Decision ID:** Q02
- **Exact question:** **Partially approved U03**: No-show requires appointment start passed plus ten-minute grace, explicit owner/staff confirmation, actor/timestamp/reason and customer notification; never silently cancel. Define scoped confirmer authorization, appeal/correction and notification retry handling, no-show financial treatment, duplicate/excess refund and separate salon-caused refund under L01. Do not infer a no-show penalty from cancellation bands.
- **Current proposed default / approved scope:** U03 requires start passed, full ten-minute grace, authorized owner/staff confirmation, recorded actor/time/reason and customer notification; never silently cancel. No-show money policy: U06 selects under-4-hour treatment (refund zero, provider costs deducted, 70/30 split); U07 selects the hold.
- **Alternatives and consequence of each choice:** Explicit confirmation after grace records attendance with audit/notification. Mere time expiry cannot mark no-show/cancel. Scoped owner/staff authority and correction/appeal options change control/latency; notification retry must not repeat attendance/financial action. No-show penalty/refund/allocation choices remain unset, not inherited from cancellation.
- **Recommendation:** Bind start/grace and actual confirmer, sanitize reason and use durable notification intent/retry in later design. Revalidate arrivals/check-ins, preserve audit and explicitly settle no-show finances separately.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G01, G03, G04, G08.
- **Cashfree account required:** No for attendance process; any later provider financial policy separately P01/P05.
- **Approval status:** Partially approved U03: grace/confirmation/audit/notify/no-silent-cancel selected; scoped enforcement, correction/notification behavior, no-show finances and salon-caused refunds remain open.
- **U06 update:** no-show money follows the under-4-hour treatment (refund zero, provider costs deducted, remainder 70% salon / 30% platform). Correction/appeal and owner projection remain open.

### Q03 - Exact 48/12/4-hour boundaries

- **Decision ID:** Q03
- **Exact question:** **Partially approved U03**: Exactly 48 hours is flat-fee, exactly 12 hours is 5%, exactly 4 hours is 35%, and strictly below 4 hours is zero refund. Approve trusted receipt-time ingress, rescheduled governing start/policy, effective rollout and exception governance; no exception is selected here.
- **Current proposed default / approved scope:** U03 puts exactly 48 hours in flat-fee band, exactly 12 in 5%, exactly 4 in 35%; below four hours zero refund.
- **Alternatives and consequence of each choice:** Approved boundaries supersede generic U02 equality uncertainty for new policy. Original versus rescheduled governing start changes bracket and needs explicit snapshot/consent. Later admin approval time cannot silently move receipt bracket. Deferral of ingress/legacy details blocks activation; no exception assumed.
- **Recommendation:** Keep exact boundaries; review trusted receipt ingress/reschedule/start/legacy version before implementation. Separate rate selection from actual refundable cash calculation Q25/Q17.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G03, G08.
- **Cashfree account required:** No.
- **Approval status:** Partially approved U03: band boundaries selected; ingress, reschedule, legacy and any future exception governance remain open.

### Q04 - Fee bearers, reserves and deficits

- **Decision ID:** Q04
- **Exact question:** **Partially approved U01/U02**: Actual provider charges reduce completed-service salon payout. Approve each other cause/component bearer, taxes, reserve/true-up, deficit/recovery and Q17 cancellation pool choice, with P01 and L02/L03.
- **Current proposed default / approved scope:** U01 selects actual provider charges reducing salon payout for completed online services, with service-total customer payment and zero platform service commission. Prior D04 salon-caused cancellation fee recommendation remains unapproved.
- **Alternatives and consequence of each choice:** Approve complete D04 cause/component matrix: determines salon net/platform expense. Other lawful platform/salon bearing: shifts net and receivables. Customer refund deductions require explicit terms and cannot add checkout surcharge. Reserve unknown costs: delays spendable net; separately funded true-up: creates explicit funding exposure. Defer: no guaranteed net/dependent payout.
- **Recommendation:** Use the selected completed-service bearer for the target policy; resolve remaining cause/component, reserve and recovery matrix without inventing actual fees.
- **Decision owner:** finance (proposed; named approver unassigned).
- **Blocking design groups:** G02, G03, G04, G06.
- **Cashfree account required:** Conditional: local policy needs no account; P01 pricing/debit evidence does.
- **Selected approved scope:** U01: salon bears actual provider charges for completed online service through a reduced salon payout; no extra customer checkout charge.
- **U02 update:** Cancellation fee-reduced pool is requested, but Q17 explicitly retains platform absorption as an unresolved alternative. 70/30 supersedes prior new-policy cancellation allocations; completed-service bearer remains U01.
- **Still unresolved:** Every cancellation/refund cause, tax/component attribution and evidence, unknown-fee reserve, deterministic allocation/true-up, deficit/recovery and historical treatment; P01/L02/L03 remain unapproved.
- **U03 precedence:** All cancellation recipients, dispute-hold duration and provider-fee treatment are explicitly unresolved. U02 70/30/net-pool and U01 completion clock cannot select a new cancellation/no-show entitlement or release time. **Updated:** U06 selected recipients, fee order and the 70/30 split; U07 selected the cancellation and no-show hold formulas. Neither inherits U02 or U01.
- **Approval status:** Partially approved under U01 (requesting user, 2026-10-18); remaining subdecisions/evidence require approval; no rollout effective date or legacy transition selected.

### Q05 - Completion hold and admin-controlled cancellation settlement

- **Decision ID:** Q05
- **Exact question:** **Partially approved U01/U02**: Retain 48 elapsed hours after service completion and no active dispute for ordinary payouts; new cancellation settlement is admin-controlled and distinct from completion. Resolve Q19 hold scope/origin/duration, Q20 authority, release/later disputes and final entitlement; never fabricate completion.
- **Current proposed default / approved scope:** U01 ordinary service hold remains 48 elapsed hours after completion, no active dispute. U02 selects separate cancellation settlement under admin approval/timing. U07 selects the cancellation and no-show hold formulas.
- **Alternatives and consequence of each choice:** Completed-service path retains U01 clock. Cancellation path requires its own Q19 origin/duration and final entitlement, never fake completion. Dispute freeze/release/later recovery scope determines eligible funds. No complete cancellation policy: initiation remains blocked even if admin approves timing.
- **Recommendation:** Resolve Q19/Q20 and account P02 feasibility; preserve KYC/funding/unique reservations/finality and identical manual/automatic checks. No numeric cancellation hold inferred.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G03, G04, G05.
- **Cashfree account required:** Conditional: selected hold must be proven enforceable upstream under P02.
- **U03 precedence:** All cancellation recipients, dispute-hold duration and provider-fee treatment are explicitly unresolved. U02 70/30/net-pool and U01 completion clock cannot select a new cancellation/no-show entitlement or release time. **Updated:** U06 selected recipients, fee order and the 70/30 split; U07 selected the cancellation and no-show hold formulas. Neither inherits U02 or U01.
- **Approval status:** Partially approved U01/U02: ordinary hold and separate admin-controlled cancellation path selected; hold scope, cancellation timing/authority and evidence gates remain open.

### Q06 - Trial activation, cap and calendar

- **Decision ID:** Q06
- **Exact question:** **Partially approved U01**: Two-calendar-month trial has no booking cap. Confirm activation versus approval, local calendar/month-end/exclusive boundary, and legacy-salon/cap transition without restarting trials.
- **Current proposed default / approved scope:** U01 selects two calendar months with no booking-count cap for the target trial policy. Existing legacy cap/history is not changed; D07 calendar/activation/grandfathering details remain unapproved.
- **Alternatives and consequence of each choice:** Remove cap prospectively: expands entitlement. Retain explicit cap: booking access may end before calendar duration. Approval-as-activation versus separate activation changes start event. Proposed versus another explicit calendar convention changes edge dates; neither may substitute 60 days/restart on reapproval. Prospective-only versus approved existing-salon adoption changes legacy eligibility.
- **Recommendation:** Prepare policy review around the selected uncapped calendar trial; resolve exact activation/calendar and grandfathering without silently removing legacy constraints.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G07, G09.
- **Cashfree account required:** No.
- **Selected approved scope:** U01: trial duration is two calendar months, without a booking cap; no 60-day substitution.
- **Still unresolved:** First approved activation versus approval, exact local calendar/month-end/exclusive-end convention, legacy salons/cap transition and effective rollout. Reapproval cannot restart the C07 trial.
- **Approval status:** Partially approved under U01 (requesting user, 2026-10-18); remaining subdecisions/evidence require approval; no rollout effective date or legacy transition selected.

### Q07 - Expiry, grace, receipts and late capture

- **Decision ID:** Q07
- **Exact question:** **Partially approved U01**: Seven-day renewal grace blocks new bookings/booking-payment initiation and allows existing bookings to finish; renewal checkout remains available. Approve exact day-count/start/end/trial applicability, direct receipt permission, late captures and legacy mapping.
- **Current proposed default / approved scope:** U01 selects seven-day renewal grace, no new bookings/new booking payments during grace and permission for existing bookings to finish. D09 calendar/start/trial details, D08 receipt recording and D15 late captures remain unapproved.
- **Alternatives and consequence of each choice:** D08 approval preserves receipt evidence/completion without new collection. Restrict receipts: needs alternate explicit obligation/completion path or remains blocked. Seven versus zero/other explicit renewal-only days changes display/renewal timing, not expiry booking restrictions. Trial renewal-only grace versus none changes lifecycle presentation. Apply late funds to valid work versus approved refund remedy changes fulfillment; verified movement always recorded.
- **Recommendation:** Preserve selected grace restrictions and completion permission; explicitly resolve renewal timing, direct receipts and late captures without enabling new booking orders or waiving evidence.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G07, G08, G09; G02-G04 for money consequences.
- **Cashfree account required:** Conditional: access policy local; late-capture evidence needs P05.
- **Selected approved scope:** U01: seven-day renewal grace with no new booking/payment initiation for bookings and existing service completion allowed; subscription renewal remains permitted under C08.
- **Still unresolved:** Calendar versus elapsed-day calculation, start/end/timezone, paid/trial applicability, exact receipt permission with collection-before-completion, late-capture remedy, consent and legacy transition. Seven days does not select every detail of D08/D09/D15.
- **Approval status:** Partially approved under U01 (requesting user, 2026-10-18); remaining subdecisions/evidence require approval; no rollout effective date or legacy transition selected.

### Q08 - Checkout, deposits and open orders

- **Decision ID:** Q08
- **Exact question:** **Approval required**: Confirm full online checkout for the approved service/cart total and whether any advance/deposit exception survives. May direct cash receipts be partial? Define handling of old surcharge orders, quote expiry and unpaid-booking release deadlines.
- **Current proposed default / approved scope:** U01 confirms customer service-total payment and zero extra platform commission for completed online service. No deposit/advance, partial direct-receipt, deadline or old-order decision is inferred.
- **Alternatives and consequence of each choice:** Full online payment: simpler balance binding. Deposit exception: requires partial-balance/expiry/refund rules. Partial versus full direct receipt: changes collection/API tracking, never creates platform payout funds. Versioned old-order grandfathering versus cancel/requote before new initiation changes transition; captures cannot be repriced. Unset deadlines block dependent rules.
- **Recommendation:** Use the selected service-total target; resolve checkout exceptions/deadlines/legacy orders under Q07/L01/L02 without changing historical receipts.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G02, G03, G07, G08, G09.
- **Cashfree account required:** Conditional: provider order/capture/refund behavior needs P05.
- **Selected approved scope:** U01: customer pays the service total; completed-service platform commission is INR 0 and actual provider charges reduce salon payout.
- **Still unresolved:** Whether advance/deposit exceptions survive, partial direct receipts, quote expiry/unpaid release deadlines, old surcharge/open-order and capture handling; this confirmation does not approve all checkout transition details.
- **Approval status:** Partially approved under U01 (requesting user, 2026-10-18); remaining subdecisions/evidence require approval; no rollout effective date or legacy transition selected.

### Q09 - Subscription terms and salon-specific offers

- **Decision ID:** Q09
- **Exact question:** **Approval required** for tax inclusion, benefits, subscription cancellation/paid-through/refunds and D12 manual renewal. U02 approves salon-specific offers with immutable original/discounted price, effective dates, actor/reason and final-price-only owner projection; resolve Q22 expiration/binding and Q20 authority. No recurring mandate is authorized.
- **Current proposed default / approved scope:** U02 approves unchanged default plan plus salon-scoped original/discounted price, effective dates, admin actor/reason and final-price-only owner projection. D12 manual renewal remains a proposal; tax/benefits/cancellation terms unset.
- **Alternatives and consequence of each choice:** Immutable salon offer version: supports prospective discount without repricing catalog/history. Expired/revoked offer and open orders: Q22 must choose honoring bound quote versus explicit requote before collection; verified late captures keep original amount. Manual versus later consent-based recurring mode changes purchase obligations and provider needs; no mandate approved.
- **Recommendation:** Review offers under Q22/Q20/L02/Q24. Preserve old invoices/subscriptions and show only final payable owner price, never internal margin or discount breakdown.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G07; G01 audit, G02 accounting.
- **Cashfree account required:** Conditional: local offer design no account; later purchase/capture evidence needs P05.
- **Approval status:** Partially approved U02 offer capability/immutability/visibility; duration/binding, tax/terms/authority/retention and manual-renewal selection remain open.

### Q10 - Staff basis, allocation and recovery

- **Decision ID:** Q10
- **Exact question:** **Partially approved U01**: No cancelled-booking service commission and immutable booked snapshot source. Approve gross/net basis, rate/rule selection, earning event, precedence/weights, no-show, reversals, separately typed time compensation and authorized recovery under L04.
- **Current proposed default / approved scope:** U01 selects no commission for cancelled bookings and immutable booking-snapshot basis. Remaining D10 gross basis, rule-selection, no-show and proportional reversal proposals are not approved as a bundle.
- **Alternatives and consequence of each choice:** Gross versus approved net basis changes pool/fee exposure. Booking-time versus approved completion-time rule changes binding, never old snapshots. Explicit scope precedence/weights/residual determines one shared pool. Proportional versus other lawful reversal changes recovery. Exclude time compensation versus separately typed/funded obligation changes category. Approved recovery after disbursement creates a process/receivable, never automatic bank debit. Defer: no new earning rule.
- **Recommendation:** Apply selected cancellation exclusion and snapshot source to the target design; obtain explicit earning/formula/allocation/recovery policy before any commission rule executes.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G06.
- **Cashfree account required:** No; provider-fee-dependent basis separately needs P01.
- **Selected approved scope:** U01: cancelled bookings earn no service commission; commission derives from immutable booked snapshots rather than current catalog values.
- **Still unresolved:** Gross/net calculation, rate/rule selection time and earning event, precedence/fixed scope, multiple-staff weights/residuals, no-shows, refund reversals, separate time compensation, internal fee bearing and authorized correction/recovery under L04.
- **Approval status:** Partially approved under U01 (requesting user, 2026-10-18); remaining subdecisions/evidence require approval; no rollout effective date or legacy transition selected.

### Q11 - Availability, closure and reschedule policy

- **Decision ID:** Q11
- **Exact question:** **Approval required**: Specify buffer/minimum notice/same-day cutoff values and scope, overnight/recurring closures, and post-expiry reschedule/repricing policy. No unstated numeric defaults.
- **Current proposed default:** No numeric buffer/notice/cutoff, preview/request expiry or recurring expansion default. Resource scope, overnight rules, retired services, consent and post-expiry repricing remain open.
- **Alternatives and consequence of each choice:** Explicit zero versus positive buffer/notice changes eligible intervals; neither is implied. Staff-only versus extra resources changes exclusion representation/conflict scans. Interval-only versus bounded recurring/overnight closure changes scope. Preserve price/services versus separately approved adjustment changes consent/funding; unresolved retired services block reassignment. Permit versus restrict expired reschedule changes access while original work remains visible.
- **Recommendation:** Set every value/scope/consent boundary; preserve original slot until atomic approval. Price/service changes need a separate adjustment workflow, not snapshot edits.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G03 where terms change, G08, G09.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### Q12 - Selected Redis-outage fallback; healthy hold policy open

- **Decision ID:** Q12
- **Exact question:** **Partially approved U05**: PostgreSQL availability and SQL-only booking fallback are selected when Redis is unavailable; never require unavailable Redis to commit cancellation or fabricate hold success. Are healthy holds mandatory, and what actor/churn/renewal limits apply? Review operational outage recovery under Q28/Q30.
- **Current proposed default / approved scope:** U05 selects fresh primary availability and eligible SQL-only booking attempts on unavailable Redis. No fabricated hold or stale-cache gate. Healthy mandatory/optional proof, actor/churn/renewal limits remain unset.
- **Alternatives and consequence of each choice:** Unavailable Redis uses selected SQL fallback with normal DB guards. Healthy mandatory versus optional hold changes admission/fairness and requires explicit choice. Numeric limits change abuse/load; never infer unlimited/rolling renewal. PostgreSQL unavailable/freshness unknown: retryable unavailability, never cache-only booking.
- **Recommendation:** Retain selected fallback and truthful coordination status; specify healthy policy/limits plus Q28/Q30 outbox/recovery. Do not keep outage booking admission unresolved.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G08, G09.
- **Cashfree account required:** No.
- **Approval status:** Partially approved U05: outage SQL fallback selected; healthy policy and numeric limits remain open.

### Q13 - Admin capabilities, finance authority and independent approval

- **Decision ID:** Q13
- **Exact question:** **Partially approved U02**: Admin controls cancellation payout approval/timing and custom offers, but concrete admin roles/stages/scopes/limits and D11 model remain open under Q20. Define independent transfer evidence, automation, audit durability and dispute/reversal/correction authority; common manual/automatic checks remain mandatory.
- **Current proposed default / approved scope:** U02 selects admin cancellation approval/timing, reporting/history and custom offers. No concrete role/grant, stage/limit, independent review, D11 automation model or audit-failure mechanism selected.
- **Alternatives and consequence of each choice:** Named scoped human versus bounded delegated system approval changes workload and automation power. One versus independent stages changes fraud exposure/latency. Approved manual evidence versus no manual method changes execution options; neither bypasses common eligibility. Unknown grantor/stage or unavailable durable audit: commands fail closed.
- **Recommendation:** Resolve Q20 permission/limit/stage and reporting/export scopes, admin aal2, independent evidence, no self-expansion and durable audit. Reporting/admin UI visibility is not authority to transfer.
- **Decision owner:** security (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** Conditional: authority local; transfer identity/evidence needs P05/P06.
- **Approval status:** Partially approved U02 capability scope only; Q20/Q13 authority and D11 approval model remain approval required.

### Q14 - Verified product and funding choice

- **Decision ID:** Q14
- **Exact question:** **Approval required** plus Cashfree confirmation P01-P06: Select verified products/account capabilities/schedules and demonstrate delayed settlement/manual funding without double payout, informed by L03. Keep activation blocked until sandbox evidence exists.
- **Current proposed default:** No account product/capability/schedule or delayed-funding path is verified or selected; mock ports remain separate.
- **Alternatives and consequence of each choice:** Verified delayed split settlement: may satisfy holds if P02 proves it. Separate payout/manual funding: needs lawful custody and cross-method dedup under P06/L03. Early automatic settlement violating C05: cannot activate. Defer: no real integration enablement.
- **Recommendation:** Choose only after account-specific P01-P06 and L03 evidence proves fund flow and synthetic sandbox behavior; bind scope/environment/provenance.
- **Decision owner:** finance (proposed; named approver unassigned).
- **Blocking design groups:** G02, G04, G05; G07 selected purchase capability.
- **Cashfree account required:** Yes: P01-P06 account evidence, not mock results.
- **Approval status:** Approval required; no selection/sign-off recorded.

### Q15 - Encryption/tokenization and plaintext transition

- **Decision ID:** Q15
- **Exact question:** **Partially approved U01**: Encrypt/tokenize payout data; no plaintext raw credentials. Select concrete solution, decryptor/rotation authority and reviewed plaintext/replica/backup cleanup under P04/L05.
- **Current proposed default / approved scope:** U01 approves encryption/tokenization of payout data and prohibition of plaintext raw payout credentials. Envelope encryption versus adequate tokenization, exact solution/authorities and transition remain unselected.
- **Alternatives and consequence of each choice:** Envelope encryption: scoped local decryption with key custody/rotation burden. Adequate tokenization: reduces local secret storage but depends on provider and retained evidence access. Defer: dependent enablement blocked. Plaintext storage/rollback is outside approved options.
- **Recommendation:** Choose and review the concrete solution under Q15/P04/L05; keep payout enablement blocked until existing plaintext exposure and operational key handling are resolved.
- **Decision owner:** security (proposed; named approver unassigned).
- **Blocking design groups:** G01, G02, G04, G05; every group with sensitive/digest fields.
- **Cashfree account required:** Conditional: encryption design local; provider tokenization/destination claims need P04.
- **Selected approved scope:** U01: payout data must be encrypted/tokenized; raw payout credentials must never be stored in plaintext. This is a requirement, not approval of a specific cipher, key service or provider token.
- **Still unresolved:** Concrete encryption/tokenization solution and P04 support, decryption/rotation authority, destination change/cooling-off, reviewed plaintext backfill/replica/backup cleanup, dedup continuity and L05 retention.
- **Technical recommendation update:** TP01/TA10 proposes separate managed KMS wrapping keys and managed secret-store credentials with ciphertext/version references in database, or adequate provider tokenization. Concrete storage/region/access/rotation remain approval required.
- **Approval status:** Partially approved under U01 (requesting user, 2026-10-18); remaining subdecisions/evidence require approval; no rollout effective date or legacy transition selected.

### Q16 - Retention, erasure and continuing obligations

- **Decision ID:** Q16
- **Exact question:** **Approval required**: Approve retention/erasure, legal holds, provider references/keys, unresolved obligation handoff and post-payout funding/recovery. Include U02 cancellation/report/offer evidence under Q24/L05; no statutory period is invented.
- **Current proposed default:** All 43 field classifications and all new-field treatment await approval. No durations, legal basis/holds, key-destruction, handoff or post-payout funding/recovery selected.
- **Alternatives and consequence of each choice:** Finite lawful restricted retention: preserves necessary evidence with review/access/destruction duties. Demonstrated anonymization/deletion: reduces identity retention but requires dedup/obligation handoff. Validated legal hold: delays destruction only within approved authority/review. Defer: dependent new flows blocked; unknown obligations cannot be forgotten/retried as new.
- **Recommendation:** Resolve L05-F01 through L05-F43 and all new fields with L01-L05; include backups/caches/logs, third-party content, immutable facts and refund/fee/chargeback funding/recovery.
- **Decision owner:** legal (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** Conditional: provider necessity/wind-down/reference handling needs P04-P06.
- **Technical recommendation update:** TP01/TA08 proposes only 90-day resolved operational outbox retention; TA09 requires a separate lawful finite financial-audit schedule and supplies no numeric period. All retention/key/exception/erasure approval gates remain open.
- **Approval status:** Approval required; no selection/sign-off recorded.

### Q17 - Provider fees across cancellation bands

- **Decision ID:** Q17
- **Exact question:** **Approval required**: How are provider fees treated in each U03 cancellation band and any no-show financial policy: reduce retained funds, reduce a beneficiary share, or platform-absorbed? Define actual cost/tax evidence, reserve, true-up and deficit funding; Q26 beneficiaries are unresolved and historical U02 70/30 cannot select them.
- **Current proposed default / approved scope:** Provider-fee treatment was unresolved under U03. **Selected by U06:** actual provider costs are deducted from the penalty before the 70/30 split; unknown fees keep payout pending; platform absorbs any shortfall.
- **Alternatives and consequence of each choice:** Reduce retained funds: changes recipient pool after beneficiary decision. Deduct from approved beneficiary: changes its net and requires funding authority. Platform absorbs: creates expense/possible deficit. Unknown fees block guaranteed net; no implicit zero or double deduction. Defer: no dependent payout.
- **Recommendation:** Decide per-band/cause fee/tax evidence, bearer, reserve/true-up and deficit with Q25/Q26/P01/L02/L03 before applying any split.
- **Decision owner:** finance (proposed; named approver unassigned).
- **Blocking design groups:** G02, G03, G04.
- **Cashfree account required:** Conditional: local policy no account; P01 actual costs require separate account evidence.
- **Approval status:** Partially approved U06 for cancellation bands and no-show; other causes and deficit/true-up remain open.
- **U06 update:** actual provider costs are deducted before the 70/30 split of the retained amount. Owner/admin cancellation before check-in: platform bears non-recoverable provider fees. An unknown fee keeps payout pending, never zero. If provider costs exceed the retained pool the platform absorbs the shortfall and the customer refund is unchanged. Tax components and reserve/true-up remain open.

### Q18 - Exactly-four-hour penalty and refund mechanics

- **Decision ID:** Q18
- **Exact question:** **Partially approved U03**: Exactly four hours is in the 35% penalty band, not the below-four-hour zero-refund band. Approve the percentage base, rounding/caps and actual refundable balance under Q25/Q17; do not assume an extra full refund, a zero refund or a fixed net cash amount.
- **Current proposed default / approved scope:** U03 assigns exactly four hours a 35% penalty, superseding the earlier unselected full/zero-refund equality alternatives.
- **Alternatives and consequence of each choice:** 35% of an explicitly approved base yields a penalty; net refund depends captured funds, prior obligations and fees. No approval for current-price base, automatic 65% of capture or another cash amount. Incomplete base/fees: no final monetary quote. Historical equality rules remain bound to original policy.
- **Recommendation:** Resolve Q25 base/caps/rounding and Q17 fee treatment; preserve 35% band without imposing the below-four-hour zero refund.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G03, G08.
- **Cashfree account required:** No for rate/base selection; provider refund feasibility separately P01/P05.
- **Approval status:** Partially approved U03: equality belongs to 35% band; exact refund calculation/fees remain open.

### Q19 - Dispute and cancellation hold duration

- **Decision ID:** Q19
- **Exact question:** **Approval required**: What dispute-hold duration and start event govern cancellation settlement? Is any prospective change requested to U01's 48-hour completed-service hold? Define dispute scope/release/later claims without rewriting historical holds.
- **Current proposed default / approved scope:** U01 completion hold 48 elapsed hours remains selected. U07 selects the customer-cancellation and confirmed no-show hold formulas (see the U07 update below); dispute scope/release and any prospective ordinary-hold change remain open.
- **Alternatives and consequence of each choice:** Preserve ordinary 48-hour clock: no policy change. Prospective alternate ordinary hold: explicit approved version only. Cancellation hold from final entitlement/decision or other explicit event: changes release latency/exposure; no choice selected. Unset cancellation hold: no new payout. Later valid disputes survive all operational deadlines.
- **Recommendation:** Define scope/start/duration/release authority and later-dispute funding. Admin scheduling cannot shorten holds; verify upstream capability P02.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G03, G04, G05.
- **Cashfree account required:** Conditional: capability evidence needs P02; selecting policy needs no account.
- **Approval status:** Partially approved U07 for customer cancellation and confirmed no-show holds; owner/admin cancellation has no salon payout unless separately approved; dispute scope/release and any prospective ordinary change remain open; historical/selected ordinary 48 hours preserved.
- **U07 update (replaces the first U06 wording):** customer cancellation `hold_until = max(cancellation_time + 48 hours, appointment_start)`; confirmed no-show `hold_until = max(no_show_confirmation_time, appointment_start + 10 minutes) + 48 hours`. Owner/admin cancellation: no salon payout unless separately approved. Payout stays blocked during a dispute or provider-fee uncertainty.

### Q20 - Admin payout/offer roles and stages

- **Decision ID:** Q20
- **Exact question:** **Approval required**: Which admin payout approval roles, permission scopes, amount limits, independent stages and automated delegation may approve and schedule cancellation payouts or custom offers? Approval/timing cannot bypass common financial checks.
- **Current proposed default / approved scope:** Admin control selected, but role identities, scopes/limits/stages/independence and offer/reports/export permissions unselected.
- **Alternatives and consequence of each choice:** Scoped human stage approval: controlled access with operator latency. Independent multi-stage/amount limits: stronger separation with overhead. Bounded automated delegation: requires same guards and current authority. No eligible authority: command disabled, never infer powers from admin label.
- **Recommendation:** Define Q13/RP01-RP04 permissions, bootstrap/revocation, aal2, independent manual evidence, automation and audit; offer admin reason does not authorize arbitrary bank transfers.
- **Decision owner:** security (proposed; named approver unassigned).
- **Blocking design groups:** G01, G04, G05, G07; reporting G02/G03/G06.
- **Cashfree account required:** No for roles; manual/provider evidence separately P05/P06.
- **Approval status:** Approval required; capability direction does not grant concrete roles or stages.

### Q21 - Owner-visible fields and confidentiality

- **Decision ID:** Q21
- **Exact question:** **Approval required**: Approve the owner-visible payout allowlist (eligible amount, status, payout date, admin message), exact scheduled/actual date semantics, message sanitization and history/export scope. Platform percentage and internal formula remain forbidden.
- **Current proposed default / approved scope:** Candidate allowlist: eligible amount, status, payout date, sanitized admin message. Platform percentage/formula forbidden; offer owner sees final payable price only, no margin.
- **Alternatives and consequence of each choice:** Approve allowlist: minimum intended projection with clear scheduled/actual dates. Narrow subset: less support visibility. Additional metadata: requires explicit review proving no formula/margin/secret leakage. Never include forbidden internal allocation in owner payload then hide in UI. Defer: no new owner projection.
- **Recommendation:** Approve explicit serializers/report/export/replay/message allowlists, salon authorization, date meanings and message sanitization. Do not promise the displayed amount prevents all inference from known service price.
- **Decision owner:** security (proposed; named approver unassigned).
- **Blocking design groups:** G01-G05 owner financial projections; G07 offers.
- **Cashfree account required:** No.
- **Approval status:** Approval required for exact fields/semantics; prohibition of internal percentage/formula/margin disclosure approved U02.

### Q22 - Offer duration, expiry and purchase binding

- **Decision ID:** Q22
- **Exact question:** **Approval required**: What offer duration, timezone and expiration boundary apply? Define overlap/precedence, revocation, existing quote/order expiry and final checkout price binding; no old invoice/subscription may be repriced.
- **Current proposed default / approved scope:** Salon scope, original/discounted prices, effective dates, actor/reason and no retroactive repricing approved; numeric duration, timezone/bounds, overlap/revocation and quote/order policy unset.
- **Alternatives and consequence of each choice:** Honor an eligible bound quote/order across expiry: preserves quoted price but needs clear price-lock lifetime. Require fresh quote before new initiation: expired offer unavailable, requires explicit owner consent to changed price. Never silently reprice captured orders/old periods. Overlap precedence/revocation choices affect who qualifies; no implicit best discount. Defer: no offer activation.
- **Recommendation:** Specify duration/end semantics, limits/precedence, plan/period eligibility and immutable offer/purchase version with Q09/L02/Q20/Q24. Late movement reconciles original amount.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G07; G01 authority/audit, G02 revenue.
- **Cashfree account required:** Conditional: expiration policy local; provider order/capture behavior needs P05.
- **Approval status:** Approval required for duration/expiration/binding; required immutable offer fields/visibility approved U02.

### Q23 - Legal zero-refund cancellation wording

- **Decision ID:** Q23
- **Exact question:** **Approval required**: What legal wording, advance notice, customer consent, dispute/statutory remedy and cause scope are required for zero-refund late cancellation? Product approval does not establish enforceability or override mandatory rights.
- **Current proposed default / approved scope:** Zero refund for new strictly-late cancellation is product-approved; no wording/notice/consent or legal enforceability established.
- **Alternatives and consequence of each choice:** Approved lawful terms plus evidenced advance consent: permits dependent rollout within lawful scope. Required statutory/dispute remedy: needs explicit obligation/funding without erasing original facts. Unapproved wording: no release; never assume zero refund overrides mandatory rights.
- **Recommendation:** Legal reviewer defines wording, customer-facing cause/boundary/fees, exceptions, acceptance evidence and dispute remedies under L01; do not expose internal owner allocation to satisfy customer notice.
- **Decision owner:** legal (proposed; named approver unassigned).
- **Blocking design groups:** G03, G04, G08; G01 consent/audit.
- **Cashfree account required:** No for legal review; remedy feasibility separately provider-dependent.
- **Approval status:** Approval required; no legal conclusion follows from product selection.

### Q24 - Retention and erasure of new financial/offer evidence

- **Decision ID:** Q24
- **Exact question:** **Approval required**: What financial retention and erasure rules cover cancellation allocation, reports, payout/audit history and offer actor/reason/price evidence? Define lawful basis, durations/holds, access, scrubbing, backup/key destruction and open-obligation handoff with Q16/L05.
- **Current proposed default / approved scope:** No durations/lawful basis/holds/key destruction approved. Existing L05-F01-F43 remain unapproved; U02 report/offer/cancellation evidence needs new explicit classification.
- **Alternatives and consequence of each choice:** Finite lawful restricted retention: keeps required evidence with controlled access/destruction. Demonstrated anonymization/deletion: reduces identity with safe obligation/dedup handoff. Valid legal hold: limited reviewed extension, not indefinite storage. Defer: privacy-dependent workflows blocked; no financial-row hard delete.
- **Recommendation:** Define per-field purpose/subject/access/basis/duration, holds, actor/reason scrubs, backups/caches/replay and key destruction preserving source/amount/old invoice facts and open obligations, under Q16/L05.
- **Decision owner:** legal (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** Conditional: reference necessity/wind-down needs P04-P06; legal policy local.
- **Approval status:** Approval required; no retention exception or runtime erasure proof selected.

### Q25 - Flat-fee amount and penalty calculation base

- **Decision ID:** Q25
- **Exact question:** **Approval required**: What exact flat cancellation fee applies at 48 hours or more? Define currency, percentage penalty base for the 5%/35% bands, rounding/caps, partial/unpaid captures and refund calculation without negative refund or double provider-fee deduction.
- **Current proposed default / approved scope:** Flat band and 5%/35% rates selected; exact flat amount, percentage base/caps/rounding and partial/unpaid capture refund calculation remain unset.
- **Alternatives and consequence of each choice:** Chosen flat amount changes retained penalty and refund; no zero/default invented. Captured versus immutable booked-service or another explicit lawful base changes percentage penalty, especially partial payments. Caps/residual conventions prevent over-retention/paise drift but require selection; do not silently clamp. Defer: incomplete monetary outcome blocked.
- **Recommendation:** Name flat INR/paise amount and exact percentage base/capture/rounding/cap/refund rules under L01/L02, separate from Q26 beneficiary and Q17 fees.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G02, G03, G04, G08.
- **Cashfree account required:** No for policy; actual provider costs/refunds separately P01/P05.
- **Approval status:** Partially approved U06: percentage base selected; flat amount, rounding, caps and partial/unpaid captures remain open.
- **U06 update:** the penalty base is the captured amount before provider fees. The flat fee amount is **unresolved**; it must stay a configurable value with no default, and the flat-fee band stays blocked until the owner supplies the INR amount.

### Q26 - Recipient of each cancellation penalty

- **Decision ID:** Q26
- **Exact question:** **Approval required**: Who receives each cancellation penalty or retained amount in every U03 band, including below-four-hour zero refund? Specify beneficiary, allocation and funding authority per band; do not inherit U02 70/30 or invent staff compensation.
- **Current proposed default / approved scope:** U03 explicitly left every recipient unresolved, including retained below-four-hour captured funds, and U02 70/30 was not inherited. **Superseded by U06:** 70% salon / 30% platform of the retained pool after provider costs, for all bands.
- **Alternatives and consequence of each choice:** Salon, platform, another explicitly approved recipient or a reviewed allocation per band changes accounting/payable ownership. Any staff time compensation needs separate authority/category; never cancelled-service commission. No beneficiary chosen: retained funds stay unresolved, not spendable income or automatic payout.
- **Recommendation:** Approve named beneficiary/allocation per band with legal/accounting fund-flow authority, Q17 fees and Q19 hold. No arbitrary split or implicit 70/30.
- **Decision owner:** finance (proposed; named approver unassigned).
- **Blocking design groups:** G02, G03, G04; G06 only if separately approved compensation.
- **Cashfree account required:** No for beneficiary approval; funding/provider capability separately P02/P06.
- **Approval status:** Approved U06 for the split mechanics (70% salon / 30% platform of the retained pool, platform share rounded half-up, residual paise to the salon, shortfall absorbed by the platform). The flat-fee band stays blocked until its amount (Q25) is set.
- **U06 update:** after actual provider costs, the retained amount is split 70% salon and 30% platform for all cancellation bands (5%, 35%, under-4-hour, and the flat-fee band once its amount is set).

### Q27 - Checked-in cancellation actors and duplicate safety

- **Decision ID:** Q27
- **Exact question:** **Partially approved U05**: Customer cancellation is forbidden after check-in; owner/scoped admin checked-in cancellation requires reason and atomic audit. Approve remaining scope/consent/state/replay enforcement, preserving completed/no_show/rejected prohibitions and no duplicate effects. Monetary treatment is Q29; no staff checked-in grant is selected.
- **Current proposed default / approved scope:** U05 forbids customer cancel after check-in; current salon owner/scoped admin only with mandatory reason and audit. Completed/no_show/rejected forbidden ordinary transitions; cancelled safe replay. Remaining exact permissions/consent enforcement not assigned.
- **Alternatives and consequence of each choice:** Selected role restriction is binding, not an open customer-after-check-in alternative. Scoped owner/admin permission and cause policy changes operational authority and needs review without staff/finance self-grant. Different-key repeat serializes by booking source/version and cannot duplicate effects. Invalid consent/authority fails before commit; valid committed cancellation releases slot.
- **Recommendation:** Enforce explicit actor/state gate, reason, audit and source uniqueness; revalidate check-in race and authorize before replay. Define monetary remedy Q29 separately; no U03 penalty inheritance.
- **Decision owner:** security (proposed; named approver unassigned).
- **Blocking design groups:** G01, G03, G08, G09.
- **Cashfree account required:** No.
- **Technical recommendation update:** TP01/TA02 recommends owner cancellation request needing scoped admin approval, customer prohibition and admin reason/audit. The additional owner-to-admin gate is unapproved; no new runtime restriction or grant is selected here.
- **Approval status:** Partially approved U05: customer denial/owner-admin reason-audit and duplicate-effect invariants selected; exact scope/consent and enforcement remain review items.

### Q28 - Selected outbox/fallback and operational recovery detail

- **Decision ID:** Q28
- **Exact question:** **Partially approved U05**: Durable database outbox invalidation/retry, independent cancellation commit and fresh PostgreSQL/SQL-only outage fallback are selected. Review exact storage, lease/fencing, dead-letter/repair, primary-read/cache-generation validation, safe hold cleanup and notification scope. Numeric retry budgets/alerts and recovery access are Q30.
- **Current proposed default / approved scope:** U05 selects durable database outbox, Redis-independent cancellation, fresh primary/SQL-only outage fallback and nonauthoritative cache. Stable job identity, bounded retry/dead-letter/audited repair contract documented; exact storage/fencing and numeric config unchosen.
- **Alternatives and consequence of each choice:** Primary coverage safe baseline avoids stale negative/positive cache authority at database read cost. Optional later commit-fenced cache serving needs independently verified DB revision and refill/read checks. Durable bounded retry then retained dead-letter/repair preserves obligation; no best-effort-only cleanup or global flush. Defer implementation detail: no activation/coherence proof.
- **Recommendation:** Review exact outbox adaptation, leases/fences, key scope/generation, delayed-hold safety, audit/notification delivery and Q30 settings. Recovery must not change cancellation/money or certify newer state from an old job.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01, G03, G08, G09.
- **Cashfree account required:** No.
- **Approval status:** Partially approved U05: outbox/fallback/recovery invariants selected; storage, numbers, scoped repair access and runtime evidence remain open.

### Q29 - Checked-in cancellation refund and payout remedy

- **Decision ID:** Q29
- **Exact question:** **Approval required**: For owner/admin checked-in cancellation, choose cause-specific customer refund/partial-service remedy, fee bearer, fund reservation, beneficiary and payout hold/release with legal review. Do not apply U03 pre-start customer penalties or U02 70/30 automatically; define already-paid or uncertain transfer recovery without automatic bank debit.
- **Current proposed default / approved scope:** Owner/admin cancellation after check-in is distinct cause. Known approved capture-capped remedy is reserved/asynchronous; unknown remedy remains durable review with retained funds restricted. Exact refund/partial-service/bearer/beneficiary/hold not approved.
- **Alternatives and consequence of each choice:** Full versus partial or another lawful remedy changes customer entitlement and retained amount; cause/evidence/legal consent must be explicit. Direct salon receipts require accountable recipient remedy, not platform funds. Already paid/unknown payout needs separately authorized funded recovery; cannot erase transfer, free unknown funds or assume bank debit. Deferral never guesses zero refund/70-30 or blocks slot after valid commit.
- **Recommendation:** Product/finance/legal choose cause-specific remedy, partial-service evidence, fees, fund source, beneficiary and hold under Q17/Q19/Q25/Q26/L01-L03; preserve audit/capture/history and restrict unresolved payout.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G01-G04; G08/G09 cancellation state integration.
- **Cashfree account required:** No for policy; actual capture/refund/funding evidence separately P01/P02/P05/P06.
- **Technical recommendation update:** TP01/TA01 recommends manual finance/legal remedy review with restricted affected funds, no automatic refund percentage or payout; exact money treatment remains approval required.
- **Approval status:** Partially approved U06 for owner/admin cancellation before check-in; the checked-in monetary remedy remains **Approval required**.
- **U06 update:** before check-in the customer receives a full refund, started asynchronously after the cancellation commits, and the platform bears non-recoverable provider fees. Recovery from the salon is not authorized. Checked-in cancellation: no amount selected; affected funds stay restricted and the action is audited.

### Q30 - Retry budget, dead-letter and repair access

- **Decision ID:** Q30
- **Exact question:** **Approval required**: Select outbox retry/backoff/jitter bounds, lease duration, attempt/age budget, dead-letter alert/response targets and scoped repair authority. Review repair/replay evidence and optional cache-fence representation; no numeric limit, new schema or deployment is chosen by this review.
- **Current proposed default / approved scope:** Lifecycle selected in U05: pending/leased/retry/success/dead-letter with stable source, durable history, alerts and audited targeted repair. No retry/lease/age/alert values or repair identities selected.
- **Alternatives and consequence of each choice:** Explicit bounded backoff/lease/attempt-age/response limits trade recovery latency against load and operator work. Requeue after verified targeted repair retains source/idempotency; audited supersession needs proof current state already satisfies action. Unresolved poison delivery stays retained/dead-letter with primary fallback, never dropped/completed blindly. No global flush or money/state mutation.
- **Recommendation:** Choose bounded operational configuration, designated response/repair authority, monitoring and acceptance evidence before implementation enablement; optional cache fence is separate reviewed storage design.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01 audit; G03, G08, G09 recovery/readers.
- **Cashfree account required:** No.
- **Technical recommendation update:** TP01/TA03-TA08 now record recommended five retries after initial (six dispatches), delays 1m/5m/30m/2h/12h, five-minute lease, retained dead-letter, Sentry plus admin email, two-person finance/admin repair and 90-day resolved outbox retention. U06 later approved TA03, TA04, TA05 and TA08 as proposed and replaced two-person repair (TA07) with a single super-admin with `aal2`; the TA06 alert targets remain Approval required.
- **Approval status:** Approval required for numeric budget/access/storage details; retry/dead-letter/repair safety contract defined, not runtime-verified.

## 2. Cashfree/provider decisions P01-P06

Source: [specification section 2.3](../../verification/payment-subscription-booking-spec.md#23-provider-dependent-rules-requiring-cashfree-confirmation). Account evidence and owner approval are separate gates.

### P01 - Actual charges and canonical economic identity

- **Decision ID:** P01
- **Exact question:** **Approval required**: actual gateway/GST, Easy Split, settlement, payout and refund charges; tax-inclusive/exclusive components, refunds of fees, and when/how fees are debited
- **Current proposed default:** No tariff/tax rate, inclusive-component mapping, fee refund/debit timing or canonical charge identity is verified. Nullable application fee fields prove no actuals.
- **Alternatives and consequence of each choice:** Evidence-backed component mapping: enables final reconciliation without counting inclusive tax or corroborating invoices twice. Ambiguous mapping: fees remain unmatched/provisional and net unconfirmed. Defer: integration remains disabled.
- **Recommendation:** Require approved account pricing, synthetic invoice/statement reconciliation, stable charge identity across channels, component allocation/correction and approved bearer. No sample percentage becomes a tariff.
- **Decision owner:** finance (proposed; named approver unassigned).
- **Blocking design groups:** G02, G03, G04.
- **Cashfree account required:** Yes.
- **Approval status:** Approval required; no selection/sign-off recorded.

### P02 - Withholding and release feasibility

- **Decision ID:** P02
- **Exact question:** **Approval required**: ability to withhold all relevant vendor settlements until completed-service eligibility and dispute hold are satisfied; release, refund and reversal support
- **Current proposed default:** No withholding/release capability proved; 48-hour duration is unapproved. A local pending row cannot stop upstream settlement.
- **Alternatives and consequence of each choice:** Verified withholding: may support approved completion/dispute release. Alternative verified lawful funding product: needs Q14/P06/L03 review and equivalent guards. Early automatic settlement: violates C05 and blocks enablement. Defer: no new payout.
- **Recommendation:** Require account entitlement plus separately authorized synthetic delayed release/refund/reversal evidence before selecting fund flow.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G04, G05; G03 compensation branch.
- **Cashfree account required:** Yes.
- **Approval status:** Approval required; no selection/sign-off recorded.

### P03 - Schedule/calendar capabilities

- **Decision ID:** P03
- **Exact question:** **Approval required**: allowed daily/weekly/monthly schedules, timezone, cutoff, holidays/weekends and admin/owner selection limitations
- **Current proposed default:** Daily/weekly/monthly are candidate codes. Timezone/cutoff, weekend/holiday, month-end/DST/calendar source and owner/admin limitations are unverified.
- **Alternatives and consequence of each choice:** Only evidenced options: constrains owner timing to capability. Provider-defined calendar: requires reviewed immutable specification. No verified option: automated scheduling disabled, no implicit daily/manual fallback. Unsupported timing cannot be promised.
- **Recommendation:** Version capability/evidence, settle missing-calendar and expiry behavior, and recheck current restrictions at execution. Schedule never shortens hold.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G05, G04 scheduling.
- **Cashfree account required:** Yes.
- **Approval status:** Approval required; no selection/sign-off recorded.

### P04 - KYC and destination lifecycle

- **Decision ID:** P04
- **Exact question:** **Approval required**: vendor KYC/verification states, encrypted/tokenized destination handling and destination-change effects
- **Current proposed default:** KYC/verification mapping, tokenization/encryption support, destination-change/revocation and cooling-off controls remain unverified.
- **Alternatives and consequence of each choice:** Verified encrypted destination: requires Q15 keys/adapter access. Adequate tokenization: reduces local secrets, adds provider dependency. Changed/revoked/unverified generation: blocks stale instruction. No supported path: no payout enablement.
- **Recommendation:** Require synthetic vendor lifecycle evidence and explicit generation/state/change mapping; do not invent a cooling-off value or treat ciphertext as KYC proof.
- **Decision owner:** security (proposed; named approver unassigned).
- **Blocking design groups:** G04, G05; G01 evidence bindings.
- **Cashfree account required:** Yes.
- **Approval status:** Approval required; no selection/sign-off recorded.

### P05 - Signatures, finality, retries and recovery

- **Decision ID:** P05
- **Exact question:** **Approval required**: payout/refund final confirmation, pending/failure/reversal semantics, stable retry references, webhook signature/event schema and duplicate/out-of-order recovery
- **Current proposed default:** Real signature/schema, terminal/pending/reversal semantics, queries, retry limits and stable identities remain unverified; fake passes establish none.
- **Alternatives and consequence of each choice:** Verified terminal bound evidence: confirms matching outcome once. Unknown/timeout: retain reservations and reconcile original operation. Proved nonmovement: may permit renewed approved generation. Missing contract: block new activation/finality claims.
- **Recommendation:** Require signed synthetic events plus query/statement evidence for duplicate/out-of-order, late capture, refund/payout/reversal and timeout recovery. Acceptance never equals terminal success/failure.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01-G04; G07 purchases; dependent G05/G08 effects.
- **Cashfree account required:** Yes.
- **Approval status:** Approval required; no selection/sign-off recorded.

### P06 - Funding and cross-method transfer identity

- **Decision ID:** P06
- **Exact question:** **Approval required**: provider-side split settlement versus separate payout/manual bank transfer product; duplicate-transfer detection and operation funding
- **Current proposed default:** No verified split-versus-payout/manual product, funding or canonical confirmed-transfer identity across methods. Order/vendor reference alone proves no settlement.
- **Alternatives and consequence of each choice:** Split settlement only: no second bank transfer for settled share. Separate funded payout/manual: needs unpaid entitlement and lawful custody/funding. Shared funding-account/rail/final-reference identity: enables cross-method dedup; method-local keys alone cannot. Defer: no payout execution.
- **Recommendation:** Approve evidenced fund flow with L03; verify final UTR/reference identity, independent manual reviewer and original-operation reconciliation before enabling either method.
- **Decision owner:** finance (proposed; named approver unassigned).
- **Blocking design groups:** G01, G04, G05; G02 funding accounting.
- **Cashfree account required:** Yes.
- **Approval status:** Approval required; no selection/sign-off recorded.

## 3. Legal/accounting decisions L01-L05

Source: [specification section 2.4](../../verification/payment-subscription-booking-spec.md#24-legalaccounting-decisions-requiring-review). No statutory period, tax rate or licensing conclusion is selected.

### L01 - Customer terms and dispute rights

- **Decision ID:** L01
- **Exact question:** **Approval required**: customer cancellation/refund terms, four-hour/no-show consequences, dispute rights and notification/consent. An operational 48-hour hold cannot extinguish a later valid dispute.
- **Current proposed default:** D01-D06/D15 are proposals. No approved cause/no-show terms, consent/notification, dispute scope or legal dispute deadline supplied.
- **Alternatives and consequence of each choice:** Approve lawful full early/salon refunds plus explicit late/no-show rules: fixes entitlement and notice duties. Other lawful terms: changes refund/consent/recovery and Q policies. Defer: new dependent terms/finalization blocked, existing duties continue. Operational hold never extinguishes later valid dispute.
- **Recommendation:** Obtain named legal sign-off on causes, exact boundary, appeals, reschedules, late captures, notification and later disputes before product selection.
- **Decision owner:** legal (proposed; named approver unassigned).
- **Blocking design groups:** G03, G04, G07, G08, G09.
- **Cashfree account required:** No for terms; provider remedy feasibility separately needs P02/P05.
- **Approval status:** Approval required; no selection/sign-off recorded.

### L02 - Tax, invoices, recognition and chart of accounts

- **Decision ID:** L02
- **Exact question:** **Approval required**: fee bearer, taxes on each fee and cancellation allocation, invoice issuer, tax inclusion, credit notes and subscription tax treatment. Who books receivables/deficits and how recoveries are authorized.
- **Current proposed default:** Separate actual components and sealed append-only accounting proposed; fee/tax bearers, invoice issuer, rates/inclusion, credit notes, recognition events and deficit recovery unset.
- **Alternatives and consequence of each choice:** Approved inclusive treatment: avoids double-added tax. Approved exclusive treatment: needs lawful invoice/total presentation consistent with C01. Alternative evidence-backed recognition/allocation: changes postings/net, never historical facts. Defer: dependent accounting cannot finalize.
- **Recommendation:** Finance/legal should approve controlled account codes, recognition, invoice/credit-note duties, allocation, receivables and subscription tax/benefits with P01. No tax rate follows from examples or NULL flags.
- **Decision owner:** finance (proposed; named approver unassigned).
- **Blocking design groups:** G01, G02, G03, G04, G06, G07.
- **Cashfree account required:** Conditional: policy local; actual debit/component mapping needs P01.
- **Approval status:** Approval required; no selection/sign-off recorded.

### L03 - Permitted custody, reserves and recovery

- **Decision ID:** L03
- **Exact question:** **Approval required**: permitted fund flow, provider versus platform custody, hold/reserve arrangement, manual transfer funding and recovery after payout; prevent double funding and unsupported platform-held balances.
- **Current proposed default:** No platform custody, hold/reserve arrangement, manual funding, recovery or bank-debit authority approved.
- **Alternatives and consequence of each choice:** Lawful provider-held funds: depends on verified withholding/release. Separately funded lawful payout: needs explicit funds/reserves and no double payment. No lawful feasible path: initiation blocked. Approved deficit recovery: preserves original movement; erasing payout or assuming bank debit is not permitted.
- **Recommendation:** Approve fund-flow diagram, responsible entity, reserve/funding source, deficit ownership and recovery authority with P02/P06/Q04/Q16 before product choice.
- **Decision owner:** legal (proposed; named approver unassigned).
- **Blocking design groups:** G01-G05.
- **Cashfree account required:** Conditional: legal architecture local; feasibility needs P02/P06.
- **Approval status:** Approval required; no selection/sign-off recorded.

### L04 - Staff recognition and lawful correction/recovery

- **Decision ID:** L04
- **Exact question:** **Approval required**: staff service commission versus cancellation/time compensation, earning/recognition event, lawful reversal and correction authority, including after payout.
- **Current proposed default:** Internal commission separate from platform payout; D10 basis/earning/reversal, time compensation and recovery require review.
- **Alternatives and consequence of each choice:** Service-only completion earning: no cancelled-service commission, explicit reversal duties. Separately funded time compensation: distinct obligation/category/authority. Lawful post-disbursement recovery: process/receivable, never automatic payroll/bank debit. Defer: dependent rules/corrections inactive.
- **Recommendation:** Approve earning/recognition/evidence, basis, refunds/reassignment and recovery with Q10/Q13; staff payroll/bank transfer is outside this ledger.
- **Decision owner:** legal (proposed; named approver unassigned).
- **Blocking design groups:** G06; G01 correction authority.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### L05 - Retention, anonymization and evidence access

- **Decision ID:** L05
- **Exact question:** **Approval required**: financial evidence retention periods, pseudonymization versus anonymization, erasure limits, legal holds, provider references, encrypted backups and destruction/access authority.
- **Current proposed default:** All 43 fields and every new field need explicit policy. Detached UUID/digest/ciphertext is pseudonymous; no duration/legal hold/provider exception established.
- **Alternatives and consequence of each choice:** Finite lawful restricted retention: evidence preserved with access/review/destruction duties. Demonstrated anonymization/deletion: reduces identity but requires dedup/obligation handoff. Conditional provider-required retention: requires real necessity and lawful basis. Defer: new privacy-dependent workflow blocked, no indefinite exception implied.
- **Recommendation:** Approve each L05-F row plus every new field: subject/purpose/basis, duration/event, hold/review, key/backup destruction, access/handoff and residual linkability. Narrow guard changes only.
- **Decision owner:** legal (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** Conditional: provider necessity/reference branches need P04/P05; legal policy local.
- **Approval status:** Approval required; no selection/sign-off recorded.

### L05 field-level subdecisions

These 43 decisions belong to L05/Q15/Q16, not a seventh approval category.
Exact fields, primary proposals, bounded treatments and source gates come from
[the classification](ERASURE_CLASSIFICATION.md#exact-field-by-field-classification).
Questions are register-local formulations. Aggregate L05 approval cannot silently
approve individual fields or new fields absent from the historical inventory.

The following values apply explicitly to **every L05-F row**:

- **Decision owner:** legal (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09 wherever the field is used/retained/scrubbed
  by the dependent new workflow; downstream privacy dependencies inherit the block.
- **Alternatives and consequence of each choice:** select the proposed category
  subject to its bounded treatment, with category consequences below; replace it
  with an explicitly lawful field-specific treatment, requiring new necessity,
  access, retention, snapshot and dedup review and potentially changing what can
  be reconciled/erased; or defer, leaving dependent new handling blocked while
  outstanding obligations remain owned. No substitution is automatically safe.
- **Recommendation:** conditionally prefer each proposed category only after its
  bounded treatment, listed source gate and category conditions below are approved.
- **Approval status:** Approval required; no field selection/sign-off recorded.

| Proposed category | Consequence if selected and conditions for recommendation |
| --- | --- |
| retain | Preserve controlled facts for approved finite retention; validate legacy values/minimal access, without extending enclosing operational-row lifetime. |
| anonymize | Remove identifying content while conserving economic facts; prove nonidentifying template/output and handle third-party content/holds. |
| delete | Remove payload at approved boundary after pending-work handoff; no financial-row hard deletion. |
| encrypt | Retain minimum operational evidence under scoped authenticated encryption; approve finite destruction, keys/backups and lookup/uniqueness continuity. |
| digest only | Preserve minimum keyed dedup/throttle identity, still pseudonymous; approve domain separation, window, rotation and replay continuity. |
| provider-required retention | Preserve minimum encrypted/restricted evidence only after necessity/lawful basis; otherwise exception stays unapproved pending another safe treatment that preserves open obligations. |

Cashfree Conditional means later evidence for the listed P04/P05 branch. No does
not waive non-Cashfree evidence, for example email-provider correlation need.
Existing cascades, salon_access deletion and immutable financial facts remain
binding; a retain label is no permission to archive an otherwise deleted row.

| Decision ID | Exact question | Current proposed default | Bounded treatment / recommendation conditions | Approval dependencies | Cashfree account required |
| --- | --- | --- | --- | --- | --- |
| L05-F01 | Approve or replace the proposed digest only treatment for `api_rate_limits.bucket_hash`, including this row's bounded treatment and dependencies? | digest only; unapproved | Keep only a versioned keyed bucket digest for the approved throttle window; no reversible contact/IP input. Existing hash algorithm is not presumed safe. | **Approval required** — Q15/Q16/L05: key, input minimization, expiry and erasure scope. | No |
| L05-F02 | Approve or replace the proposed retain treatment for `booking_audit_events.event_type`, including this row's bounded treatment and dependencies? | retain; unapproved | Allowlisted event code only; preserve event meaning after actor detachment. | **Approval required** — Q16/L05: finite retention/access and handling invalid legacy values. | No |
| L05-F03 | Approve or replace the proposed retain treatment for `booking_audit_events.new_state`, including this row's bounded treatment and dependencies? | retain; unapproved | Controlled state code; no copied reason, name or payload. | **Approval required** — Q16/L05: retention and legacy value validation. | No |
| L05-F04 | Approve or replace the proposed retain treatment for `booking_audit_events.old_state`, including this row's bounded treatment and dependencies? | retain; unapproved | Controlled prior state code; preserve transition history. | **Approval required** — Q16/L05: retention and legacy value validation. | No |
| L05-F05 | Approve or replace the proposed retain treatment for `booking_payments.collection_method`, including this row's bounded treatment and dependencies? | retain; unapproved | Controlled receipt-method category, separate from account/UPI details. | **Approval required** — Q16/L02/L05: financial classification and duration. | No |
| L05-F06 | Approve or replace the proposed retain treatment for `booking_payments.commission_base`, including this row's bounded treatment and dependencies? | retain; unapproved | Preserve approved historical formula-basis code; do not reprice receipts. | **Approval required** — Q04/Q16/L02/L05: code validation, recognition and retention. | No |
| L05-F07 | Approve or replace the proposed retain treatment for `booking_payments.commission_policy_version`, including this row's bounded treatment and dependencies? | retain; unapproved | Preserve historical policy version, containing no personal narrative. | **Approval required** — Q04/Q16/L02/L05: policy registry and retention. | No |
| L05-F08 | Approve or replace the proposed delete treatment for `booking_payments.provider_session_id`, including this row's bounded treatment and dependencies? | delete; unapproved | Remove checkout-session material when no longer operationally needed and on applicable erasure; never put it into immutable audit. If it is a credential, restrict it during its operational life. | **Approval required** — Q15/Q16/P05/L05: actual field sensitivity, termination point and safe reconciliation handoff before removal. | Conditional: P05 |
| L05-F09 | Approve or replace the proposed retain treatment for `bookings.checkout_policy_version`, including this row's bounded treatment and dependencies? | retain; unapproved | Keep historical checkout policy identity; do not rewrite old surcharge orders. | **Approval required** — Q08/Q16/L02/L05: legacy treatment and retention. | No |
| L05-F10 | Approve or replace the proposed delete treatment for `email_events.body`, including this row's bounded treatment and dependencies? | delete; unapproved | Clear personal message content at the approved erasure boundary; retain only separate nonpersonal event/status facts. | **Approval required** — Q16/L05: affected-recipient/third-party scope, pending-delivery cancellation and any hold exception. | No |
| L05-F11 | Approve or replace the proposed digest only treatment for `email_events.event_key`, including this row's bounded treatment and dependencies? | digest only; unapproved | Retain only keyed deduplication identity without embedded user/booking text; scope and version it. | **Approval required** — Q15/Q16/L05: atomic replay migration, key rotation and expiry; do not break existing unique-key retries. | No |
| L05-F12 | Approve or replace the proposed retain treatment for `email_events.event_type`, including this row's bounded treatment and dependencies? | retain; unapproved | Allowlisted delivery-purpose code, not free text. | **Approval required** — Q16/L05: code allowlist and retention. | No |
| L05-F13 | Approve or replace the proposed retain treatment for `email_events.last_error_code`, including this row's bounded treatment and dependencies? | retain; unapproved | Allowlisted sanitized error class only; raw provider errors are not retained as codes. | **Approval required** — Q16/L05: legacy sanitization, pending-work support and retention. | No |
| L05-F14 | Approve or replace the proposed encrypt treatment for `email_events.provider_message_id`, including this row's bounded treatment and dependencies? | encrypt; unapproved | Restrict minimal operational provider correlation as authenticated ciphertext; scrub or destroy its key at approved end of need. | **Approval required** — Q15/Q16/L05: email-provider lookup need, authorized decryptor, expiry and backup handling; no provider requirement assumed. | No |
| L05-F15 | Approve or replace the proposed delete treatment for `email_events.recipient`, including this row's bounded treatment and dependencies? | delete; unapproved | Remove address/contact on the applicable verified erasure; preserve no recipient in immutable audit, dedup keys or retry payloads. | **Approval required** — Q16/L05: unsent delivery handling, third-party associations and hold exceptions. | No |
| L05-F16 | Approve or replace the proposed retain treatment for `email_events.status`, including this row's bounded treatment and dependencies? | retain; unapproved | Allowlisted delivery state only, with identity detached where allowed. | **Approval required** — Q16/L05: retention and residual linkability. | No |
| L05-F17 | Approve or replace the proposed anonymize treatment for `email_events.subject`, including this row's bounded treatment and dependencies? | anonymize; unapproved | Replace erased-person content with a controlled nonpersonal template label; no original subject copied elsewhere. | **Approval required** — Q16/L05: exact redaction scope/template, unresolved delivery/holds and evidence that output is nonidentifying. | No |
| L05-F18 | Approve or replace the proposed anonymize treatment for `payment_anomalies.detail`, including this row's bounded treatment and dependencies? | anonymize; unapproved | Remove arbitrary personal/provider payload; preserve only approved anomaly reason/fact references separately from restricted evidence. | **Approval required** — Q15/Q16/L02/L05: safe legacy decomposition and unresolved-anomaly evidence needs. | No |
| L05-F19 | Approve or replace the proposed retain treatment for `payment_anomalies.kind`, including this row's bounded treatment and dependencies? | retain; unapproved | Allowlisted anomaly category; no arbitrary explanation. | **Approval required** — Q16/L02/L05: classification and retention. | No |
| L05-F20 | Approve or replace the proposed retain treatment for `payment_anomalies.provider`, including this row's bounded treatment and dependencies? | retain; unapproved | Provider product/code only, excluding merchant/account identity. | **Approval required** — Q16/L02/L05: code validation and duration. | No |
| L05-F21 | Approve or replace the proposed encrypt treatment for `payment_anomalies.provider_ref`, including this row's bounded treatment and dependencies? | encrypt; unapproved | Restricted encrypted minimum reconciliation locator; separately keyed digest if duplicate detection needs it. | **Approval required** — Q15/Q16/P05/L05: reference semantics, evidence need, key custody, erasure and retention. | Conditional: P05 |
| L05-F22 | Approve or replace the proposed retain treatment for `payment_provider_account_audit.action`, including this row's bounded treatment and dependencies? | retain; unapproved | Controlled onboarding action code; no before/after secret payload. | **Approval required** — Q16/L05: allowlist and duration. | No |
| L05-F23 | Approve or replace the proposed anonymize treatment for `payment_provider_account_audit.detail`, including this row's bounded treatment and dependencies? | anonymize; unapproved | Replace personal/vendor payload with controlled result/reason facts; any justified evidence belongs in separately restricted storage. | **Approval required** — Q15/Q16/P04/L05: field-level extraction, lawful evidence retention and deletion scope. | Conditional: P04 |
| L05-F24 | Approve or replace the proposed retain treatment for `payment_provider_account_audit.new_status`, including this row's bounded treatment and dependencies? | retain; unapproved | Controlled onboarding state, not provider response text. | **Approval required** — Q16/P04/L05: state mapping and retention. | Conditional: P04 |
| L05-F25 | Approve or replace the proposed retain treatment for `payment_provider_account_audit.previous_status`, including this row's bounded treatment and dependencies? | retain; unapproved | Controlled prior onboarding state. | **Approval required** — Q16/P04/L05: state mapping and retention. | Conditional: P04 |
| L05-F26 | Approve or replace the proposed retain treatment for `payment_provider_account_audit.provider`, including this row's bounded treatment and dependencies? | retain; unapproved | Provider code only, not a vendor/account identifier. | **Approval required** — Q16/L05: validation and retention. | No |
| L05-F27 | Approve or replace the proposed encrypt treatment for `payment_provider_account_audit.vendor_ref`, including this row's bounded treatment and dependencies? | encrypt; unapproved | Restrict vendor reconciliation reference after operational mapping deletion; never expose it as ordinary audit text. | **Approval required** — Q15/Q16/P04/P05/L05: need, duration, operator handoff and eventual key/reference destruction. | Conditional: P04/P05 |
| L05-F28 | Approve or replace the proposed retain treatment for `payment_refunds.kind`, including this row's bounded treatment and dependencies? | retain; unapproved | Preserve controlled historical refund category and its meaning; no new cancellation-policy inference. | **Approval required** — Q01/Q02/Q16/L01/L02/L05: category compatibility and retention. | No |
| L05-F29 | Approve or replace the proposed retain treatment for `salon_access.trial_ended_reason`, including this row's bounded treatment and dependencies? | retain; unapproved | Allowlisted reason only, not a personal explanation. Existing salon_access deletion still removes the whole operational row on owner erasure. | **Approval required** — Q06/Q16/L05: any distinct nonpersonal lifecycle-history retention; no extension of current row lifetime. | No |
| L05-F30 | Approve or replace the proposed anonymize treatment for `subscription_billing_records.benefits`, including this row's bounded treatment and dependencies? | anonymize; unapproved | Preserve approved nonpersonal purchased-benefit facts while removing identifiers/free-form personal additions; never change the contractual economic entitlement. | **Approval required** — Q09/Q16/L02/L05: immutable-snapshot-compatible field schema/redaction and restricted evidence if exact payload is lawfully needed. | No |
| L05-F31 | Approve or replace the proposed retain treatment for `subscription_billing_records.billing_interval`, including this row's bounded treatment and dependencies? | retain; unapproved | Preserve the purchased interval, not a newly inferred renewal policy. | **Approval required** — Q09/Q16/L02/L05: duration and historical meaning. | No |
| L05-F32 | Approve or replace the proposed retain treatment for `subscription_billing_records.currency`, including this row's bounded treatment and dependencies? | retain; unapproved | Preserve the financial currency code. | **Approval required** — Q16/L02/L05: retention. | No |
| L05-F33 | Approve or replace the proposed retain treatment for `subscription_billing_records.failure_code`, including this row's bounded treatment and dependencies? | retain; unapproved | Sanitized allowlisted error class only; no raw provider body. | **Approval required** — Q16/L05: code sanitization and unresolved purchase evidence. | No |
| L05-F34 | Approve or replace the proposed retain treatment for `subscription_billing_records.plan_code`, including this row's bounded treatment and dependencies? | retain; unapproved | Preserve purchased plan identity, without reseeding/admin-price reset. | **Approval required** — Q09/Q16/L02/L05: validation and retention. | No |
| L05-F35 | Approve or replace the proposed retain treatment for `subscription_billing_records.provider`, including this row's bounded treatment and dependencies? | retain; unapproved | Provider code only; no account scope or credentials embedded. | **Approval required** — Q16/L02/L05: code validation and retention. | No |
| L05-F36 | Approve or replace the proposed provider-required retention treatment for `subscription_billing_records.provider_order_ref`, including this row's bounded treatment and dependencies? | provider-required retention; unapproved | Only if a named provider/financial evidence obligation is established: keep minimum exact locator encrypted/restricted, plus approved dedup digest; otherwise no provider exemption is established. | **Approval required** — Q15/Q16/P05/L02/L05: necessity, lawful basis, duration/hold, access and eventual destruction. | Conditional: P05 |
| L05-F37 | Approve or replace the proposed provider-required retention treatment for `subscription_billing_records.provider_payment_ref`, including this row's bounded treatment and dependencies? | provider-required retention; unapproved | Only verified necessary capture/refund evidence, encrypted/restricted with scope-matched dedup; not ordinary owner-visible history. | **Approval required** — Q15/Q16/P05/L02/L05: evidence mapping, duration, post-erasure reconciliation and destruction. | Conditional: P05 |
| L05-F38 | Approve or replace the proposed provider-required retention treatment for `subscription_billing_records.receipt`, including this row's bounded treatment and dependencies? | provider-required retention; unapproved | Preserve exact receipt only where required to reconcile or evidence the purchase; classify whether it is internal or provider-required before any exception. Restrict/encrypt if retained. | **Approval required** — Q15/Q16/P05/L02/L05: actual semantics, uniqueness/replay continuity, necessity and retention; the column name proves no provider requirement. | Conditional: P05 |
| L05-F39 | Approve or replace the proposed retain treatment for `subscription_billing_records.status`, including this row's bounded treatment and dependencies? | retain; unapproved | Controlled historical purchase state; preserve unresolved money and application facts. | **Approval required** — Q09/Q16/L02/L05: duration and wind-down semantics. | No |
| L05-F40 | Approve or replace the proposed retain treatment for `subscription_plans.features`, including this row's bounded treatment and dependencies? | retain; unapproved | Curated nonpersonal plan-feature schema only. Personal/custom legacy text must be separately assessed, not grandfathered as public catalog content. | **Approval required** — Q09/Q16/L02/L05: benefits schema, legacy review and catalog retention. | No |
| L05-F41 | Approve or replace the proposed anonymize treatment for `support_messages.body`, including this row's bounded treatment and dependencies? | anonymize; unapproved | Redact erased-person content or replace the affected authored message with a controlled removed-content marker; preserve other parties' content only where justified. | **Approval required** — Q16/L01/L05: author/mentioned-person scope, dispute evidence, legal hold and demonstrated nonidentifying output. | No |
| L05-F42 | Approve or replace the proposed retain treatment for `support_tickets.status`, including this row's bounded treatment and dependencies? | retain; unapproved | Controlled support workflow state; this does not stop existing customer-ticket cascades or retain deleted rows. | **Approval required** — Q16/L05: any separately justified retained fact and duration. | No |
| L05-F43 | Approve or replace the proposed anonymize treatment for `support_tickets.subject`, including this row's bounded treatment and dependencies? | anonymize; unapproved | Replace personal subject with a controlled nonpersonal support category, without copying the original to audit/logs. | **Approval required** — Q16/L01/L05: third-party scope, dispute evidence, holds and acceptable nonidentifying category. | No |

## 4. Runtime privilege decisions

Sources: [shared minimum-rights contract](README.md#minimum-rights-contract),
[G01](0048-admin-financial-audit.md), [G09](09-slot-hold-concurrency-support.md)
and [Mumbai privilege risks](../MUMBAI_SCHEMA_HISTORY_RECONCILIATION_2026-10-18.md#6-rls-and-privilege-risks).
These subdecisions expand Q13/Q15/Q16; process duties are not asserted existing
DB roles. No concrete privilege separation or effective runtime identity is proved.

### RP01 - Effective identity and principal separation

- **Decision ID:** RP01
- **Exact question:** Which concrete runtime principals, effective rights and guarded entry points enforce API, audit, accounting, executor, authority and erasure duties, and how is owner/BYPASSRLS residual risk contained before activation?
- **Current proposed default:** Distinct least-rights responsibilities proposed, but no concrete credentials/roles verified or selected.
- **Alternatives and consequence of each choice:** Separate scoped principals: limits cross-duty compromise, requires credential/adapter design. Reviewed narrow guards/adapters: must prove equivalent ceilings including invoker underlying rights. Broad owner/BYPASSRLS credentials: retain bypass risk, so new finance activation remains blocked; RLS/FORCE RLS alone cannot resolve it. Defer: no sensitive writers.
- **Recommendation:** Approve an enforceable matrix after separately authorized runtime identity/effective-rights inventory. Do not mutate managed Supabase roles or infer finance power from a service credential.
- **Decision owner:** security (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### RP02 - Object ACLs and function/publication boundaries

- **Decision ID:** RP02
- **Exact question:** Which creator, object/column/default/inherited/schema privileges, function caller contracts and publication exclusions must each future artifact assert without reopening client application access?
- **Current proposed default:** Backend-only RLS/client revocations, pinned invoker entry points, no new finance publication. Exact creator and effective ACL matrix remains pending.
- **Alternatives and consequence of each choice:** Explicit object ACL assertions in reviewed transaction: prevents creator defaults reopening rights. Preserve existing definer until caller review: keeps current contract while replacement is evaluated. Invoker replacement: needs scoped underlying rights. New definer bypass/blanket grants or finance publication is outside this proposal. Defer: no new entry-point activation.
- **Recommendation:** Review exact creator/object/function matrix and latent client policies; preserve 0039/0040, extension exclusions and managed privileges. No sweeping revocation to manufacture zero access counts.
- **Decision owner:** security (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### RP03 - Authority bootstrap and stages

- **Decision ID:** RP03
- **Exact question:** Who bootstraps/manages authority, which permissions/scopes/amount limits and independent stages apply, and which bounded system authority may approve automatic work?
- **Current proposed default:** Q13 must select authority.manage bootstrap, grantors, independence, limits, stages, revocation and automation. No seed or implicit super-admin power.
- **Alternatives and consequence of each choice:** Independent audited bootstrap with human approval: creates reviewed grantors, adds overhead. Explicit scoped system delegation: enables automation under current stages/limits. No grantor/unknown policy: commands disabled. Self-grant/self-expansion and executor self-approval excluded.
- **Recommendation:** Approve Q13 matrix, current DB profile/role, admin aal2, independent manual verifier and revocation rules; recheck current authority/stage/expiry at initiation.
- **Decision owner:** security (proposed; named approver unassigned).
- **Blocking design groups:** G01, G04, G05; sensitive G02-G09 commands.
- **Cashfree account required:** No for authority policy; P06 independently governs transfer identity.
- **Approval status:** Approval required; no selection/sign-off recorded.

### RP04 - Rollback-safe audit and availability

- **Decision ID:** RP04
- **Exact question:** Which independent durable mechanism records denied/rolled-back commands, and what happens when audit or outcome-ingestion availability fails?
- **Current proposed default:** Business effects/audit commit together; failed attempts need independent minimal audit transaction or durable security outbox. No mechanism/availability policy chosen.
- **Alternatives and consequence of each choice:** Independent audit transaction: supports sanitized failure after rollback but needs separate durability. Durable security outbox: requires independent receipt/recovery/delivery guarantees. Unavailable durable audit: proposed new admin commands fail closed; verified incoming money outcomes still need durable receipt. Defer mechanism: new commands disabled.
- **Recommendation:** Select exact crash/denial/availability behavior with no FK to rolled-back objects. Audit seals freeze assertions; they do not prove balanced accounting or money finality.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### RP05 - Canonical identity, attestation and key rotation

- **Decision ID:** RP05
- **Exact question:** Which canonical command/payload/economic-source identities, trusted verifiers and key transitions preserve deduplication across channels, retry, scope/environment, rotation and erasure?
- **Current proposed default:** Immutable replay namespace and attested provenance proposed; canonical fields/digest versions, verifier authority and cross-key transition unapproved.
- **Alternatives and consequence of each choice:** Stable source/command mapping and trusted scoped attestation: permits guarded recognition without duplicate expenses. Ambiguous/unknown evidence: remains ineligible for real finalization. Rotation preserving logical uniqueness: keeps replay protection; key_version in uniqueness alone may reopen duplicates. Defer: dependent finalization blocked.
- **Recommendation:** Approve explicit canonicalization, source/charge/transfer mappings, attestation and lawful restricted post-erasure linkage under Q14-Q16/P01/P05/P06. Mock/sandbox scopes cannot be relabelled live.
- **Decision owner:** security (proposed; named approver unassigned).
- **Blocking design groups:** G01-G07; replay/erasure integration G08/G09.
- **Cashfree account required:** Conditional: local design needs no account; real mapping needs P01/P05/P06.
- **Approval status:** Approval required; no selection/sign-off recorded.

### RP06 - Erasure powers, immutable guards and handoff

- **Decision ID:** RP06
- **Exact question:** Which verified request-scoped erasure powers, column-level scrub exceptions, FK detachments and restricted operator handoff preserve privacy and open obligations?
- **Current proposed default:** Only classified identity/payload scrub; financial amounts/sources/policy/outcomes/seals immutable. Exact guards/handoff, composite FKs and staff-shell retention strategy pending.
- **Alternatives and consequence of each choice:** Narrow scrub with retained financial shells: allows privacy treatment without repricing facts. Lawful finite restricted handoff: permits unknown transfer/refund/dispute work after mappings vanish. Retained anonymized staff shell versus approved nullable identity link changes FK handling and must preserve financial parent bindings. Generic GUC bypass/indefinite erasure refusal not approved. Defer: privacy-dependent activation blocked.
- **Recommendation:** Approve Q16/L05 guards, G03 action-request/G08 holiday/block SET NULL exceptions, per-column identity nulling, third-party scrubs, keys/backups and named obligation owners. Flags alone confer no authority.
- **Decision owner:** security (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** Conditional: wind-down/reference access needs P04-P06.
- **Approval status:** Approval required; no selection/sign-off recorded.

### RP07 - Shared lock ranks and implicit-lock review

- **Decision ID:** RP07
- **Exact question:** What exhaustive table-rank map, implicit FK/unique/exclusion/trigger analysis and bounded worker/batch protocol implement the shared order across all legacy/new writers?
- **Current proposed default:** Sorted profile, customer, salon/subscription, funding and ranked-row order proposed. Exact ranks, helper split, implicit locks and bounded erasure/batch phases unapproved.
- **Alternatives and consequence of each choice:** Complete shared order and early helpers: coordinates all writers, needs later cross-connection proof. Retain bypassing/inverted legacy writers: new activation blocked. Separately committed queue lease then ordered transaction versus reviewed bounded phases changes orchestration; neither holds late business rows awaiting earlier gates. Missing earlier key requires rollback/rediscovery. Defer: executable preparation blocked.
- **Recommendation:** Publish exact table ranks and namespaces before executable review; coordinate late customer/access triggers, separate salon/subscription paths, staff/service changes, authority and deletion. External I/O stays outside row locks.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** No.
- **U04 scope:** Cancellation joins the shared lock and fresh-snapshot booking protocol. Its occupancy ceases at commit, without waiting for refund or Redis TTL. Q27/Q28 define state/audit/invalidation/notification review. Stale negative caches and an orphan cancelled-generation hold cannot hide a released candidate; delayed cleanup must preserve newer valid holds. Every booking still revalidates SQL/exclusion.
- **Approval status:** Approval required; no selection/sign-off recorded.

### RP08 - Typed integration, capability gates and rollback

- **Decision ID:** RP08
- **Exact question:** Which staged artifact/link ownership, server capability predicates and compatible API/worker rollout prevent incomplete new-mode writes and preserve reconciliation on rollback?
- **Current proposed default:** G01 foundation before G02 seals; G04/later owners attach typed links. New mode disabled until mandatory authority/audit/accounting/concurrency/privacy constraints exist; final split/contract pending.
- **Alternatives and consequence of each choice:** Early inert helpers and later validated typed links: dependency-safe installation with reviewed split. Foundation kept late: every dependent writer stays server-blocked until complete. Feature flags alone insufficient. Empty unused schema may allow reviewed removal; data-bearing rollback stops initiation and repairs forward, preserving evidence/keys/reconciliation.
- **Recommendation:** Approve exact same-command/source/salon/currency/environment/generation links, schema capability predicates and version-compatible API/state/error mapping across old/new workers. No NULL legacy escape for new mode; assign no IDs here.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** No for gating design; provider predicates separately need P01-P06.
- **U04 scope:** Cancellation joins the shared lock and fresh-snapshot booking protocol. Its occupancy ceases at commit, without waiting for refund or Redis TTL. Q27/Q28 define state/audit/invalidation/notification review. Stale negative caches and an orphan cancelled-generation hold cannot hide a released candidate; delayed cleanup must preserve newer valid holds. Every booking still revalidates SQL/exclusion.
- **Approval status:** Approval required; no selection/sign-off recorded.

## 5. Mumbai migration-history decisions

Source: [Mumbai report sections 8-10](../MUMBAI_SCHEMA_HISTORY_RECONCILIATION_2026-10-18.md#8-required-forward-only-reconciliation-plan).
MH01-MH09 cover report preparation gates A01-A06 and separately required later
history/execution/deployment approvals. No history strategy is selected here.

### MH01 - Restoration provenance and backfill uncertainty

- **Decision ID:** MH01
- **Exact question:** What restoration provenance and historical data/backfill evidence can be accepted, which effects remain unknown, and how is each uncertainty resolved without asserting migrations ran?
- **Current proposed default:** Keep history untouched; source head/restore names do not establish execution. Eight payment rows were observed historically, not proved synthetic.
- **Alternatives and consequence of each choice:** Document accepted provenance/unknowns: permits bounded proof planning, not history change. Separately authorized evidence gathering: can narrow uncertainty. Unknown required data effects: blocks dependent preparation or needs explicit safe disposition. Baseline/old upgrade replay against populated schema is not a default.
- **Recommendation:** Preserve baseline/revisions/sealed restore evidence and historical snapshot meaning; record data uncertainty separately from schema compatibility.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### MH02 - Independent PG17 reference strategy

- **Decision ID:** MH02
- **Exact question:** Which separately authorized disposable PG17 reference/harness represents baseline, managed prerequisites and prepared 0038-0040 without replay overlap or policy bypass?
- **Current proposed default:** No independent expected-PG17-0040 proof. Portable policy stops at 0037; consolidated baseline overlap including staff.experience and managed prerequisites need review.
- **Alternatives and consequence of each choice:** Isolated identity-verified PG17 build: can support complete comparison under separate permission. Another explicit reviewed reference method: must cover same effects/prerequisites without rewriting history/weakening guards. Old PG18/October 15 catalog match alone: insufficient, hold remains.
- **Recommendation:** Approve report A02 reference method and acceptance criteria before any later database build. No reference construction/SQL/live inspection is authorized here.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### MH03 - Full equivalence and accepted differences

- **Decision ID:** MH03
- **Exact question:** Which full PG17 catalog/data criteria and explicitly justified physical-order/deparse differences establish final-state compatibility independently of historical execution?
- **Current proposed default:** Prepared effects appear present; canonical equality remains unverified. Owners/effective/default ACLs, publications, data and physical representation need acceptance criteria.
- **Alternatives and consequence of each choice:** Accept proved representation-only differences: avoids unnecessary rebuild with documented consumer impact. Semantic mismatch: separately reviewed forward repair. Unresolved difference: no equality acceptance. Physical column order and PG17/PG18 NOT NULL/deparse differences cannot prove execution.
- **Recommendation:** Compare full columns/order, functions/config/security, constraints/indexes/triggers, RLS/effective/default/inherited rights, extensions/publications and seed/data effects; review row-composite/SELECT-star consumers.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### MH04 - No-op compatibility versus forward repair

- **Decision ID:** MH04
- **Exact question:** For each proved mismatch, is no structural change appropriate or what separately reviewed forward-only repair preserves financial facts, definitions and hardening?
- **Current proposed default:** No repairs authorized; already-compatible definitions need no recreation/backfill. Incompatible final definitions require exact forward plan.
- **Alternatives and consequence of each choice:** Proved compatibility: no structural repair for that item. Proved incompatibility: separately approved bounded forward repair. Unresolved: held. Broad IF NOT EXISTS, duplicate seeds, baseline replay or cosmetic table rebuild can hide/damage state and are outside proposal.
- **Recommendation:** Review deltas after MH02/MH03, preserving 0039/0040, erasure and legacy snapshots. Never relabel mock/estimated amounts as provider actuals.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### MH05 - Independent restored-history recording strategy

- **Decision ID:** MH05
- **Exact question:** After schema/data review, what explicit restored-history recording strategy and guarded tooling, if any, may be approved without claiming unproved historical Alembic execution?
- **Current proposed default:** Mumbai history empty and fails current guard. No applied revision/starting point certified; no transition/stamp approved or proposed for execution.
- **Alternatives and consequence of each choice:** Keep untouched: Mumbai execution held. Explicit reviewed truthful restoration transition: requires new exact policy/tooling authorization after proof. Future stamp consideration: distinct explicit approval/policy review, never inferred from equality. Guard removal/automatic stamp excluded.
- **Recommendation:** Present concrete truthful strategy only after MH01-MH04 acceptance; preparation, history mutation and execution must remain distinct approvals.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### MH06 - Bounded executable preparation scope

- **Decision ID:** MH06
- **Exact question:** Which exact source/design versions, selected groups, branch and executable preparation artifacts may later be authorized, including any explicitly bounded inert scaffolding with open policy choices?
- **Current proposed default:** Report A01/A06 require later permission for revisions/SQL/tests; current scope creates register only.
- **Alternatives and consequence of each choice:** Later bounded preparation approval: permits exact artifacts, no execution/history/deploy. Early schema-only scaffolding: requires explicit bounds, no baked-in default or workflow activation. Defer: no executable artifact creation.
- **Recommendation:** Resolve dependent decisions or bound inert scaffolding explicitly and identify versions/branch/artifacts. No executable package is created in this task.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** No; provider evidence/access remain separate.
- **Approval status:** Approval required; no selection/sign-off recorded.

### MH07 - Final graph, IDs and target policy

- **Decision ID:** MH07
- **Exact question:** What final artifact split, dependency graph, IDs/parents and target-policy extension preserve early audit/concurrency guards and independent history approval?
- **Current proposed default:** G01-G09 review order provisional; final early helper/audit split, typed integration, IDs/parents and policy beyond 0040 unapproved.
- **Alternatives and consequence of each choice:** Approve safe early helpers/foundation and staged integration: may require more artifacts than groups. Alternative graph: must keep writers inert until equivalent guards. Defer: no IDs/parents or policy extension. Filenames are not execution order.
- **Recommendation:** Resolve RP07/RP08 and MH05; only then review graph/IDs and policy extension retaining identity/evidence/history guards, never guard removal.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### MH08 - Executable preconditions and verification scope

- **Decision ID:** MH08
- **Exact question:** Which exact schema/data/security preconditions, bounded index/validation phases, rollback/forward-repair rules and separately authorized disposable tests establish readiness?
- **Current proposed default:** Report A04/A05 require privilege/privacy/lock design, additive inert changes, no guessed backfill and explicit disposable-test permission; no tests authorized here.
- **Alternatives and consequence of each choice:** Reviewed bounded additive plan plus later disposable PG17 tests: can prove privilege/conservation/erasure/concurrency/repair behavior. Large existing indexes: separate concurrent build/validation review. Unresolved/untested preconditions: readiness blocked. Data-bearing destructive downgrade or crossing irreversible 0040 not approved.
- **Recommendation:** Approve exact rights/locks/provenance/privacy and typed FK/constraint/nullability/money-bound review, source-sealed artifacts, meaningful tests, backup/recovery and customer/owner refresh evidence. Markdown/mock passes do not satisfy these gates.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** Conditional: local DB tests need no account; separate provider sandbox evidence does.
- **Approval status:** Approval required; no selection/sign-off recorded.

### MH09 - Target execution and coordinated deployment

- **Decision ID:** MH09
- **Exact question:** Which exact target, reviewed artifacts/history transition, preflight evidence and recovery plan may later receive staging execution approval, and what separate API/worker deployment is authorized afterward?
- **Current proposed default:** No execution/deploy approval; target/history/schema/grants/count preflight and coordinated rollout still required.
- **Alternatives and consequence of each choice:** Exact target/artifact/history-specific staging execution approval: allows only scoped action after gates. Separate deployment approval: permits compatible API/worker rollout with server capability checks. Defer either: respective operation held. Other environments/infrastructure never implicitly included.
- **Recommendation:** Keep preparation, reference/test DB writes, provider access, history mutation, staging execution and deployment distinct with hashes, recovery/refresh evidence and immediate target rechecks.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09.
- **Cashfree account required:** No for authorization; provider activation independently needs account evidence.
- **Approval status:** Approval required; no selection/sign-off recorded.

## 6. Redis concurrency decisions

Sources: [G09](09-slot-hold-concurrency-support.md),
[G08](0047-business-closure-reschedule.md) and Q11/Q12/Q15/Q16. RC01/RC03
require product choices; RC02/RC04-RC08 require concrete engineering/security
review. No Redis access or concurrency test occurs in this task.

### RC01 - Healthy/outage admission modes

- **Decision ID:** RC01
- **Exact question:** U05 selects PostgreSQL-only outage/partition fallback; what mandatory/optional healthy-hold policy and operational limits still require approval?
- **Current proposed default / approved scope:** U05 selects SQL-only outage/partition booking fallback and fresh primary availability; healthy-hold requirements remain open.
- **Alternatives and consequence of each choice:** Selected outage fallback preserves eligibility/SQL exclusion without unavailable Redis. Healthy mandatory/optional policy affects fairness/admission and still needs selection. No primary truth means retryable failure, never stale cache success. Requiring unavailable Redis is a superseded outage option.
- **Recommendation:** Keep selected fallback; settle healthy proof/limit and operational parameters under Q12/Q30.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G08, G09.
- **Cashfree account required:** No.
- **Approval status:** Partially approved U05: outage fallback selected; healthy mode/limits and implementation remain open.

### RC02 - Atomic interval/resource representation

- **Decision ID:** RC02
- **Exact question:** Which atomic data structure, Redis key/cluster boundary and conflict algorithm cover differing starts, durations and every resource without partial acquisition?
- **Current proposed default:** G09 proposes one atomic resource boundary, for example one salon hash slot. Exact interval structure/resources/cluster strategy unset.
- **Alternatives and consequence of each choice:** Single-salon atomic resource set: simplifies all-or-none holds, needs reviewed bounds/cluster behavior. Other atomic representation: must prove interval and multi-resource safety. Exact-start SET NX or independent per-resource writes: insufficient for differing intervals/partial failures. Defer: no acquisition implementation.
- **Recommendation:** Choose bounded atomic representation after Q11 resource/buffer scope; SQL supplies candidates/occupied intervals. No permanent hold table or Python availability engine.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G09; G08 resource changes.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### RC03 - Actor limits, renewal and transfer

- **Decision ID:** RC03
- **Exact question:** What per-customer limit/churn controls apply, and are renewal or reschedule-hold transfers allowed under which atomic, expiry and consent rules?
- **Current proposed default:** Five-minute duration confirmed. Actor limit, rate/churn bound, renewal and transfer have no approved numeric/default behavior.
- **Alternatives and consequence of each choice:** No renewal/transfer with explicit actor limit: simpler fairness, fresh attempts needed. Explicit bounded renewal/transfer: needs identity/resource/consent/expiry checks without silently changing confirmed duration. Higher versus lower chosen limit changes abuse/flexibility. Defer: no implicit unlimited holds or rolling renewal.
- **Recommendation:** Product chooses Q12 bounds/renewal with Q11 reschedule policy; engineering reviews atomic enforcement, duplicate same-payload replay and conflicting-payload rejection.
- **Decision owner:** product (proposed; named approver unassigned).
- **Blocking design groups:** G08, G09.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### RC04 - Expiry, cleanup and memory bounds

- **Decision ID:** RC04
- **Exact question:** Which per-entry/container expiry, cleanup/memory bound and backlog/eviction policy prevent stale reservations and false acquisition success?
- **Current proposed default:** Absolute entry expiry/container TTL must agree; atomic expired cleanup and safe bounded backlog refusal proposed. Exact work/memory/recovery values unset.
- **Alternatives and consequence of each choice:** Bounded atomic cleanup/index expiry: limits memory/work with explicit refusal/retry at backlog. Another reviewed bounded structure: must prevent stale indexes extending holds. Unbounded cleanup/memory: no operational bound and not accepted by proposal. Defer: no acquisition enablement.
- **Recommendation:** Specify cleanup/memory/backlog limits, eviction/failover effects and honest unavailable response; later prove expired indexes cannot preserve reservations.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G09.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### RC05 - Proof, API compatibility and privacy

- **Decision ID:** RC05
- **Exact question:** Which token/verifier, actor/payload binding, private namespace, rate limits and version-compatible route/status/error contract govern create, replay, consume and release?
- **Current proposed default:** Opaque scoped proof and atomic compare-and-delete proposed. Exact verifier/key schema, rate limits and final route/status/error mappings unapproved.
- **Alternatives and consequence of each choice:** Minimal token/safe verifier: limits leakage and prevents delayed release deleting new hold. Other secure proof design: requires equivalent actor/resource/privacy review. URL/log tokens, unconditional delete or immutable raw payload excluded. Proposed versus compatible existing API/error mapping changes clients and needs contract review. Defer: no new contract activation.
- **Recommendation:** Approve Q15/Q16 key/namespace and allowlisted ephemeral payload, secure proof transport, authorization, response/retry/conflict and rate-limit rules. Hold never promises booking.
- **Decision owner:** security (proposed; named approver unassigned).
- **Blocking design groups:** G09; G08 hold-assisted requests.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

### RC06 - Commit, replay and invalidation

- **Decision ID:** RC06
- **Exact question:** Which durable replay and cleanup/invalidation protocol handles crash after commit, consumed/expired holds, independent workers and delayed messages without duplicate booking or lost state?
- **Current proposed default:** SQL commits before best-effort hold cleanup/cache invalidation; durable replay returns original booking independent of hold expiry. Exact orchestration/recovery unset.
- **Alternatives and consequence of each choice:** Durable commit plus scoped retry/outbox cleanup: may leave temporary stale hold until cleanup/expiry while preserving booking. Other recovery: must prove same committed result across workers and no reopening occupied slot. Redis cleanup alone cannot prove SQL commit. Defer: no hold-integrated writer activation.
- **Recommendation:** Specify cross-process invalidation, crash recovery, same-key payload conflict and original-command replay; no Redis I/O inside SQL row locks or new booking key after uncertain result.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G08, G09; G01 replay integration.
- **Cashfree account required:** No.
- **U04 scope:** Cancellation joins the shared lock and fresh-snapshot booking protocol. Its occupancy ceases at commit, without waiting for refund or Redis TTL. Q27/Q28 define state/audit/invalidation/notification review. Stale negative caches and an orphan cancelled-generation hold cannot hide a released candidate; delayed cleanup must preserve newer valid holds. Every booking still revalidates SQL/exclusion.
- **U05 disposition:** Durable database outbox, lease/fenced retry/dead-letter/audited repair and PostgreSQL fallback are the reviewed recovery contract. Numeric budget/access/storage remain Q28/Q30; cancellation-versus-hold/payment outcome analysis is in specification section 4.5.
- **Approval status:** Partially approved U05 contract; concrete implementation and runtime evidence remain open.

### RC07 - Canonical SQL and buffer integration

- **Decision ID:** RC07
- **Exact question:** Which canonical helpers, schedule UPDATE guards, approved buffer/resource representation and legacy-writer changes enforce final booking/reschedule eligibility without lock inversion?
- **Current proposed default:** G09 integrates schedule intersection, access/duration/resources and UPDATE closure guards with G08/shared locks. Q11 values and exact helper/exclusion extension pending.
- **Alternatives and consequence of each choice:** Reuse unchanged occupied range plus reviewed guards: preserves existing overlap while improving intersection/update checks. Approved buffer/resource extension: requires conflict scan, legacy treatment and index/constraint build/mixed-writer review. Unresolved values/resources: dependent availability/reschedule stays blocked. Redis cannot replace SQL exclusion.
- **Recommendation:** Resolve Q11/RP07/RP08; preserve pending/confirmed/checked_in exclusion, frozen duration and staff compatibility. Failed approval preserves original slot. Review early helper split even though G09 is last in review order.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G01-G09 shared-lock activation; G08/G09 availability.
- **Cashfree account required:** No.
- **U04 scope:** Cancellation joins the shared lock and fresh-snapshot booking protocol. Its occupancy ceases at commit, without waiting for refund or Redis TTL. Q27/Q28 define state/audit/invalidation/notification review. Stale negative caches and an orphan cancelled-generation hold cannot hide a released candidate; delayed cleanup must preserve newer valid holds. Every booking still revalidates SQL/exclusion.
- **Approval status:** Approval required; no selection/sign-off recorded.

### RC08 - Erasure cleanup and concurrency proof

- **Decision ID:** RC08
- **Exact question:** What scoped erasure retry/fallback and separately authorized independent Redis/database evidence are required before holds may activate?
- **Current proposed default:** Scoped hold/cache/replay cleanup needs reviewed erasure and durable retry on unavailable Redis. TTL alone not erasure proof. No tests authorized here.
- **Alternatives and consequence of each choice:** Verified scoped cleanup with durable retry: accountable privacy completion without flushing unrelated data. Alternative approved fallback: must prove expiry/access barrier and accurate erasure state. Deferred proof: activation unproved/blocked. Future independent outage/failover/multi-worker/DB tests need distinct permission; mock checks insufficient.
- **Recommendation:** Approve scoped erasure/handoff and future evidence for expired-token release, interval/resource overlap, outage/failover, crash, deletion, independent transactions and legacy-lock inversion. Do not report cleanup complete without confirmation.
- **Decision owner:** engineering (proposed; named approver unassigned).
- **Blocking design groups:** G09; G01-G08 participating erasure/locks.
- **Cashfree account required:** No.
- **Approval status:** Approval required; no selection/sign-off recorded.

## Final technical approval defaults - recommendations only

Proposal package TP01, prepared 2026-10-19 (Asia/Calcutta). **All ten TA items
are Approval required.** This is a cross-category review package linked to the
existing Q/P/L/RP/RC decisions, not a seventh design group or a new approval.
No TA approver, approved selection, effective version/date, rollout environment,
legal retention entitlement or service configuration is recorded. A previously
selected aligned business restriction remains historical evidence; inclusion in
this package does not approve the added technical choices. In particular,
owner-to-admin approval and the supplied numeric defaults remain proposals.

The [specification section 13.5](../../verification/payment-subscription-booking-spec.md#135-final-technical-approval-defaults---recommendations-only)
defines retry counting/lease safety and distinguishes outbox, dedup and financial
audit retention. Every entry below preserves recommendation versus approval.

### TA01 - Checked-in monetary remedy

- **Decision ID:** TA01
- **Exact question:** What cause-specific checked-in refund/partial-service/payout remedy, evidence and fund restrictions may be selected without automatic customer timing penalties?
- **Current proposed default:** Manual finance/legal remedy review; restrict affected captured funds from new payout while undecided. Reserve/dispatch only an explicitly approved, capture-capped refund asynchronously. No automatic zero/full refund, customer late penalty, 70/30 payout or bank debit. No monetary amount recommended without cause/partial-service policy.
- **Alternatives and consequence of each choice:** Known approved remedy: reserves and async delivery follow immutable capture caps. Unknown remedy/manual review: prevents arbitrary refund or income but needs case ownership. Any full/partial/other lawful remedy changes customer entitlement and funding; no amount is selected here.
- **Recommendation:** Use the proposed default only after explicit scoped approval; Approval required: Q29/Q17/Q19/Q25/Q26/L01-L03.
- **Decision owner:** product (proposed; named reviewer/approver unassigned).
- **Blocking design groups:** G01-G04; G08/G09 state integration.
- **Dependencies:** Q29/Q17/Q19/Q25/Q26; L01-L03.
- **Cashfree account required:** No for policy; actual fee/funding/refund evidence needs separately authorized provider review.
- **Approval status:** Approval required; recommendation only, no selection/sign-off recorded.

### TA02 - Owner/admin cancellation authority

- **Decision ID:** TA02
- **U06 status:** **Rejected.** The owner-to-admin approval gate is not adopted; the owner cancels directly with a reason and notification, and an admin reviews afterwards (U06 A1). Customer cancellation after check-in stays forbidden (U05).
- **Exact question:** Approve or replace the proposed checked-in authority matrix: customer forbidden, owner request requires admin approval, admin cancellation requires reason/audit; what exact scopes and stages apply?
- **Current proposed default:** Customer cancellation after check-in forbidden; owner submits a reasoned request requiring scoped admin approval before actual cancellation. Admin cancellation/approval requires reason and atomic audit; no new staff or finance grant. Request alone leaves booking checked_in/occupied until valid approved cancellation commits.
- **Alternatives and consequence of each choice:** Owner-to-admin gate adds independent control and latency. Existing U05 scoped owner/admin evidence does not approve that additional gate; any alternative needs explicit authority/consent review. Neither role name nor requester payload grants permission. Request alone does not cancel/release.
- **Recommendation:** Use the proposed default only after explicit scoped approval; Approval required: extra admin gate and exact scopes/stages/independence Q20/Q27; prior U05 restriction is preserved as evidence, not approval of this package.
- **Decision owner:** security (proposed; named reviewer/approver unassigned).
- **Blocking design groups:** G01, G03, G08, G09.
- **Dependencies:** Q20/Q27; Q13/RP03.
- **Cashfree account required:** No.
- **Approval status:** Approval required; recommendation only, no selection/sign-off recorded.

### TA03 - Retry count/backoff

- **Decision ID:** TA03
- **U06 status:** **Approved** as proposed (five retries after the first dispatch, delays 1m/5m/30m/2h/12h). Jitter, age budget and timeout classification remain Q30.
- **Exact question:** Approve five retries after initial dispatch with 1m/5m/30m/2h/12h delays, or choose another bounded attempt interpretation/schedule including jitter and age budget?
- **Current proposed default:** Five retries after the initial dispatch, with delays 1m, 5m, 30m, 2h, 12h from the preceding failed attempt. Proposed interpretation is up to six total dispatch attempts, not five total. Permanent validation errors may dead-letter earlier.
- **Alternatives and consequence of each choice:** Proposed five retries gives six possible dispatches, with durable attempt accounting and finite load. Five total attempts would require a different explicit schedule. Other bounded delays change recovery latency/load; timeout/lease reclaim cannot reset budget. No schedule becomes a runtime default without selection.
- **Recommendation:** Use the proposed default only after explicit scoped approval; Approval required: Q30 must confirm retry-count interpretation, failure accounting, jitter/age budget and timeout classification.
- **Decision owner:** engineering (proposed; named reviewer/approver unassigned).
- **Blocking design groups:** G03, G08, G09.
- **Dependencies:** Q28/Q30; RC06.
- **Cashfree account required:** No.
- **Approval status:** Approval required; recommendation only, no selection/sign-off recorded.

### TA04 - Outbox lease

- **Decision ID:** TA04
- **U06 status:** **Approved** as proposed (five-minute fenced lease). Renewal/heartbeat and clock rules remain Q30.
- **Exact question:** Approve a five-minute fenced database delivery lease; which timeout, renewal/heartbeat, reclaim and stale-worker rules apply?
- **Current proposed default:** Five-minute lease per delivery claim, database time and fencing identity. No booking/payment row locks during external I/O; stale worker cannot acknowledge or overwrite a new lease.
- **Alternatives and consequence of each choice:** Five minutes bounds reclaim delay but may expire during slow I/O; idempotent effects and fenced acknowledgement remain necessary. Shorter/longer lease changes reclaim/duplicate-delivery exposure. Renewal requires explicit protocol and cannot be inferred from duration. No business-row locks span network I/O.
- **Recommendation:** Use the proposed default only after explicit scoped approval; Approval required: timeout/heartbeat/renewal, crash reclaim and clock details Q28/Q30.
- **Decision owner:** engineering (proposed; named reviewer/approver unassigned).
- **Blocking design groups:** G03, G08, G09.
- **Dependencies:** Q28/Q30; RP07/RC06.
- **Cashfree account required:** No.
- **Approval status:** Approval required; recommendation only, no selection/sign-off recorded.

### TA05 - Dead-letter

- **Decision ID:** TA05
- **U06 status:** **Approved** as proposed (dead-letter after a permanent error or exhausted retries; audited requeue). Error classification and requeue bound remain Q30.
- **Exact question:** Approve durable dead-letter after permanent error or exhausted retry budget with retained evidence, alerting and audited original-job repair; what classifications and requeue bounds apply?
- **Current proposed default:** Durable retained failed-delivery state on retry exhaustion or permanent error, with attempt/source history and alert. Stop automatic poison-job retries; continue primary fallback and financial reconciliation. Audited repair/requeue uses original logical identity; dead-letter is not completion or deletion.
- **Alternatives and consequence of each choice:** Early poison-error dead-letter reduces repeated failure but requires operator response. Exhaustion dead-letter stops bounded automatic replay while SQL fallback continues. Repaired bounded requeue preserves original identity/history. Dropping jobs or calling dead-letter successful cleanup is excluded; no endless silent manual cycle.
- **Recommendation:** Use the proposed default only after explicit scoped approval; Approval required: classification, repair/requeue budget and evidence Q28/Q30.
- **Decision owner:** engineering (proposed; named reviewer/approver unassigned).
- **Blocking design groups:** G01, G03, G08, G09.
- **Dependencies:** Q28/Q30; Q24/L05.
- **Cashfree account required:** No.
- **Approval status:** Approval required; recommendation only, no selection/sign-off recorded.

### TA06 - Alert targets

- **Decision ID:** TA06
- **Exact question:** Approve Sentry plus admin email as alert targets; which recipients, sanitized fields, dedup/escalation, response and channel retention rules apply?
- **Current proposed default:** Sentry plus admin email for dead-letter and recovery incidents; sanitized job/source IDs, failure class and correlation only. Neither channel receives credentials, hold tokens, bank details or raw payloads.
- **Alternatives and consequence of each choice:** Two alert channels improve response paths but require access/data-minimization and independent failure handling. Another approved route changes operations responsibility/coverage. Neither channel is durable job truth; failed alert delivery cannot silently resolve the incident. No addresses/projects or numeric response target selected.
- **Recommendation:** Use the proposed default only after explicit scoped approval; Approval required: recipients/on-call routing, escalation/dedup/response targets, channel data retention and delivery Q20/Q24/Q30. No Sentry project or address is configured.
- **Decision owner:** engineering (proposed; named reviewer/approver unassigned).
- **Blocking design groups:** G01, G03, G08, G09.
- **Dependencies:** Q20/Q24/Q30; L05.
- **Cashfree account required:** No; no monitoring/email service access is authorized.
- **Approval status:** Approval required; recommendation only, no selection/sign-off recorded.

### TA07 - Repair authorization

- **Decision ID:** TA07
- **U06 status:** **Changed and approved:** a single super-admin with `aal2` may perform emergency repair, with a reason, an approval record and a complete audit trail. The proposed two-person approval is not required. Repair scope limits (targeted invalidation, canonical rebuild, original-job requeue; no refund or transfer initiation, financial edit, global flush or cancellation reversal) are unchanged and not relaxed.
- **Exact question:** Approve scoped finance/admin repair access with two distinct-person approval; which named permissions, proposer/approver/executor independence and emergency controls apply?
- **Current proposed default (superseded by the U06 status above):** Scoped finance/admin repair access with two-person approval by distinct current authorized people; no self-approval. Repair limited to targeted invalidation, canonical rebuild and original-job requeue; no refund/transfer initiation, financial edits, global flush or cancellation reversal.
- **Alternatives and consequence of each choice:** Two-person control reduces unilateral repair risk, adds response latency. An alternative scope/stage model requires explicit security approval, not implicit break-glass. Repair may requeue/invalidate only; it cannot approve payouts, alter final facts or use provider credentials. No self-approval or role-wide rights inferred.
- **Recommendation:** Use the proposed default only after explicit scoped approval; Approval required: named permissions/actors, separation of proposer/approver/executor, MFA, emergency procedure and limits Q13/Q20/Q30. Role label alone grants no access.
- **Decision owner:** security (proposed; named reviewer/approver unassigned).
- **Blocking design groups:** G01, G03, G08, G09.
- **Dependencies:** Q13/Q20/Q28/Q30; RP01/RP03.
- **Cashfree account required:** No; repair scope excludes provider operations.
- **Approval status:** Approval required; recommendation only, no selection/sign-off recorded.

### TA08 - Outbox retention

- **Decision ID:** TA08
- **U06 status:** **Approved** as proposed (90 days from resolution for resolved operational outbox rows). Unresolved-job and legal-hold exceptions remain open; this does not set the financial audit period (TA09).
- **Exact question:** Approve 90-day retention from delivered/verified-superseded resolution for operational outbox evidence; what unresolved-job/hold exceptions, cleanup and dedup/backup rules apply?
- **Current proposed default:** 90 days for successfully delivered or verified superseded operational delivery evidence, measured from that terminal resolution, not creation. Unresolved/dead-letter/legal-hold items require restricted exception review, not automatic 90-day disposal or unbounded retention.
- **Alternatives and consequence of each choice:** Resolution-based 90 days retains completed operational evidence without prematurely aging open work. Creation-based deletion could lose obligations and is not the proposal. Another finite lawful window changes operational traceability/storage. Unresolved/dead-letter exceptions require named review and minimized lawful handoff, not automatic deletion or indefinite exemption.
- **Recommendation:** Use the proposed default only after explicit scoped approval; Approval required: start clock, lawful basis, cleanup/erasure, backups, open-obligation exceptions and dedup continuity Q16/Q24/L05. No new financial-row hard-delete permission.
- **Decision owner:** legal (proposed; named reviewer/approver unassigned).
- **Blocking design groups:** G01, G03, G08, G09.
- **Dependencies:** Q16/Q24/Q28; L05.
- **Cashfree account required:** No.
- **Approval status:** Approval required; recommendation only, no selection/sign-off recorded.

### TA09 - Financial audit retention

- **Decision ID:** TA09
- **Exact question:** What separate finite financial-audit retention schedule, lawful purpose, hold/review and per-field scrubbing/destruction rules apply?
- **Current proposed default:** Separate finite legal/finance-approved schedule by field/purpose; preserve necessary accounting/source facts and minimize/scrub identifying details under reviewed erasure. No numerical audit duration proposed; do not inherit 90-day outbox window.
- **Alternatives and consequence of each choice:** Approved restricted necessary facts preserve financial evidence with finite access/destruction duty. Demonstrated anonymization reduces identifying retention while preserving conserved facts/source. No numeric period is proposed or inherited from outbox; unresolved law/hold policy blocks privacy-dependent enablement.
- **Recommendation:** Use the proposed default only after explicit scoped approval; Approval required: lawful duration, holds/reviews, actor/reason evidence, access and destruction Q16/Q24/L02/L05.
- **Decision owner:** legal (proposed; named reviewer/approver unassigned).
- **Blocking design groups:** G01-G09.
- **Dependencies:** Q16/Q24; L02/L05; all field classifications.
- **Cashfree account required:** Conditional only for provider-reference necessity; no account needed to draft legal schedule.
- **Approval status:** Approval required; recommendation only, no selection/sign-off recorded.

### TA10 - Encryption/key-management storage

- **Decision ID:** TA10
- **U06 status:** **Design approved only:** Google Cloud KMS and Secret Manager. No resource creation, region, access grant or rotation is authorized; those need a separate approval.
- **Exact question:** Approve or replace the managed envelope/tokenization storage proposal; which KMS/secret-store products, regions, wrapping/decryption authority, rotation, recovery/destruction and old-copy treatment apply?
- **Current proposed default:** Managed authenticated envelope encryption or adequate provider tokenization; encrypted restricted payload and key/version reference in database, wrapping/master keys in separately managed KMS, provider/application secrets in a managed secret store. No plaintext payout credentials, raw keys or secrets in tables, Git, logs, outboxes, cache, replay or backups.
- **Alternatives and consequence of each choice:** Managed envelope encryption separates wrapping keys from database ciphertext but needs key access/rotation/recovery design. Adequate provider tokenization reduces local secrets but needs verified capability and lawful reference handling. Keys/secrets stored with ciphertext or in logs/Git/outbox are not accepted alternatives. No specific product, rotation period or key is selected.
- **Recommendation:** Use the proposed default only after explicit scoped approval; Approval required: concrete KMS/secret/tokenization products, region, access/decryptors, rotation, key recovery/destruction, backup handling and plaintext transition Q15/P04/L05. No key/credential access or service provisioning.
- **Decision owner:** security (proposed; named reviewer/approver unassigned).
- **Blocking design groups:** G01-G09 where sensitive evidence/keys are used.
- **Dependencies:** Q15/P04; Q16/Q24/L05.
- **Cashfree account required:** Conditional: local encryption design no account; tokenization/provider destination claims need P04.
- **Approval status:** Approval required; recommendation only, no selection/sign-off recorded.

No executable defaults are supplied by this document. Before activation, each
TA approval must name selected values, reviewers/evidence, access scopes and
independence, effective version/environment, legacy/open-job treatment and legal/
provider/security conditions. TA08 does not approve a financial-row hard delete
or loss of required dedup identity; TA09 has no numerical retention default.
TP01 records recommendations only and changes no U01-U05 approval evidence.

## Unresolved blockers

- TP01: U06 approved TA03, TA04, TA05 and TA08 as proposed, changed TA07 to a single
  super-admin with `aal2`, rejected TA02, and approved the TA10 design only. Still
  **Approval required**: TA01 checked-in monetary remedy, TA06 alert targets, TA09
  financial audit retention period and TA10 resource creation. No values are activated.

- U05 resolves customer denial after check-in, mandatory scoped owner/admin
  reason/audit, duplicate-effect protection, durable invalidation outbox and
  PostgreSQL-only Redis-outage fallback. Those directions are not left pending.
  Q27 exact permissions/consent, Q28 concrete storage/fencing/key inventory,
  Q29 checked-in monetary remedy and Q30 numeric retry/lease/dead-letter/repair
  authority remain open, alongside RP07 exact ranks and independent runtime proof.
- Cancel/booking/hold/payment race protocols are defined; final state guards,
  economic-source uniqueness and SQL exclusion still require later implementation
  and cross-connection evidence. No reviewed diagram/prose establishes tested
  exactly-once network processing or globally atomic PostgreSQL/Redis holds.
- U03 selects all four cancellation bands and exact 48/12/4-hour boundaries. U06
  selects the percentage base (captured amount before provider fees), the 70/30
  split of the retained pool after provider costs, and the shortfall and residual
  rules; U07 selects the hold formulas. Still **Approval required**: the exact flat
  fee in INR (Q25), caps and partial or unpaid captures, tax components, reserve and
  true-up for unknown fees, and dispute scope and release.
- U03 selects start-passed plus ten-minute grace, explicit owner/staff no-show
  confirmation, actor/time/reason, customer notification and no silent cancellation.
  U06 selects the no-show money treatment (under-4-hour). Staff earning on no-show
  remains unapproved. Confirmer scope, race/appeal/correction and notification
  failure handling need Q02 review.
- No policy rollout/open-order adoption or retrospective rewrite is authorized.
  Remaining business/admin/offer/privacy questions, P01-P06, L01-L05, all 43
  field treatments, new-field classification and RP/MH/RC gates remain open.
  Unknown retained funds/fees are not guaranteed payable or recognized income.
- U01 non-conflicting ordinary service/lifecycle/security scopes remain recorded;
  no ordinary completion hold is fabricated for cancellation/no-show. Existing
  money and erasure obligations remain owned; no database/provider/runtime proof
  or new authorization follows from this documentation approval.

## Recommended approval order

This is a review sequence, not execution authorization. Independent legal,
provider and history reviews can proceed in parallel only within their separately
authorized access/preparation scope. This task starts none of those operations.

1. Assign named product, finance, legal, security and engineering reviewers;
   review L01-L05, P01-P06 evidence requirements and MH01-MH03 local proof plan.
   Triage needs no account or database. Fresh metadata/reference construction
   and provider sandbox evidence require separate authorization.
2. Complete remaining Q01-Q05/Q08/Q14/Q16 subdecisions with L01-L03 and
   evidenced P01/P02/P05/P06: Q25/Q26/Q17/Q19 first (U03 bands already selected), then legal terms and cause-specific fees,
   dispute governance, lawful funding and recovery. Retain non-conflicting historical selections without importing superseded penalty allocations;
   provider selection still waits for actual account evidence.
3. Complete Q19-Q22 hold/authority/projection/offer rules and remaining
   lifecycle Q06-Q09 and staff Q10/L04 details, then
   availability/hold policy Q11-Q12/RC01/RC03 and U05 Q27-Q30/RC06. State/role
   and cache-recovery design approval cannot defer database release after a valid commit. U01's no-cap calendar trial,
   seven-day restrictions, existing completion and cancelled-service exclusion
   are selected; timing, formulas, receipt permissions and legacy treatment are not.
4. Complete Q13-Q16/Q24/Q29/Q30, RP01-RP08, L05-F01 through L05-F43 and all new-field
   treatment: authority/bootstrap, encryption/retention, handoff, stable identities
   and exact locks. Complete RC02/RC04-RC08 and P03/P04 schedules/destinations;
   revisit earlier choices when evidence makes them infeasible.
5. Complete MH01-MH05 acceptance under separately authorized proof work; approve
   MH07 final graph/guard design. Review G01 through G09 with applicable common
   concurrency guards required from the first writer. Review order permits no
   interim unsafe activation, and numeric filenames assign no execution order.
6. Only later consider bounded MH06/MH08 executable preparation and disposable
   verification. After reviewed artifacts/evidence exist, require distinct
   history-mutation, target execution, provider activation and coordinated deploy
   approvals under MH05/MH09. None is part of maintaining this register.

## Recording an approval

For each decision and applicable field, record exact selected option/values,
named authorized approver/function, evidence/reference, effective version/date,
scope/environment, legacy/open-operation treatment, required legal/provider/
security evidence and remaining conditions. Rejection requires an explicit
replacement or continued block. A parent Q/L approval cannot silently select
unresolved subdecisions. Provider verification names account scope/environment,
source integrity and verifier; legal holds name valid basis and review/end.
A policy approval, provider confirmation and execution approval are different
records. This register is not an execution manifest or a new retention exception.

## Owner finance decisions F01-F12 (user, 2026-10-29)

Recorded as given by the product owner. **Do not ask these again** unless a later decision
conflicts. They answer the open questions in `finance/FINANCE_PHASE0_DISCOVERY.md` section 9 and
the assumptions in `finance/FINANCE_PHASE1_DESIGN.md` section 0, and where they differ they win.

| ID | Decision | Status |
| --- | --- | --- |
| F01 | **Amounts in paise.** All financial amounts are whole integer paise. 1 rupee = 100 paise. | Approved |
| F02 | **Internal fields are never shown.** Platform/salon allocation, gateway fees, Cashfree fees and internal platform percentages are never shown to salon owners or staff. Staff never see commission rules or other staff's earnings. The owner sees and configures a staff commission rule only inside a restricted Staff Earnings / Commission Settings area. The Daily Ledger and Analytics show only salon-operational totals, and staff earned amounts where permitted. | Approved (changed from the recommendation) |
| F03 | **Opening cash.** First ledger day: the owner enters it once. Later days: it is the previous closed day's counted cash. If the prior day was not closed the system must **not** assume zero or carry forward silently: the owner confirms or reconciles it. Any later correction is an audited adjustment with a reason. | Approved |
| F04 | **Who writes.** Salon owner only. Staff and salon managers cannot add expenses or close or reopen a day. A platform super-admin may audit records where authorized but must not create or alter a salon's ledger entries through the owner workflow. | Approved |
| F05 | **Plan access.** Trial, Growth and Premium all get the Daily Ledger and Staff Earnings. Premium-only remains for SMS alerts. When a trial or subscription ends the salon keeps read-only access to past finance records and every financial write is locked. | Approved |
| F06 | **Retention after account deletion.** Requires accountant/legal input. No duration is invented. Personal identity is erased or anonymized where approved; necessary financial evidence is kept only for the required period. **The purge design stays blocked until the user supplies the period.** | Approval required |
| F07 | **Commission precedence.** 1 staff + specific service, 2 staff-wide, 3 service-wide, 4 salon default, 5 no rule = zero commission. The selected rule is snapshotted when the service completes; later rule changes never rewrite past earnings. | Approved |
| F08 | **SMS feature name.** Keep `sms_alerts`. Premium-only through subscription entitlement. Do not rename it to `premium_sms_alerts`. | Approved |
| F09 | **WhatsApp.** Not approved and out of scope. Build SMS alerts only; send no WhatsApp message to customers. It needs separate customer consent, provider review, template approval, cost/quota and privacy wording, and a separate future decision. It does not count toward the 300 monthly SMS quota because it is not being built. | Not approved |
| F10 | **Changing a service's staff.** Only before the service is completed. After completion the original allocation is never edited: a genuine correction is an audited earning adjustment/reversal plus a replacement record. | Approved |
| F11 | **Expired trial or subscription.** The owner keeps read-only access to historical Daily Ledger and Staff Earnings. No new expenses, payment receipts, day close, commission changes or financial edits while access is expired. Prior records are never deleted or hidden because a subscription ended. | Approved |
| F12 | **Cash refunds.** A generic "cash adjustment out" is not the long-term refund workflow. A proper `Cash Refund` action/financial event must be built before any public refund workflow launches: linked to the original booking/receipt, with amount, actor, timestamp, reason and audit history. Until it exists a generic adjustment must not be presented as a customer refund and stays restricted to audited internal corrections. | Approved (changed from the recommendation) |

What these changed in the build (2026-10-29): migration 0051's owner routes now allow reads after
a plan ends and refuse every write (F05, F11); the daily ledger reports `can_write`; opening cash
needs owner confirmation when the previous day is unclosed (F03); the dormant WhatsApp
"service completed" message code and its setting were removed (F09); the adjustment sheet no
longer mentions customer refunds (F12). Not yet built: staff earnings and commission settings
(F02, F07, F10), the Cash Refund event (F12) and the retention purge (F06).

### F13 - Owner expense book is local-first (recorded 2026-10-29)
- The owner types their own expense name; entries are kept on the phone and synced to the backend in
  batches (client id is the idempotency key). The backend stays the financial authority.
- Header totals on the Expenses tab are expenses only; the app sums nothing (server month summary).
- Cancelling an expense is dated on the original day, so it never disturbs another day's cash.
- Auto-repeat rules are a later phase (E4). Migration 0051 was edited in place because it had never
  been applied anywhere; see FINANCE_PHASE2_IMPLEMENTATION.md.

### F14 - Repeating expenses (recorded 2026-10-29)
- The owner can make an expense repeat daily, weekly or monthly. The rule lives on the server so every
  phone sees it; it is never edited (stop it and make another).
- Each due day is saved by the phone as an ordinary expense with a fixed id, so it can be cancelled like
  any other and never comes back. Setting up or stopping a repeat needs the internet; recording due days
  does not. The server refuses any day a rule does not allow.
- Missed days are filled in for up to 31 days back when the app opens.

### F15-F18 - Staff earnings (S1) answers (recorded 2026-11-01)
- **F15 Fixed commission above the price:** capped at the service's price. A rule is never refused for this.
- **F16 Who did each service:** the customer app keeps one barber per booking (service chosen first, the barber
  free soonest is the default, the customer may pick another and sees that barber's times). Per-service
  attribution defaults to the booking's barber; the owner may change it before the service is completed;
  after completion only an audited correction (F10). No customer-app or availability change in S1.
- **F17 Where rules live:** Finance, Staff earnings (owner only), with a Commission settings button.
- **F18 Paying staff:** the app records when the owner pays a staff member their commission ("Mark as paid"), so the
  owner sees earned, paid and still owed. Open design points to settle before building it: part payments,
  corrections (append-only), and whether a cash payment reduces the expected drawer cash.

## Verification boundary and stopping point

Only local Markdown links/anchors, section/decision/field numbering and whitespace
are checked for the five changed Markdown files. No app imports, pytest, lint, SQL validation, revision
graph checks, databases/Redis/provider access, credentials, migrations/stamping,
infrastructure operations, deployment, commit or push are performed. Existing
reconciliation evidence, executable artifacts and user code changes are preserved.
Only the specification, this register, cancellation, G09 concurrency and G08
availability/closure-reschedule design Markdown change;
no code, database or infrastructure is changed by this task. Stop here.
