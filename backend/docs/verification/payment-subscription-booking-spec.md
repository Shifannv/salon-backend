# Payment, subscription and booking domain specification

Revised: 2026-10-19 (Asia/Calcutta)

Status: Documentation risk review U05 with recommendation-only technical package TP01. Explicit U01/U02 business approvals recorded; remaining decisions, provider/legal evidence and implementation remain held.

Scope: shared FastAPI backend only. This document neither implements behavior nor authorizes migration execution, provider activation or deployment.

## 1. Evidence and change boundaries

Phase 0 inspected repository source and Mumbai project `wqjlgpnbiapcrlkxumcp` metadata. Those observations are evidence from that phase, not fresh database verification in Phase 1:

- Repository graph: 40 linear Alembic revisions; source head `0040_fastapi_only_access`.
- Portable migration test target: `0037_customer_processing_charge`.
- Mumbai `public.alembic_version`: zero rows despite a populated restored schema. Four separate Supabase restore/hardening history entries exist. Schema presence does not establish Alembic execution history.
- All 44 public tables have RLS enabled; no explicit public-table grants to `anon`/`authenticated` were found. This is not a complete effective-privilege or ownership proof.
- Cashfree code exists with mock-transport evidence only; real provider behavior is unverified. Defaults keep it disabled. Runtime secrets/settings were not inspected.

Existing contracts and implementation references: [payments](../PAYMENTS.md), [payment decisions](../PAYMENT_DECISIONS.md), [booking flow](../BOOKING_FLOW.md), [subscriptions](../SUBSCRIPTIONS.md), [authorization](../AUTHORIZATION.md), [account deletion](../ACCOUNT_DELETION.md), [migration policy](../migrations/MIGRATION_POLICY.md), and [Mumbai reconciliation](../migrations/MUMBAI_FORWARD_RECONCILIATION.md). Historical statements in those documents are not approval for conflicting future behavior.

This documentation update revises this specification, the approval register and directly affected migration design Markdown only. No application code, tests, executable migrations, environment files or session-memory files may change. No SQL, Alembic upgrade/stamp, provider calls, commits, pushes or deployments are authorized. Sydney, production, VM, DNS and frontend production settings remain excluded. Any future staging execution requires separate approval and synthetic data only.

## 2. Decision classification and confirmed rules

Section 2.1 records owner-approved target requirements, including U01 direction recorded 2026-10-18 and U02/U03/U04/U05 recorded 2026-10-19 in the [approval register](../migrations/payment-subscription-booking-designs/APPROVAL_REGISTER.md). U03 selects the current cancellation bands and no-show process, reopening every penalty recipient; U01/U02 remain historical approval evidence where superseded. Historical policies and already-bound obligations never change. Approval of a target does not prove implementation or provider support. Existing behavior is evidence, not approval of its business policy. Section 2.2 contains recommended defaults awaiting approval; section 2.3 requires Cashfree confirmation; section 2.4 requires legal/accounting review. Every unconfirmed choice is labeled **Approval required**. No response, elapsed time, example or suggested number supplies approval.

Sections 3-12 elaborate these classifications. Proposed transitions, API shapes and migration designs remain **Approval required** for implementation review even where they enforce approved invariants. A blocked decision blocks only its dependent new workflow; existing refunds and accounting obligations must still be reconciled under their applicable historical policy.

### 2.1 Owner-approved rules

| ID | Required behavior |
| --- | --- |
| C01 | Customer checkout total equals the snapshotted service/cart total. No additional platform, convenience or gateway surcharge is added to the customer total. |
| C02 | Platform commission on completed services is exactly INR 0.00. Subscription revenue and cancellation allocation are separate accounting categories. |
| C03 | Store actual gateway fee, gateway-fee GST, Easy Split fee, settlement fee, payout fee and refund fee separately. Estimates never become actuals without provider evidence. No fixed percentage is final truth. |
| C04 | U03 customer cancellation bands use remaining elapsed time before appointment start: at least 48 hours, flat-fee band (amount unresolved); 12 to less than 48 hours, 5% penalty; 4 to less than 12 hours, 35% penalty; less than 4 hours, zero refund. Exactly 48/12/4 hours belongs respectively to flat/5%/35% bands. Exact flat amount, percentage base/refund accounting, penalty recipients, dispute hold and provider fees remain open. Historical policies never change; U02 70/30 is not a default for U03. |
| C05 | Ordinary completed-service payouts require verified activation/vendor/KYC, 48 elapsed hours after recorded service completion (U01), no active dispute, unencumbered funds and unique reservation; paid requires confirmed transfer. U02 permits separately governed cancellation settlement under admin approval/timing, not fabricated service completion. Cancellation hold duration/origin and admin roles remain Q19/Q20 approval required; no new execution is enabled. |
| C06 | Manual and automatic payouts pass the same eligibility evaluator and atomic reservation checks. Manual transfer evidence never bypasses a hold or dispute. |
| C07 | U01: one trial after approved salon activation, lasting two calendar months with no booking cap. Not 60 days; reapproval cannot restart it. Exact calendar/activation and legacy transition remain Q06. |
| C08 | U01: seven-day renewal grace with no new bookings or new booking-payment initiation; existing bookings remain visible and can finish. Subscription renewal checkout remains available. Refunds/disputes/payout history/reconciliation continue. Exact grace calendar/start/trial scope, direct receipt permission and late captures remain Q07; completion still needs applicable collection evidence. |
| C09 | U01: staff commission is internal to salon, based on immutable booking/service/allocation snapshots, never current catalog price. Cancelled bookings earn no service commission. Gross/net basis, rate/rule selection, weights, no-show and reversal/recovery rules remain Q10/L04. |
| C10 | PostgreSQL availability intersects salon hours, staff hours, breaks, holidays, closures, existing bookings, service compatibility, duration, cleanup buffer, minimum notice, same-day cutoff and active/business-open/access state. |
| C11 | Redis holds last five minutes and provide temporary coordination only. PostgreSQL alone commits bookings and enforces overlap protection. |
| C12 | Every admin financial action records actor, authority, reason, affected references, outcome and correlation/idempotency information. Financial corrections append evidence; they do not overwrite the original accounting entry. |
| C13 | Account erasure anonymizes retained financial history without destroying required ledger evidence. Personal identifiers, free text and provider identifiers need explicit retention classification. What can be irreversibly anonymized versus lawfully retained under restriction is **Approval required** (L05/Q16); pseudonymization alone does not prove this target is met. |
| C14 | U01: encrypt/tokenize payout data; never store raw payout credentials in plaintext or expose them in responses/logs/audit/cache/replay. Concrete solution, keys, rotation and old-copy cleanup remain Q15/P04/L05. |
| C15 | Subscription purchases are separate from vendor settlement/payout. No automatic renewal without explicit owner consent. The one-time/manual-renewal launch mode is a recommendation, **Approval required** (D12/Q09). |
| C16 | Owners select payout schedules only from confirmed provider/account capabilities. Admin restrictions apply; weekend availability cannot be promised without evidence. |
| C17 | U02: admin controls cancellation settlement approval and payout timing; manual and automatic paths retain identical eligibility/reservation/finality checks. Concrete roles, stages, holds and scheduling limits remain Q19/Q20. |
| C18 | U02: owner must not receive platform percentage or internal cancellation allocation formula. Permitted proposed projection is eligible amount, payout status, payout date and sanitized admin message; exact allowlist/date semantics require Q21. Filter at backend serialization, including reports/exports/replay/errors; hiding frontend text is insufficient. |
| C19 | U02: admin capability scope includes pending cancellation payouts, salon-level payout history, daily/weekly/monthly sales, online/cash totals, completed/cancelled/no-show totals, subscription revenue, payout status/audit history and custom subscription offers. These are target capabilities, not existing endpoints or approved finance-role grants. |
| C20 | U02: default subscription plan stays unchanged. Salon-specific offers retain original price, discounted price, effective dates, admin actor and reason. Old invoices/subscriptions retain original price; no retroactive price change. Owner receives only final payable price, never internal platform margin. Duration/expiration/purchase binding and authority remain Q22/Q20/Q09. |
| C21 | U02: all financial calculations use integer paise or Decimal, never binary floats. Preserve exact currency conservation, separately recognized provider charges, versioned rounding and immutable historical policy/price snapshots. |
| C22 | U03 no-show requires appointment start to pass, a full ten-minute grace period to elapse, and explicit authorized owner/staff confirmation. Record confirming actor, timestamp and reason; notify the customer. Time passing alone never silently cancels a booking or marks it no-show. Financial treatment is separately unresolved. |
| C23 | U04: once a valid booking cancellation commits, status is cancelled and the cancelled booking immediately ceases to block database availability; the next eligible customer may book the released interval. Redis slot/cache invalidation happens after commit. Refund execution is a separate asynchronous workflow. Canonical PostgreSQL availability and booking revalidation, with unique/exclusion constraints, remain final protection against duplicate booking. Other independent closure/access/booking/resource restrictions still apply. |
| C24 | U05: customer cannot cancel after check-in. An authorized salon owner or scoped admin may cancel checked_in only with mandatory reason and atomic actor/time/state/policy audit. Repeated/concurrent cancellation has one logical outcome, release, refund-planning task and notification intent. No new staff checked-in cancellation right or finance power is implied. Exact scopes and monetary decisions remain Q20/Q29. |
| C25 | U05: cancellation commits independently of Redis availability, with durable database outbox invalidation intent committed in the same transaction. Redis failure uses fresh PostgreSQL availability and SQL-only booking fallback, never stale busy/free cache as authority. Booking always rechecks PostgreSQL and final constraints. Retry/dead-letter/repair must preserve intent and original operation identity; numeric budgets remain Q30. |
| C26 | U05: shared ordered database gates, current state/version validation and final constraints serialize cancellation, booking and verified payment application. At most one conflicting terminal transition and one overlapping active booking commit; retries do not create duplicate effects. Payment facts are recorded even after cancellation without reopening or transferring capture to a replacement booking. Redis holds are advisory, not a globally atomic database reservation. |

### 2.2 Proposals and approval status

Selections below distinguish approved business scopes from unresolved implementation/legal/provider details. No value or recommended option is applied automatically; unset dependent policy remains blocked.

| ID | Recommended default | Status and decision gate |
| --- | --- | --- |
| D01 | U03 supersedes earlier targets for newly governed customer cancellation: flat-fee band at 48 hours or more, 5% from 12 to less than 48 hours, 35% from 4 to less than 12 hours, zero refund below 4 hours. | **Partially approved U03**: bands/rates selected; flat amount, percentage base, refund computation and every recipient remain Q25/Q26, with provider fees Q17 and hold Q19 open. |
| D02 | Earlier full early-refund proposal is superseded for U03 customer cancellation by its tiered penalties; salon-caused/closure refund proposal remains separate. U03 no-show process requires ten-minute grace and owner/staff confirmation with actor/time/reason and notification. | **Partially approved U03**: no-show operational process selected, not no-show money rules, duplicate/excess refunds or salon-caused terms; Q02/L01 remain open. |
| D03 | U03 explicitly places exactly four hours in the 35% band, exactly twelve hours in the 5% band, and exactly forty-eight hours in the flat-fee band. Below four hours has zero refund. Trusted request-received ingress and reschedule start/snapshot remain design proposals. | **Partially approved U03**: boundaries selected; percentage base/net refund and timestamp/legacy/exception governance remain open. No unmarked equality exception is assumed. |
| D04 | U01 selects actual completed-service provider costs reducing salon payout. Nonrecoverable salon-caused full-refund fee bearing remains a platform-borne proposal. U02 net 70/30 pool is historical only; U03 leaves every penalty recipient and provider-fee treatment explicitly unresolved. | **Partially approved**: completion bearer selected; cancellation bearer/base choice Q17, actual pricing P01 and L02/L03 remain open. |
| D05 | U01 selects 48 elapsed hours from service completion and no active dispute for ordinary service payout. | **Approved duration/origin** for completed service; Q19 reopens dispute-hold review for cancellation and asks whether ordinary hold changes. No replacement duration is selected; existing policy snapshots remain unchanged. |
| D06 | U02 authorizes cancellation settlement as a separate admin-controlled business entitlement, never fabricated completed service. | **Partially approved**: capability selected; cancellation hold/origin, scope, final entitlement and roles Q17/Q19/Q20 and L01-L03 block initiation. |
| D07 | U01 selects two-calendar-month trial without booking cap. Local anniversary/month-end clamp/exclusive end and first activation convention remain proposals. | **Partially approved**: no-cap duration selected; Q06 calendar/activation/grandfathering and implementation remain pending; legacy cap columns/data unchanged. |
| D08 | After expiry, permit authorized recording of cash/UPI already received directly for an existing appointment and permit service completion; do not create an online order, collect a surcharge, or make cash payable by the platform. | **Approval required**: Q07. Without this decision, collection-before-completion remains an explicit unresolved compatibility blocker. |
| D09 | U01 selects seven-day renewal grace, no new booking/payment orders and existing completion allowed; subscription renewal remains available. Calendar-day calculation/start instant and no trial grace remain proposals. | **Partially approved**: duration/restrictions selected; Q07 exact timing/trial/receipt/legacy scope remains open. |
| D10 | U01 selects immutable booked snapshots and no cancelled-service commission. Gross booked basis, booking-time rule selection, completion earning, no-show exclusion and proportional reversal remain proposals. | **Partially approved**: Q10/L04 formula, allocation and recovery details still require approval. |
| D11 | Manual and automatic payout use identical eligibility, allocation reservation and reconciliation. Each payout requires an authorized approval record; automation does not waive it. Approval limits, dual approval and who may approve automated batches remain undecided. | **Approval required**: Q13 for authority/automation; common eligibility and confirmation are already approved in C05-C06. |
| D12 | Launch with one-time subscription purchase and manual renewal; display total price before monthly equivalent. | **Approval required**: Q09 for launch mode; no automatic renewal without consent is already approved. |
| D13 | U05 selects fresh PostgreSQL availability and SQL-only booking fallback when Redis/hold coordination is unavailable; report coordination unavailable and never fabricate a hold. | **Approved fallback direction U05**: healthy mandatory-hold policy, numeric limits and operational recovery budget remain Q12/Q30; database access/state/constraint guards stay mandatory. |
| D14 | Use authenticated envelope encryption with separately managed keys or adequate provider tokenization; block payout enablement until existing plaintext exposure is addressed. | **Approval required**: Q15 for key/tokenization solution and rollout; the prohibition on plaintext is already approved. |
| D15 | Reconcile late captures on pre-expiry orders; if the existing booking remains valid, apply funds to that obligation and prevent a second collection. Otherwise retain a refundable obligation pending the approved remedy. | **Approval required**: Q07/Q08/L01; always record verified money movement regardless of expiry. |

Buffer/notice values, on-time/other-cause refund amounts, destination cooling-off, staff weights, retry limits and finance thresholds have no implicit default. U02 explicitly selects zero refund for new late cancellations only. The 48-hour completed-service hold and seven-day renewal grace are separate U01 selections, not cancellation hold approval.

### 2.3 Provider-dependent rules requiring Cashfree confirmation

No Cashfree lookup, sandbox request or live operation occurs in this revision. All rows below are **Approval required** for enabling the dependent integration, plus Cashfree account-specific evidence. Owner approval alone cannot establish provider capability.

| ID | Confirmation required | Evidence needed before enablement |
| --- | --- | --- |
| P01 | **Approval required**: actual gateway/GST, Easy Split, settlement, payout and refund charges; tax-inclusive/exclusive components, refunds of fees, and when/how fees are debited | Approved account pricing and synthetic provider statement/invoice reconciliation; no assumed 3%, 1.95% or tax rate. |
| P02 | **Approval required**: ability to withhold all relevant vendor settlements until completed-service eligibility and dispute hold are satisfied; release, refund and reversal support | Account/product entitlement and sandbox evidence of delayed release. Automatic upstream settlement before eligibility would violate C05 even if our payout row remains pending. |
| P03 | **Approval required**: allowed daily/weekly/monthly schedules, timezone, cutoff, holidays/weekends and admin/owner selection limitations | Confirmed account capabilities and timing evidence; no fixed schedule promise from example names. |
| P04 | **Approval required**: vendor KYC/verification states, encrypted/tokenized destination handling and destination-change effects | Verified account onboarding responses and sandbox synthetic vendor lifecycle. |
| P05 | **Approval required**: payout/refund final confirmation, pending/failure/reversal semantics, stable retry references, webhook signature/event schema and duplicate/out-of-order recovery | Signed sandbox events plus status-query/statement evidence; timeout and request acceptance are not terminal success or failure. |
| P06 | **Approval required**: provider-side split settlement versus separate payout/manual bank transfer product; duplicate-transfer detection and operation funding | Confirm which product/account actually moves funds and its reference/UTR reconciliation. Never pay a bank transfer on top of an already-settled vendor share. |

### 2.4 Legal/accounting decisions requiring review

Each row is **Approval required**, with owner approval informed by the designated legal/accounting reviewer. No statutory duration, GST rate, licensing conclusion or accounting recognition policy is asserted here.

| ID | Review required | Related decisions |
| --- | --- | --- |
| L01 | **Approval required**: customer cancellation/refund terms, four-hour/no-show consequences, dispute rights and notification/consent. An operational 48-hour hold cannot extinguish a later valid dispute. | Q01-Q05, Q07-Q08 |
| L02 | **Approval required**: fee bearer, taxes on each fee and cancellation allocation, invoice issuer, tax inclusion, credit notes and subscription tax treatment. Who books receivables/deficits and how recoveries are authorized. | Q04, Q09, Q16 |
| L03 | **Approval required**: permitted fund flow, provider versus platform custody, hold/reserve arrangement, manual transfer funding and recovery after payout; prevent double funding and unsupported platform-held balances. | Q05, Q13-Q14, Q16 |
| L04 | **Approval required**: staff service commission versus cancellation/time compensation, earning/recognition event, lawful reversal and correction authority, including after payout. | Q10, Q13 |
| L05 | **Approval required**: financial evidence retention periods, pseudonymization versus anonymization, erasure limits, legal holds, provider references, encrypted backups and destruction/access authority. | Q15-Q16 |

### Money vocabulary and invariants

- Currency is INR for this scope. Use integer paise or Decimal with half-up paise rounding where needed; never binary floats. Fixed two-decimal strings in the proposed public contract are **Approval required** for API compatibility review; they are not a new approved serialization rule.
- `service_amount` is the immutable booked/cart price total; `customer_paid_amount` is captured customer funds, excluding unsuccessful authorizations. Partial captures, overcollection and refunds are explicit events, not changes to that price.
- `platform_commission_amount = 0.00` for completed services. A cancellation allocation uses its own named ledger category and policy reference.
- Store `gateway_fee`, `gateway_fee_tax`, `easy_split_fee`, `settlement_fee`, `payout_fee`, `refund_fee`, `salon_net_amount`, and evidence/status for each actual charge. Preserve existing columns where their meaning matches; field names here describe semantics, not a finalized schema.
- Unknown actual fees are null/unknown, not zero. Distinguish estimated, provisional, reconciled, disputed and corrected amounts. Record provider reference, effective time, observation time and allocation basis.
- A provider fee may cover several transactions or already include a component. Reconcile statement totals, allocate deterministically, and count each fee once. Store taxes on non-gateway fee categories separately when reported; do not silently fold them into gateway GST.
- Never use a negative payout, silently clamp a financial shortfall to zero, or erase an unexplained difference. Record a receivable/reserve/adjustment and require a reviewed resolution.
- Mutable payment/payout projections may track current operational status; financial postings and corrections are append-only. A correction references the original entry, reason and actor. Provider observations are deduplicated and preserve effective versus received times.

## 3. Existing behavior requiring compatibility work

| Existing implementation | Required treatment in later phases |
| --- | --- |
| Fixed 5% customer processing charge | Remove for newly governed checkout policies. Preserve historical charge snapshots; decide treatment of already-open quotes/orders before rollout. |
| Cancellation default 120 minutes; late owner approval | Introduce versioned four-hour behavior. U02 assigns new cancellation payout approval/timing to admin; actual roles and legacy request transition remain open. Do not silently replace existing requests. |
| Configurable commission and estimated fee snapshots | New completed-service policy fixes commission at zero. Retain historical amounts and separate provider actuals from estimates. |
| `booking_payments`, refunds, webhook intake, durable idempotency | Extend these foundations; do not introduce parallel payment authority. Existing payment status changes are projections, not sufficient append-only financial accounting. |
| Earnings excludes actual provider costs | Expose provisional versus reconciled net, eligibility, holds and paid amounts separately. Do not label current `online_net` as confirmed payout balance. |
| Payout destination and vendor registration | Reuse onboarding references, but add a real payout lifecycle and capability-based schedules. Destination registration is not payout confirmation. |
| Trial is two calendar months plus 120-booking cap | U01 selects no booking cap for the target policy; calendar/activation/legacy transition and coordinated code changes remain Q06. No current cap data/constraint is changed here. |
| `trialing`, `past_due`, `pending`, `suspended` subscription states | Define a compatibility mapping to proposed customer/owner states; do not rename enums or collapse pending/suspended blindly. |
| Subscription cancellation preserves access until paid period end | This existing behavior concerns subscription cancellation, not a customer cancelling an appointment. Proposed retention is **Approval required** (Q09); do not confuse it with booking cancellation compensation. |
| Staff hours replace salon hours through `coalesce` | Intersect both schedules. Staff with null hours inherit salon hours; explicit closed staff days remain closed. |
| SQL guards and GiST exclusion prevent active overlap | Keep database authority across all booking sources. Align Python lifecycle helpers with checked-in/no-show support. |
| PAY_AT_SALON daily/no-show guards and collection-before-completion | Preserve unless separately changed. D08 proposes recording existing direct receipts after expiry; **Approval required** (Q07). Do not waive collection evidence to force completion. |
| Closure preview/application cancels reviewed overlaps and notifies | Preserve visibility and reviewed affected-set validation. Add reschedule handling without silently cancelling through ordinary settings changes. |

The six owner-requested plan prices are already seeded: Growth INR 349 / 1,499 / 1,999 and Premium INR 599 / 2,499 / 3,499 for 1 / 6 / 12 months respectively. No duplicate seed migration is needed merely to restate these prices. Existing admin edits must not be overwritten without review. Tax inclusion and plan benefits remain **Approval required** (Q09/L02).

## 4. Cancellation allocation and refunds: decision gate

### 4.1 U03 approved cancellation bands and no-show process

U03 (2026-10-19, explicit user instruction) selects the following prospective
customer cancellation bands. Use remaining elapsed time before the bound
appointment start; trusted receipt-time ingress and rescheduled governing start
still need Q03 approval. A later approval timestamp must not silently move a
request into another band.

| Remaining time before start | Approved band | Approval status |
| --- | --- | --- |
| Exactly 48 hours or more | Flat cancellation-fee band | Band selected; exact flat amount Q25 unresolved. |
| 12 hours to strictly less than 48 hours | 5% penalty | Rate/boundaries selected; percentage base, caps, rounding and refund accounting Q25 unresolved. |
| 4 hours to strictly less than 12 hours | 35% penalty | Rate/boundaries selected; exactly four hours belongs here. Net refund amount remains dependent on Q25/Q17. |
| Strictly less than 4 hours, before start | Zero customer refund | Selected; retained-fund recipients Q26, provider fees Q17 and dispute hold Q19 unresolved. |

Exactly 48 hours is flat-fee; exactly 12 hours is 5%; exactly 4 hours is 35%.
The flat band is not zero fee or free cancellation. A percentage penalty is not
platform commission or permission to pay a beneficiary. Do not infer its base
as current catalog price, captured funds or service snapshot until selected.
The four requested open items remain explicit: flat-fee amount, each penalty
recipient, dispute-hold duration and provider-fee treatment. Percentage-base/
refund mechanics are also unspecified; no invented value resolves them.

No-show is a separate operational decision: appointment start must have passed
and the full **ten-minute grace period** must have elapsed before an authorized
owner/staff member may explicitly confirm nonattendance. Record the actual
confirming actor, confirmation timestamp and reason, and notify the customer.
Time alone never marks no-show and never silently cancels. Customer arrival,
check-in/completion, confirmation and cancellation races require revalidation;
no new terminal transition is authorized merely by scheduler expiry. Preserve
state/audit and notification intent together in later design, with durable
notification retry rather than repeating the attendance decision. Reason data
must be sanitized/classified under Q24/L05, not copied into immutable raw logs.
Exact confirmer scope, correction/appeal and notification failure behavior remain
Q02/L01 review. No-show penalty/refund/payout/staff entitlement is not selected
by this attendance rule and cannot inherit the customer-cancellation bands.

### 4.2 Superseded U02 financial branch and historical policies

U03 explicitly leaves **every cancellation penalty recipient unresolved**, even
for below-four-hour retained funds. Therefore prior U02 70% salon / 30% platform
is retained below as historical/conditional arithmetic only, not an approved
allocation for new U03 bookings. Do not automatically pay salon, platform or
staff under it. Q26 must name each band's beneficiary and allocation before
finalization. No-show confirmation itself creates no payout entitlement.
Already-bound historical policies/obligations retain their original rules.

Under historical U02 late policy, customer refund R is **zero** (also selected for U03 below-four-hour cancellation). The full
verified captured amount attributable to the obligation enters cancellation
settlement, with duplicate/excess/previously refunded or uncertain commitments
separately reconciled, never confiscated as a second entitlement. Provider fees
are recorded separately with actual evidence. The requested distributable pool
is captured amount less approved provider costs; salon receives **70%** and
platform **30%**. These are cancellation proceeds, not completed-service commission.

U02 also explicitly asks whether provider costs reduce the pool or are absorbed
by platform. Therefore the net-pool expression is the **current requested branch,
pending Q17 approval**, not a silently finalized fee-bearer rule. Unknown cost is
not zero. Neither branch may finalize before its exact fee/tax categories,
recognition and funding are approved with P01/L02/L03.

Let P be verified eligible captured funds, F deduplicated approved provider costs,
D distributable pool, U platform allocation and V salon allocation. Arithmetic
uses integer paise or Decimal with a versioned half-up paise rule; binary floats
are prohibited. Proposed residual convention: round platform allocation once,
then assign salon the residual; precise rounding allocation remains reviewable.

| Q17 branch | Pool and allocation | Conservation and consequence |
| --- | --- | --- |
| Requested fee-reduced pool; **Approval required** | R=0; D=P-F; U=round(0.30*D); V=D-U. | P=R+F+U+V. Costs reduce both recipients' distributable base; never deduct F from V again. |
| Platform absorbs fees; **Approval required** | R=0; D=P; U=round(0.30*P); V=P-U; platform net=U-F. | P=V+F+platform net. Platform funds its fee shortfall; salon receives 70% of gross pool without another deduction. |

If F is unknown or exceeds the applicable available funds, block distributable
finalization/transfer and record an explicit deficit/funding obligation; do not
silently clamp, invent zero costs, create negative payouts or discard evidence
of money already moved. Fees observed after payout need append-only true-up and
approved recovery, not retroactive mutation of the original entitlement.

Admin controls approval and payout timing. This creates a cancellation settlement
business path, not permission to mark cancelled work completed or bypass KYC,
funding, dispute, reservation, independent evidence or transfer confirmation.
The U01 48-hour clock starts at **service completion**; it cannot run from a
fabricated completion for a cancellation. Q19 must select cancellation hold
origin/duration and Q20 roles/stages before this path may initiate transfers.

Owner projection is limited to eligible amount, payout status, payout date and
sanitized admin message, subject to Q21 exact-field approval. Never expose the
platform percentage or internal formula through owner APIs, reports, exports,
replay/error bodies or notifications. Scheduled versus actual payout date must
be distinguished; a scheduled date is not proof of payment. Admin projections
retain full restricted allocations and audit evidence under authorization.

### 4.3 Other causes and approval dependencies

U02 supersedes earlier U01 refund-first/20%-platform/80%-salon direction for the
new target late policy only. Old policy versions, already-bound bookings,
refund obligations, finalized postings, invoices and prices never change.
Publication/version/effective date, explicit exceptions and open-order adoption
must be approved; do not globally rewrite historical ratios, amounts or quotes.
Corrections append linked events under their original policy authority.

| Cause | Target handling | Remaining approval |
| --- | --- | --- |
| U03 customer cancellation at least four hours before start | Apply flat/5%/35% selected band and quote only approved monetary terms | Q25 flat amount/base/caps/refund, Q26 recipient, Q17 fees. Exactly four hours is 35%, never silently full refund. |
| U03 customer cancellation below four hours | Zero refund and separate retained funds; no selected beneficiary | Q26 recipient, Q17 fees, Q19 hold, Q20 roles, Q21 fields, Q23 legal terms and rollout. |
| Salon cancellation/closure | Preserve notification and distinct refund obligation | Full refund recommendation D02 and fee bearer require Q02/Q04/L01. No customer no-refund rule is copied onto salon-caused cancellation. |
| No-show | Start passed, ten-minute grace, explicit owner/staff confirmation, actor/time/reason and customer notification; no silent cancellation | Q02 authorization/correction/appeal and financial treatment; after-start customer cancellation scope remains separate. |
| Duplicate/excess payment | Reconcile separately; never allocate or fulfill twice | Q02/Q04/Q08 excess refund, fee bearer and authority. |
| Failed/unknown refund | Preserve obligation/reservation and stable operation identity | Retry/operator limits and P05; failure does not create extra cancellation pool. |
| Active/later dispute | Block affected unpaid entitlement; preserve later valid rights | Q19/Q20/L01 dispute scope, release and recovery. |

### 4.4 U04 immediate slot release after committed cancellation

**Approved business rule (2026-10-19):** after a valid cancellation commits,
booking status is cancelled and that booking no longer blocks the interval.
The slot is available immediately in canonical PostgreSQL availability and a
next eligible customer may book it. Refund delivery is asynchronous and cannot
keep the slot occupied. Redis slot/cache invalidation follows database commit.
PostgreSQL remains final authority; booking always revalidates canonical
availability and retains unique/exclusion protection against overlapping active
bookings. Cancellation does not remove independent closures, staff/access/service
rules, another active booking or a valid new customer's temporary hold.

Immediate means no refund, worker or cache-TTL wait for authoritative reads
started on the primary with a fresh snapshot after commit; it is not a promise
that an old in-flight snapshot, lagging replica or already-rendered client view
instantly changes. No code or runtime evidence is supplied by this document.

The following is the proposed transition/transaction/recovery contract, requiring
Q27/Q28 and RP07/RC06 implementation review where unresolved. U05 resolves
checked-in actors/reason/audit and selects durable outbox plus PostgreSQL outage
fallback; remaining storage/numeric/monetary choices stay explicitly open.

| Current state | Proposed cancellation behavior |
| --- | --- |
| pending | Allowed only through an authorized eligible cancellation command with applicable policy/consent; no new actor authority is granted. |
| confirmed | Allowed under the same authorization, policy and current-version checks. |
| checked_in | U05: customer forbidden; authorized salon owner/scoped admin only, with mandatory reason, actor/time and atomic audit. No new staff grant. Scope enforcement remains Q20/Q27; financial treatment Q29 cannot be guessed. |
| cancelled | Authorized idempotent no-op/replay of original cancellation; never a second cancellation or financial allowance. |
| completed, no_show, rejected | Forbidden to transition to cancelled through this workflow; a separately authorized correction never silently resurrects/reprices history. |
| Unknown state, inaccessible booking or invalid actor | Fail closed without mutation or leaking another actor's booking existence. |

A cancellation request, quote, owner approval request or HTTP acceptance alone
never releases a slot. Release is bound to the actual committed transition.
U03 no-show stays a separate confirmed attendance decision, not a silent cancel.

Proposed ordered transaction:

1. Authenticate/authorize current actor, bind immutable command/payload and
   discover all affected booking, profile/customer, salon/subscription and
   applicable financial identities before taking business-row locks.
2. Acquire the shared order: sorted profile gates (`profile:<uuid>`, seed 0),
   applicable sorted existing customer guards (customer UUID, seed 3715), sorted
   salon UUID gates (seed 0), then sorted `subscription:<salon_uuid>` gates
   (seed 0), then any sorted funding-scope gates. Acquire existing rows by
   published category/table/primary-key rank, including booking before its
   payment/cancellation/refund children and later audit records. Do not first
   lock a booking and then acquire an earlier gate. Missing earlier identity
   means rollback/rediscovery, never late out-of-order acquisition.
3. Under locks revalidate actor, state, schedule revision, bound policy, consent,
   required financial planning and replay identity. Record cancelled status,
   cancellation fact, one logical slot-release audit marker, durable post-commit
   cache-invalidation intent and notification intent atomically. Preserve any
   required known refund obligation/reservation; unresolved financial policy
   cannot be guessed. If policy prevents a valid cancellation, fail before commit
   with the original reservation intact. Refund provider delivery never occurs
   inside this transaction and is not a condition for release after commit.
4. Commit once. Rollback keeps the booking's occupancy and emits no committed
   release, invalidation or notification. An unknown commit result is reconciled
   using the original durable command, never a second cancellation key.
5. After commit dispatch scoped Redis invalidation and notifications independently
   from refund processing. Failures leave the cancellation and released database
   interval intact; durable retries reuse the same event/operation identities.

Proposed concurrency outcomes:

| Race/order | Required outcome |
| --- | --- |
| Cancellation commits before new booking revalidation | New booking sees cancelled as nonblocking, rechecks all current availability/access rules and may commit. |
| New booking checks while old active booking is still committed | It may conflict/reject, or wait through normal locking; an old snapshot never guarantees a slot. A fresh retry after cancellation may succeed. |
| Cancellation rolls back | Old booking still blocks; speculative release/Redis state cannot authorize a new overlap. |
| Two customers race for released overlapping intervals | Shared locks and final active-booking exclusion admit at most one overlapping commit, even with different start times/idempotency keys. |
| Cancellation races completion, check-in, no-show, reschedule or closure | Serialize and revalidate state/version; loser conflicts/replays without undoing the winner. Final reschedule/closure guards still apply. |
| Delayed cancellation invalidation arrives after new booking/hold | It cannot delete the new actor's hold or overwrite availability as unconditionally free. Refill only from current PostgreSQL state. |

Repeated cancellation requires authorization before replay. Same key/same payload
returns original committed cancellation; same key/different payload conflicts.
A new key against already-cancelled state returns the original safe outcome/no-op
without new refund obligation, slot-release marker, notification or reactivation.
Durable recovery may re-dispatch an outstanding original side effect. Replay
must distinguish original mutation result from current availability: the slot
may already have been booked by someone else. Current availability is re-read,
never replayed as a fresh promise from a cached cancellation response.

Proposed audit marker name is `booking.slot_released` (not an existing enum or
implemented event). Bind its stable identity to booking/cancellation revision,
original staff/resource interval, previous/new state, actor or verified system
principal, recorded transaction/effective time, policy/reason code, correlation
and idempotency references. Record a database-backed availability revision or
other reviewed equivalent if chosen under Q28. It means only this booking's
occupancy was removed, not that the interval is unconditionally free or refund
was paid. Preserve financial/privacy rules; no contact, hold token, credentials,
raw errors or internal allocation in user-visible audit/notifications.

Proposed notifications use one committed logical event per cancellation for the
customer and authorized salon operations recipients, with durable delivery state,
retry and duplicate suppression. A message says cancelled and refund status
separately; never claim refund paid or guaranteed free slot. Do not broadcast old
customer details to prospective next customers. Notification outage cannot
rollback cancellation/re-reserve slot; retries cannot repeat state/money effects.
Channel, recipient and retry/escalation particulars remain Q28 review.

Stale-cache and Redis failure requirements, including mandatory fresh canonical
coverage for the requested interval and old-hold cleanup, are detailed in
[G09 U04 protocol](../migrations/payment-subscription-booking-designs/09-slot-hold-concurrency-support.md#u04-committed-cancellation-and-cache-recovery).
No new path may activate until legacy writers and cross-process cache readers
honor this contract; a feature flag or assumed TTL is not proof of coherence.

### 4.5 U05 resolved cancellation and slot-release risk review

Review date: 2026-10-19 (Asia/Calcutta). These design rules resolve the latest
user-directed invariants and supersede conflicting U04 proposals. They are not
proof of runtime behavior or approval to implement schema/code. Exact money
policy and numeric operational limits remain Q29/Q30, alongside prior open items.

**Checked-in cancellation:** a customer must receive a denial before any
mutation, even if attempting a new idempotency key or an owner-style payload.
A salon owner or permission-scoped admin may issue controlled cancellation with
mandatory cause/reason and current actor/profile/authority validation. Record
actor, trusted timestamp, prior/new state, current schedule/policy revision,
cause/reason, correlation/idempotency and permission basis in the same commit.
Admin authority remains scoped under Q20 and requires existing admin-finance MFA
when exercising financial powers. Staff no-show authority does not grant this
checked-in cancellation permission. Completed/no_show/rejected are not converted
through ordinary cancellation. Check-in winning a race makes customer cancel
fail; operator cancel must revalidate the checked-in state.

Refund/payout treatment is explicitly defined as follows, without inventing a
refund amount:

| Checked-in money situation | Required treatment |
| --- | --- |
| No verified collected funds | No fictitious refund or salon/platform payout. Record cancellation and any outstanding issue separately. Authorization-only is not captured money. |
| Verified platform capture, approved remedy known | Under booking/payment/root locks bind one cancellation source, reserve the approved still-unfulfilled refund subject to cumulative capture/reservation caps, and enqueue asynchronous original-operation delivery. Prevent payout of those funds. |
| Remedy, fee bearer or beneficiary unknown | Commit permitted operational cancellation with one durable financial-review obligation referencing immutable capture/policy facts. Restrict affected retained captured funds from new payout pending Q29 and existing Q17/Q19/Q25/Q26; do not recognize arbitrary income, invent a refund amount, mark refunded, or fabricate an entitlement/sealed final allocation. If a required consent or legal precondition makes cancellation invalid, reject before commit instead. |
| Direct cash/UPI paid to salon | Record direct-receipt evidence and operator/customer remedy workflow; it is not a platform-funded refund or provider payout. Responsibility/remedy remains Q29. |
| Payout already confirmed or submitted/unknown | Preserve prior movement and reservations. Append funded refund/deficit/recovery review; do not undo paid facts, release unknown funds, double transfer or assume salon bank debit authority. |

Checked-in operator cancellation is a different cause from U03 pre-start
customer cancellation; it does not automatically imply zero refund, 5%/35%,
a flat fee or 70/30 allocation. Cancelled service is never fabricated as completed
for payout. Partial service entitlement/remedy needs Q29/L01/L02 and an explicitly
approved adjustment, not mutation of booked price or past invoices. Refund
approval/settlement never delays slot release after a valid cancellation commit.

Duplicate protection is booking-root/state based as well as command-key based:
two owner/admin requests with different keys lock the same booking/version;
one changes state, the other returns the existing safe outcome/no-op or stale
version conflict. One cancellation source/revision owns one release marker,
financial planning/refund obligation and logical notification. A later authorized
money correction appends evidence; it is not another cancellation. Same key with
changed payload conflicts; delivery retries reuse original external identities.
Unknown database commit outcome is reconciled before any renewed submission.

**Redis failure:** status/audit/refund-planning and durable database outbox
invalidation intent commit atomically without Redis I/O or connectivity checks.
Independence is from Redis, not from database durability: if the required outbox
intent cannot persist, transaction rolls back and no successful cancellation
is reported. Postcommit invalidation failure never rolls cancellation back or
reoccupies the slot. The outbox is a durable delivery obligation, not Redis-only
queue state or best-effort deletion. It remains recoverable through worker crash.

When Redis is unavailable, bypass cache and unavailable hold admission, use
fresh canonical primary availability, and permit eligible PostgreSQL-only
booking attempts. Indicate hold coordination unavailable; never fake an acquired
hold. Apply all database actor/access/resource/payment guards and final overlap
constraints. Healthy-hold requirements/limits remain Q12, but cannot override
this selected outage fallback. If PostgreSQL itself is unavailable or freshness
cannot be established, return truthful retryable unavailability without a new
booking; Redis cache is not a substitute. Neither stale busy/empty cache nor
stale free cache can block/create a booking. A legitimate healthy new hold is
not stale cache and retains its approved temporary-coordination behavior.

**Concurrency outcome analysis:** all database mutation paths use complete
identity discovery, sorted profile/customer/salon/subscription/funding gates,
then ranked booking/payment/cancellation/audit rows, with fresh state/version
revalidation after waiting. Webhook intake verifies/deduplicates durable receipt
before separate ordered business application; never lock payment first then
wait on earlier booking/salon gates. External calls stay outside business locks.

| Race | Resolution and final outcome |
| --- | --- |
| Cancellation versus new booking | Cancellation first removes old occupancy; next booking checks current rules. New booking seeing old active occupancy conflicts or retries. Two new overlapping contenders admit at most one commit under final exclusion, regardless of keys. Cancellation rollback preserves old occupancy. |
| Cancellation versus hold acquisition | PostgreSQL and Redis are not one atomic transaction. Hold acquisition uses canonical candidate/revision, performs atomic Redis work outside SQL row locks, then fresh PostgreSQL validation; stale tentative hold is compare-released or treated as nonbinding/unavailable. Cancellation cleanup removes only its old hold generation, never a newer valid hold. Each eventual booking rechecks PostgreSQL even after hold validation; a subsequent change cannot turn hold into booking authority. |
| Cancellation versus verified payment confirmation | Both business applications lock same booking/payment/source under shared order. Capture first: cancellation sees captured funds and plans approved refund or financial review. Cancellation first: later verified capture is still recorded once for original booking, kept cancelled, and sent to refund/remedy review. It never auto-confirms/reopens the slot or attaches capture to a replacement customer's booking. |
| Cancellation versus completion/check-in/no-show/reschedule | State/revision winner commits; loser revalidates and conflicts/no-ops without overriding terminal facts. A customer request loses cancellation eligibility after check-in. A permitted checked-in owner/admin cancellation cannot double-finalize with completion. |
| Duplicate/delayed payment or outbox delivery | Deduplicate economic source and logical side effects, reconcile original operation, append observations. No duplicate booking, refund, release or automatic reactivation. |

Exactly one final booking outcome means at most one conflicting terminal state
transition for a booking revision and at most one overlapping active booking,
not a promise that one contender must succeed. Both may fail normal eligibility
checks. Payment facts are separate from booking outcome and must still be
recorded after cancellation; recording money never changes cancelled to confirmed.
PostgreSQL constraints protect overlap but do not alone enforce state/financial
exactly-once semantics: guarded current-state updates, source uniqueness and
idempotent workers are also required, including all legacy entry points.

Outbox retry/dead-letter/manual repair contract is defined in
[G09 U05 recovery](../migrations/payment-subscription-booking-designs/09-slot-hold-concurrency-support.md#u05-durable-outbox-retry-dead-letter-and-repair).
Database fallback remains active for stale/unverified cache through pending,
retry-wait, leased and dead-letter states; dead-letter is not successful cleanup.
No quantitative recovery/latency or exactly-once network-delivery claim is made.

## 5. Proposed state machines

These are target domain models, not claims about current endpoints or database enums. State names and transitions are **Approval required** for implementation review. Approved completion/hold/confirmation requirements cannot be weakened by approving a state machine.

| Aggregate | Proposed transitions and guards |
| --- | --- |
| Booking | pending -> confirmed / rejected / cancelled; confirmed -> checked_in / completed / cancelled / no_show; checked_in -> completed / cancelled / no_show. All cancelled transitions are subject to U04 section 4.4/Q27 state-by-actor checks; U05 checked_in cancellation forbids customers and requires scoped owner/admin reason and audit. U03 no_show additionally requires full ten-minute grace after start, explicit owner/staff confirmation, actor/time/reason and customer notification; never silently cancel. Completion requires applicable collection evidence. Terminal states cannot be edited to recreate availability or erase financial obligations. |
| Reschedule request | requested -> approved / declined / withdrawn / expired. Approval rechecks PostgreSQL availability atomically, retains the original schedule/audit, updates policy applicability explicitly, and notifies affected parties. Request creation alone does not release the original booking. |
| Cancellation request | requested -> approved / declined / withdrawn / invalidated. A direct eligible cancellation may finalize immediately. Valid cancellation fact, required financial obligation/intent, slot-release audit and post-commit invalidation/notification intents are atomic; refund processing is separate. U04 slot release occurs at cancellation commit, never refund settlement. |
| Payment attempt | created -> authorized / captured / failed / cancelled / expired; authorized -> captured / failed / cancelled / expired. A late verified capture is still recorded after a failure/expiry and sent to reconciliation. Refund totals are separate from capture evidence. |
| Refund attempt | created -> processing -> processed / failed; failed -> processing only through a reconciled retry. An uncertain timeout remains pending reconciliation; it is not proof of failure. Never create a second refund obligation for the same retry. |
| Payout | eligible -> approved -> scheduled -> processing -> paid / failed; failed -> approved after reconciliation and renewed eligibility; paid -> reversed only on verified reversal. Preserve attempt history and linkage on retry. Scheduling may be immediate, but no validation stage is bypassed. |
| Dispute | open -> under_review -> resolved_customer / resolved_salon / dismissed. Resolution records evidence, authority and resulting append-only postings; hold release is a separate validated action. |
| Subscription access | trial -> active / expired / cancelled; active -> grace_period / expired / cancelled; grace_period -> active / expired / cancelled; expired or cancelled -> active only after verified purchase/admin action allowed by policy. D09 proposes grace only after a paid period, with no new booking/order privileges. Cancellation/paid-through access and admin authority remain **Approval required** (Q07/Q09/Q13). Pending activation/payment and suspension remain distinct operational reasons. |
| Redis hold | absent -> held -> consumed / released / expired. Only the bound actor with the opaque token may release/consume; expiry permits another hold but grants no booking entitlement. |

Payout `eligible` is a revocable assessment, not a transfer. Every approval, schedule and execution rechecks current eligibility, locks/reserves the unpaid allocation, and rejects a changed destination or active dispute. A unique allocation-to-payout reservation prevents both retries and simultaneous manual/automatic runs from spending it twice. An uncertain timeout remains `processing` until provider/manual reconciliation proves the outcome. Provider transfers require provider terminal confirmation; a separately approved manual bank method requires independently verified transfer evidence (D11/P06/L03; **Approval required**). An admin assertion or approval record alone is insufficient. Confirmed actual net and any refund/dispute reserves must support the requested amount; unknown charges do not justify a guaranteed available balance. The U01 48-hour completed-service hold and seven-day restricted renewal grace are selected business scopes, not deployment authorization; Q19 cancellation hold and Q07 timing details remain unset.

Manual payout command requirements: amount, immutable recipient/destination version, reason, default/custom message, authorized finance/admin actor, transfer reference/UTR, transfer date and provider/manual method. Separate approval from confirmation; capture reference/date when the transfer occurs, not as invented values during approval. Reject duplicates and amounts above eligible funds. Default cancellation message: "Customer cancelled this booking inside the 4-hour cancellation window. Your eligible amount is INR {amount}. Payout status: {status}." Customer identity/contact details never appear in staff financial history.

## 6. Money examples and snapshots

All examples use synthetic amounts, not Cashfree tariffs, confirmed GST treatment, sandbox results or real transfers. A sample fee/GST pair must not be converted into a hardcoded rate. Each conditional financial example is **Approval required** for its stated policy assumptions; the arithmetic does not approve them.

### 6.1 Completed online booking and Cashfree charge reconciliation

For a ₹150.00 completed online booking, the approved customer total is ₹150.00 and platform service commission is ₹0.00. There is no ₹7.50 processing surcharge. Under U01's selected salon-borne completed-service charge policy (actual pricing/tax still requires P01/L02), a hypothetical provider reconciliation could show:

| Component | Synthetic amount | Evidence/classification |
| --- | --- | --- |
| Customer paid | ₹150.00 | Verified capture for the booked service/cart |
| Platform service commission | ₹0.00 | C02, not a Cashfree charge |
| Cashfree gateway fee | ₹2.00 | Illustrative provider actual; real amount requires P01 |
| GST on that gateway fee | ₹0.36 | Separately reported illustrative actual; no GST-rate assumption approved (L02/P01) |
| Easy Split fee | ₹0.20 | Separate illustrative actual; account applicability requires P01 |
| Settlement fee | ₹0.10 | Separate illustrative actual; do not duplicate an inclusive provider total |
| Payout fee | ₹0.10 | Separate illustrative actual, charged once for the relevant transfer |
| Refund fee | ₹0.00 | Example only; zero needs evidence/not-applicable classification in real records |
| Total provider charges | ₹2.76 | 2.00 + 0.36 + 0.20 + 0.10 + 0.10 |
| Salon net after provider charges | ₹147.24 | 150.00 - 0.00 - 2.76, conditional on approved fee bearer |

Before any transfer, the nominal ₹147.24 may be held or provisional. It becomes eligible only after all C05 checks, the approved dispute hold, reconciled charges/reserves and a unique reservation. The transfer becomes paid only upon confirmed outcome. If payout cost is only available afterward, the reserve/true-up method is **Approval required** (Q04/Q16/L02); do not promise a final net from an estimate. Unknown actual charges remain null and block a claim of guaranteed available net.

### 6.2 Historical U02 late cancellation: conditional 70/30 examples

These U02 examples do not supply a recipient/allocation for U03; Q26 is open.
Synthetic P=INR 150.00 and evidenced F=INR 3.00 illustrate Q17 branches, not
provider pricing or fee-bearer approval. Customer refund R=0 under new U02 late
policy; requests exactly four hours before start are outside this example.

| Example | Distributable pool | Salon amount | Platform allocation / net | Approval boundary |
| --- | --- | --- | --- | --- |
| E01: requested net pool | 147.00 | 102.90 | 44.10 allocation and net after separately recorded 3.00 cost | Q17 must confirm fee reduction; 150=3+102.90+44.10. No second fee deduction. |
| E02: platform absorbs costs | 150.00 | 105.00 | 45.00 allocation; 42.00 net after 3.00 cost | Q17 alternative remains open; 150=105+3+42. |
| E03: unknown or underfunded costs | Not finalizable | Not a guaranteed payable amount | Unresolved evidence/deficit, never forced zero cost | Retain obligation/evidence; await approved accounting/funding. |

Admin approval/timing does not turn either amount into a confirmed transfer.
Q19/Q20 and provider/legal gates still block execution. No cancelled-service
staff commission is earned. Historical 20/80/refund-first examples are superseded
for new U02 late terms and remain meaningful only under their original bindings.

### 6.3 PAY_AT_SALON balance collection

Example: booked service ₹150.00, online collected ₹0.00. At the visit the owner records ₹50.00 actually received in cash, then ₹100.00 actually received directly by cash/UPI. The balance goes ₹150 -> ₹100 -> ₹0. The ledger must record each distinct receipt once; replaying either idempotency key records no second receipt. A customer saying "I paid" alone is not a receipt. Whether the public API supports partial direct receipts is **Approval required** for contract review (Q08); if not approved, record one verified ₹150 receipt rather than inventing partial-payment support.

Platform commission remains ₹0.00; the salon already possesses the ₹150.00 and the platform owes no vendor payout on these direct receipts. Do not invent Cashfree PG, Easy Split or payout fees for a flow that never called Cashfree. Any salon's independent UPI/provider charges, if present, are separate actual expenses and not evidence of platform collection. Existing collection-before-completion remains the compatibility requirement.

If the subscription expires before the appointment, the appointment stays visible. D08 proposes allowing the same actual-receipt recording and completion while blocking a new online order (**Approval required**, Q07). This does not allow a new booking or start a new payment collection session. Until approved, the conflict between expiry and required receipt is a release blocker, not permission to mark an unpaid booking completed.

### 6.4 Staff commission on completed services, refunds and cancellation

| Example | Conditional calculation | Decision status |
| --- | --- | --- |
| E04: ₹1,000 service, 40% staff | Staff ₹400.00; salon internal gross ₹600.00; platform service commission ₹0.00 | The supplied example illustrates an allowed rule, not a universal 40% rate. Gross-price basis/effective-time/earning event are **Approval required** (D10/Q10). |
| E05: ₹150 service, same illustrative rule | Staff ₹60.00, salon gross ₹90.00. If D04 salon charges total ₹2.76 and owner alone bears them internally, salon remainder ₹87.24; ₹147.24 provider net = 60 + 87.24 | Internal charge bearer is **Approval required** (Q04/Q10/L04). Staff allocation is not an extra platform payout or second expense on top of the same allocation. |
| E06: completed ₹1,000 service later refunded ₹250 | Under proposed proportional reversal: staff debit ₹100, salon debit ₹150; original ₹400/₹600 entries stay unchanged | **Approval required** (D10/Q10/L04); already-disbursed staff recovery needs separate authority. |
| E07: ₹150 cancelled booking | Under D10, no earned completed-service commission. Any staff time compensation is a new approved ledger category, never automatically 40% of ₹80/₹120 cancellation proceeds | **Approval required** (D10/Q10/L04); until decided, do not auto-post cancellation staff earnings. |

Staff snapshots include rule/version, effective interval, assignment, service lines, amount basis, percentage and rounded allocation. Prevent overlapping effective rules for the same scope. D10 proposes selecting the rule at booking creation and earning at completion; **Approval required** (Q10). Multiple staff weights must share the approved pool, not each claim it. Daily/monthly reports use the salon timezone. A later price/rate change cannot alter historical snapshots; reversals/corrections append linked entries.

### 6.5 Refund and dispute handling

| Example | Required distinction | Decision status |
| --- | --- | --- |
| E08: ₹150 captured, ₹50 refund owed | Reserve ₹50 from the start. Refund accepted -> processing; failed or unknown -> obligation still reserved. Provider-confirmed processed -> record customer refund ₹50 once; duplicate webhook adds no refund | This illustrates a separately approved on-time/other-cause refund, not new U02 late cancellation (R=0); cause/formula needs Q02/Q18 and processed semantics P05. Do not distribute the reserved amount. |
| E09: dispute before payout | For E04 or the ₹150 online example, block the disputed allocation from both manual and automatic execution even after the ordinary hold expires. Record review and outcome without deleting capture/fee evidence | Hold scope, permitted partial release and decision authority are **Approval required** (Q05/Q13/L01). Recommend freezing the entire affected booking allocation until scope is approved. |
| E10: full refund after confirmed ₹147.24 payout | If the customer is entitled to ₹150.00, record the ₹150 refund obligation, the historical ₹147.24 payout and ₹2.76 fee facts separately. Find an approved funding/recovery source; do not erase the payout or assume the salon bank account can be debited | **Approval required** (Q04/Q16/L01-L03). Later refund/reversal fees are additional separate actuals, not hidden in the old ₹2.76. |
| E11: provider reverses payout | Preserve the paid event, append verified reversal with reference/amount, reopen only the reconciled recoverable entitlement. Do not automatically resend funds or refund the customer solely because a vendor payout reversed | **Approval required** for retry/authority (Q13/Q16), with provider terminal evidence P05-P06. |

### 6.6 Trial and subscription price display

Calendar proposal D07 (**Approval required**, Q06): activation 2026-12-31 10:00 Asia/Kolkata -> trial end 2027-02-28 10:00 Asia/Kolkata, with an exclusive end instant and no implicit 60-day conversion. Snapshot the dates once. Later timezone changes cannot extend the trial. U01 selects no cap for the new target policy; calendar convention and legacy cap transition remain unapproved.

Grace proposal D09 (**Approval required**, Q07): paid period ends 2026-11-01 10:00 Asia/Kolkata; renewal-only grace ends 2026-11-08 10:00 Asia/Kolkata. Under this proposal, new bookings/online orders are blocked from November 1, not November 8; history and approved existing-booking handling continue. This is a seven-calendar-day renewal interval, unrelated to the selected 48-elapsed-hour completed-service hold. No trial grace is a D09 proposal only, not an approved applicability rule.

Plan totals appear first; monthly equivalents are informational only: Growth 1 month INR 349.00 (349.00/month), 6 months INR 1,499.00 (249.83/month), 12 months INR 1,999.00 (166.58/month); Premium 1 month INR 599.00 (599.00/month), 6 months INR 2,499.00 (416.50/month), 12 months INR 3,499.00 (291.58/month). Rounded equivalents never determine charges. Subscription tax inclusion and launch renewal policy remain **Approval required** (Q09/L02).

## 7. Availability, expiry and coordination

- Extend the existing PostgreSQL `get_available_slots` and `create_booking` paths; never calculate slots or insert bookings/service snapshots directly in Python. Apply the same guards to app, QR and manual walk-ins.
- Intersect salon and staff schedules, then exclude breaks/leave/holidays/closures and active bookings. Duration plus cleanup buffer must fit the permitted interval. Buffer values and whether they occupy staff only or other resources are **Approval required** (Q11).
- Evaluate minimum notice and same-day cutoff using trusted time and salon timezone. Values, overnight hours and recurring closure expansion are **Approval required** (Q11); do not invent defaults. A missing day is closed. Test daylight-saving boundaries even when the initial default timezone has none.
- Pausing/closing prevents new bookings; existing bookings remain visible. Preview affected bookings, require explicit cancellation/reschedule handling and notify them. A settings update must not silently delete/hide existing appointments.
- Trial/paid access expiry hides the salon from new discovery, blocks new bookings and new online booking-payment attempts, and returns a customer-safe inactive reason with nearby eligible alternatives. Subscription renewal remains a separate permitted purchase. Owner reads retain history, pending service work and an upgrade prompt. Refund/dispute/payout processing is not disabled by expiry. U01 selects seven-day restricted grace and completion permission; exact timing/applicability and direct receipt recording remain **Approval required** (Q07).
- Recheck access at quote, booking creation and payment-order creation. An already-open provider order can still capture after expiry; record the money rather than discarding a webhook. D15's proposed fulfillment/refund handling is **Approval required** (Q07/P05); provider observation does not authorize another collection.
- Acquire a five-minute Redis hold atomically with `SET NX EX` or equivalent, using a random opaque token bound to actor, salon, staff, interval and requested services. Prevent overlapping intervals with different starts/durations; locking only an exact start-time key is insufficient. Use atomic interval/resource coordination, without inventing availability in Python.
- Availability may annotate/filter PostgreSQL-returned slots for holds; hold responses never promise a reservation. A booking with a valid hold still rechecks PostgreSQL. Consume/release uses atomic compare-and-delete, never unconditional delete. Do not log tokens.
- PostgreSQL commit precedes cache invalidation. Idempotent retry returns the original booking; it must not depend on a consumed/expired hold. Recovery must tolerate a crash between commit and hold cleanup.
- U05 selects PostgreSQL-only outage fallback with fresh canonical availability and truthful hold-unavailable reporting. Unavailable Redis cannot gate valid cancellation or booking fallback. Healthy mandatory-hold/limit policy remains Q12; booking always rechecks PostgreSQL/exclusion, and lack of fresh database truth returns retryable unavailability, never cached acceptance.
- Required later independent-connection test: two different customers/idempotency keys compete for the same slot -> one HTTP 201, one HTTP 409 `slot_unavailable`, exactly one booking row. Same-key replay is a separate test and may return the original successful booking.

## 8. API contract requirements

Reuse existing `/v1` routes and durable idempotency where semantics match. Routes, new field names, serialization, error mappings and async status shapes below are **Approval required** for API design/compatibility review; they are proposed additions/extensions, not available endpoints. They cannot choose unresolved money or access policy. Generate implementation OpenAPI and runnable synthetic examples only in later authorized phases; this document does not publish a contract or create a Postman workspace.

| Surface | Required request/response behavior |
| --- | --- |
| Existing booking quote | Server-resolved service snapshots, service/cart total, zero customer surcharge, currency, policy/version, payment availability, quote expiry; never accept client prices as truth. Quote is not a hold. Cancellation quote output also identifies selected allocation model, refundable base, refund R, fee bearer and provisional/actual charge status; **Approval required** policy values cannot become an executable final quote. |
| Slot hold create/release | Proposed POST `/slot-holds` (201), DELETE `/slot-holds/{id}` (204). Input salon/staff/services/start; return opaque token, expiry, interval and availability reason. Release supplies token securely, not in query strings. Scope to actor, rate-limit and return conflicts consistently. |
| Booking/payment creation | Existing booking route remains 201; accept hold proof if enabled, recheck SQL, reject changed/stale quote as defined by reviewed contract. New online payment amount equals the approved unpaid service amount, never a fixed surcharge. Define full versus advance support in Q08. |
| Cancellation | Authorized customer quote shows applicable customer refund/terms. Restricted admin view may show complete allocation; owner payout view must omit platform percentage/formula and expose only Q21-approved fields. Confirmation binds quote/policy/current booking and durable outcome/notification intent. |
| Refund | Existing request returns an explicit pending/processed/failed state and immutable obligation reference. Provider acceptance never means completed refund. Customer refund-request authorization is separate from owner/admin approval authority. |
| Owner earnings/ledger | Extend existing earnings with collected, refunded, actual charges, provisional/reconciled net, held, eligible, scheduled, processing, paid and reversed totals. Distinguish cash receipts from online payout funds; paginate ledger entries. |
| Payout schedule | Proposed owner GET/PATCH capability-backed schedule; response lists allowed choices, timezone, effective date, admin restriction and unconfirmed provider limitations. Unsupported choice -> 422. No weekend guarantee from a static list. |
| Admin finance | Proposed payout list/detail, approval/scheduling/manual confirmation, charges, ledger, dispute resolution and correction commands. Require reason, scoped financial permission, MFA and idempotency; response includes audit reference and pending versus final state. |
| Staff commission | Owner rule/assignment management and daily/monthly reports; staff sees only approved own allocations without customer PII. Historical correction is a separate command with reason, not edit/delete. |
| Subscription | Extend existing config/plans/status/access-state/checkout/history; expose trial and paid-through dates, grace, reason, booking/payment eligibility and upgrade action. Manual renewal is D12, **Approval required**; never enable automatic renewal without explicit owner consent. Return direct-receipt permission separately from new online-order eligibility under Q07. |
| Inactive salon | Proposed safe detail response exposes inactive reason and nearby active alternatives without enabling booking. Preserve existing list envelopes/404 privacy behavior until compatibility review chooses a versioned representation. |
| Reschedule | Proposed request/list/respond routes return original/requested intervals, expiry, status and history; approval rechecks access, slot, price and cancellation-policy effects. |

Shared contract requirements:

- Explicit response model and HTTP status on every endpoint. Authentication uses verified Supabase JWT subject and current profile role; ownership and business authorization are enforced in use cases.
- Require `Idempotency-Key` for financial/state-changing commands; bind actor, operation and canonical payload fingerprint. Same key/different payload -> 409 `idempotency_conflict`; an uncertain external outcome requires reconciliation, not a new key/transfer.
- Proposed errors: 409 `slot_unavailable`, `hold_expired`, `booking_state_conflict`, `payout_not_eligible`, `payout_already_reserved`, `dispute_active`, `quote_stale`, `subscription_expired`; 403 `forbidden`/`mfa_required`; 404 for inaccessible resources; 422 `unsupported_payout_schedule`; 503 `payment_provider_unavailable`/`slot_hold_unavailable`. Review mappings against existing error codes instead of replacing them silently.
- Expose UTC timestamps with offsets, salon timezone, stable IDs, pagination/cursor limits and request correlation ID. No raw SQL, constraints, credentials or provider response bodies in errors.
- A durable asynchronous operation may return 202; reserve 200/201 for the actual represented outcome. Define retryability and polling reference explicitly. Do not imply payment/payout success through HTTP acceptance alone.

### 8.1 Admin capabilities and reporting scope (U02)

Approved target capability scope; routes, permission names, filter contracts and
metric definitions still require design review, not an assertion of availability:

| Capability | Required target behavior and remaining boundary |
| --- | --- |
| Pending cancellation payout list | Authorized admin sees pending items, eligibility blockers, selected policy, evidence and approval state; no list action bypasses hold/dispute/funding checks. |
| Salon-level payout history | Scoped salon chronology with attempts, scheduled/actual dates, outcomes and corrections; distinguish pending/unknown/failed/paid/reversed. |
| Daily/weekly/monthly sales | Time-bucketed sales with explicit timezone/calendar and recognized event. Gross booked/captured/net/refunded are distinct; metric definitions and week boundaries remain reviewable. |
| Online/cash totals | Distinguish verified online captures from direct cash/UPI receipts. Direct receipts are not platform cash or funds payable through platform settlement. |
| Completed/cancelled/no-show totals | Separate lifecycle counts; cancellation allocation never implies completed service. Define date cohort, correction and unique booking counting. |
| Subscription revenue | Separate subscription purchases/recognized revenue, offer discount, taxes and refunds from service/cancellation money; recognition basis remains L02. |
| Payout status and audit history | Approval, schedule, attempts, verified outcome and append-only corrections with actor/authority/reason; approval and HTTP acceptance are not transfer success. |
| Custom subscription offers | Admin creates salon-specific effective-dated offers under section 8.2, with actor/reason and immutable purchase binding. |

Full internal allocation is admin-restricted. Exact roles/scopes/stages/limits
remain Q20/Q13, including export access. Use paginated bounded reads; no arbitrary
cross-salon or owner access through a generic report endpoint. Report queries,
caches and exports need the same actor/salon and privacy boundaries. Revenue
recognition, refund attribution and late-provider-cost corrections must be
explicitly distinguished from mutable operational projections.

### 8.2 Salon-specific subscription offers (U02)

- Keep the default plan and its price unchanged; an offer is salon-scoped,
  effective-dated commercial terms, not a catalog overwrite or implicit mandate.
- Preserve original price and discounted price, currency, effective dates,
  target salon/plan and the approving admin actor/reason. Required persistence
  semantics are approved; exact storage/constraints and migration design remain
  later review, with no new table/revision assigned here.
- Purchase/quote must bind an immutable offer/version and final payable amount;
  old invoices and existing subscriptions keep their original recorded price.
  Corrections append evidence; no retroactive invoice/period repricing.
- Duration/expiration, timezone/end-inclusivity, overlap/precedence, revocation,
  eligible plan/period and open quote/order behavior are **Approval required**
  Q22. No automatic best-discount selection or numeric duration is invented.
  Late capture keeps its original order/purchase amount and is reconciled;
  offer expiry does not discard money or authorize silent repricing.
- Owner sees only final payable price for the offer, not original/discount
  breakdown or internal platform margin. The required original/discounted
  snapshots remain in restricted admin/accounting evidence. Internal costs,
  allocation fields and admin-only reason must not leak through generic detail,
  exports, notifications, cache or replay responses. An owner-facing message
  must be separately sanitized and authorized.
- Financial calculations use integer paise or Decimal. Discount/tax validation,
  funding, zero/negative price constraints, recognition, invoice wording and
  grandfathering need Q09/L02; the existence of an offer approves no tax rate.
  Q20 defines authority and Q24/L05 defines actor/reason retention/erasure.

## 9. Proposed migration groups and dependencies

No revisions or SQL are created here. All groups are **Approval required** for migration-design review and dependent business/provider/legal decisions; a numbered group is not execution approval. Reinspect the actual source head before assigning any revision ID. Existing `0040` is an observed source head, not Mumbai's applied revision. Never stamp, replay restored history or alter old migrations to manufacture equality.

| Order | Group | Reuse and proposed additions |
| --- | --- | --- |
| Gate | Mumbai reconciliation | Review restored-schema/history mismatch and prepared 0038-0040; prove target compatibility and explicit execution plan separately. |
| 1 | Payment actuals and financial postings | Extend 0026/0029/0033/0037 foundations with charge evidence, distinct components, reconciliation/allocation and append-only corrections. Preserve legacy snapshots. |
| 2 | Cancellation policy versions | Effective policies, immutable booking bindings, quoted/final refund and allocation obligations; depends on money vocabulary. |
| 3 | Disputes, settlements and payouts | Eligibility, holds, allocation reservation, payout attempts/confirmations/reversals and unique references; depends on groups 1-2. |
| 4 | Payout schedules/capabilities | Account-specific allowed schedules, owner selection and admin override; depends on payout identity and verified provider capabilities. |
| 5 | Staff commission ledger | Effective rules, multiple-staff allocation snapshots, reversals/corrections and reporting indexes; depends on booking service and financial references. |
| 6 | Subscription lifecycle | Extend existing trial/billing/access rules and grace/expiry contracts. Existing plan prices need no duplicate seed. |
| 7 | Booking/availability/holds support | Extend SQL guards for schedule intersection, notice/buffers and concurrency if missing. Redis TTL coordination itself needs no permanent hold table. |
| 8 | Closures and reschedule conflicts | Review affected-set integrity, original/new interval history, policy changes and transactional notification intents. |
| 9 | Finance authorization/audit coverage | Audit mechanism must be available before any new financial command is enabled; integrate it in earlier groups where needed. Final group closes cross-workflow coverage, not delayed auditing. |

Every eventual migration review must cover upgrade, safe downgrade or explicit forward repair, bounded locks, indexes, constraints, uniqueness, timestamps/actors, RLS and effective privileges, retention, erasure behavior, existing-row compatibility and rollback. Add no blanket client grants. Keep the raw baseline and sealed evidence intact. Data-bearing finance changes should normally be repaired forward rather than destructively downgraded. None may execute before separate migration-design and staging-execution approval.

## 10. Security, audit and account deletion

- Keep clean architecture: API -> application -> domain; infrastructure implements ports. Fine-grained finance authorization belongs in use cases; repository scoping and RLS remain defense in depth.
- Existing roles are customer, staff, owner and super_admin. Finance delegation, dual approval and amount limits are **Approval required** (Q13), not an assumed new trusted JWT claim. Require verified `aal2` for admin financial actions.
- Set transaction-local actor context from the verified identity. Audit approval, rejection, schedule changes, manual confirmations, refunds, disputes, corrections, failed/denied sensitive actions and secret-destination changes without logging financial PII.
- Verify provider signatures over raw request bytes before business effects. Deduplicate provider events, enforce amount/currency/reference binding, and handle out-of-order delivery. Persist intent before external calls; use stable external references and reconcile timeouts.
- Financial audit entries include immutable action/event ID, actor/role/permission snapshot, timestamp, reason code, sanitized explanation, object IDs, policy/destination versions, idempotency/correlation references and outcome. Append a new outcome/correction event instead of replacing evidence.
- D14 recommends authenticated envelope encryption with keys managed separately from the database, or adequate provider tokenization; solution/provider/backfill design is **Approval required** (Q15/P04/L05). Bind ciphertext to salon/destination version; version keys, support rotation and restrict decryption to the required adapter. Responses/audits contain only masked values and nonreversible fingerprints where justified. No plaintext storage alternative is approved.
- Treat existing plaintext as a release blocker for payout enablement. A later separately approved backfill must encrypt, verify decryptability, eliminate plaintext copies and assess replicas/backups/retention. No key generation, secret access or backfill is authorized here. Rolling back to plaintext is prohibited.
- On account erasure, remove direct profile/contact links, scrub arbitrary personal free text and restricted replay/cache payloads, and retain pseudonymous accounting/event relationships, amounts, currency, policy snapshots, provider evidence required for reconciliation and legal audit only under an approved retention schedule.
- Financial references may themselves be personal data. Classify/encrypt/restrict them; do not label all provider IDs anonymous. Non-user-derived subject IDs with detached mappings are proposed pseudonymization, not proof of irreversible anonymization. The exact anonymization/retention design is **Approval required** (Q16/L05). Never create a new undeclared erasure exception for platform records.
- Erasure must not cascade-delete bookings, financial postings, refunds, payouts or audit evidence. Coordinate outstanding refunds, disputes and provider wind-down through durable work; retry without resurrecting erased PII. A failure/unknown transfer remains an obligation for operators, not an excuse to delete evidence.
- Retention periods, legal holds, access authority and destruction schedule are **Approval required** (Q16/L05). This document does not invent statutory retention periods or claim legal compliance.

## 11. Rollback and release risks

1. Restored Mumbai schema with empty Alembic history makes naive upgrades/stamps unsafe. Prepared Supabase-specific revisions cannot simply be treated as a portable fresh-database chain.
2. Removing surcharge/configurable commission changes both amounts and provider splits. Version new policy; never rewrite historical receipts or reuse incompatible open provider orders. Rollback cannot reprice a completed capture.
3. Tightened hours/buffer/notice rules may make existing appointments invalid for new booking. Grandfather visibility, identify conflicts and require explicit owner handling; never delete them during backfill.
4. New cancellation allocations can conflict with old pending refund requests. Preserve old obligations, reserve funds, and reconcile before enabling compensation payouts.
5. Expiry enforcement can prevent receipt recording while completion requires a receipt. D08 distinguishes direct cash/UPI receipt from provider-order initiation, but is **Approval required** (Q07). History/refunds/payout access alone does not resolve it. U01 target no-cap/grace selections do not by themselves authorize code changes, legacy transition or deployment.
6. Mixed old/new API and workers can bypass payout reservations, encryption or cache invalidation semantics. Review rollout compatibility and stop new initiation when coordination cannot be guaranteed; keep reconciliation active.
7. Provider call success followed by local failure must recover from stable references. No automatic retry with a new transfer/refund ID after timeout. Never downgrade away evidence of money already moved.
8. Rollback may disable new checkout/holds/scheduling but must retain financial projections, ledger evidence, encryption reads, webhook verification and obligation reconciliation. Prefer a reviewed forward repair after new financial rows exist.
9. Provider capabilities and business eligibility are separate. Easy Split availability does not prove settlement can wait for completion/hold. Do not enable a flow that automatically settles earlier than C05 permits.
10. Snapshot immutability must coexist with privacy erasure: separate financial facts from erasable PII. An indiscriminate immutable full-payload audit would prevent required scrubbing.

Later verification must cover Decimal conservation/rounding, policy boundaries, calendar month ends, expiry and existing bookings, independent booking transactions, real isolated Redis outages/restarts/multiple workers, duplicate webhooks/transfers, failed/unknown/reversed payouts, fee reconciliation, ownership/MFA/RLS/effective privileges, encryption/rotation and erasure. Mock tests prove local logic only; Cashfree payout/refund/settlement claims require separate sandbox evidence. No tests or runtime checks are executed by this specification phase.

U02 accounting risks: choosing the wrong fee branch changes both salon entitlement
and platform margin; double-deducting provider costs, treating unknown as zero or
ignoring fees above captured funds breaks conservation. No-refund business terms
still require Q23/L01 legal review and cannot erase later valid disputes. Offer
expiry/order capture and report event-time/recognition differences can misstate
revenue; preserve old invoice/period and policy snapshots with explicit true-ups.

U02 security risks: broad admin labels cannot grant payout/offer authority; enforce
current scoped permissions, MFA, independent review and immutable audit under
Q20. Internal percentages/formulas/margins can leak through API fields, exports,
caches, replay, notifications and unsanitized messages even if hidden in the UI.
Encryption/tokenization still needs reviewed keys, restricted decryptors, old-copy
cleanup and finite lawful retention. No design here proves runtime enforcement.

## 12. Frontend handoff requirements

After backend implementation and tests, provide a versioned route/status/error matrix with request/response examples, required auth/idempotency, async polling/retry rules and deprecated-field mappings. Unapproved contract designs are **Approval required**, not promises to frontend consumers. Do not modify any frontend in this phase.

- Customer: service-only total, transparent cancellation quote, refund status, hold countdown/expiry, authoritative booking conflict, reschedule status, inactive salon message and nearby eligible alternatives.
- Owner: approved trial/paid-through/grace dates, total plan price before informational monthly equivalent, approved renewal mode, existing-booking/receipt permissions, allowed payout schedules and limitations, provisional/reconciled earnings, holds/payout status, staff commission and closure conflicts. U01 selects no-cap trial, seven-day restricted grace and a 48-hour completion hold; expose only implemented/verified states, never a guaranteed release date. For cancellation owner reports, exclude platform percentage/formula and use Q21 projection only.
- Admin/finance: onboarding information requests, payout eligibility explanation, approval versus confirmed transfer, dispute workflow, component provider charges, correction reason/audit ID and support messages.
- Staff: assigned booking/service work and approved own commission history only; no customer personal details in financial history, bank secrets or platform finance controls.
- Clients never infer success from SDK callback, cache contents, hold possession or HTTP 202. Never send provider secrets or trust client-submitted rates, roles, prices or net amounts.
- Handoff must explicitly distinguish requested new status names from existing enums; it must identify Cashfree items still unverified and carry synthetic success/conflict/failure examples. It cannot advertise weekend payouts, auto-renewal or settlement timing without approval/evidence.

## 13. Exact questions requiring owner approval

Each row below distinguishes selected U01-U04 scopes from remaining **Approval required** subquestions. Recommendations and examples do not supply missing answers. Approval must identify the question/decision ID, selected policy/values, approver and effective version/date, including grandfathering. Provider evidence and legal/accounting sign-off are separate dependencies, not substitutes for owner approval. Do not enable a financially dependent new workflow until its questions are resolved.

| ID | Exact approval question |
| --- | --- |
| Q01 | **Partially approved U03**: Record flat-fee band at 48 hours or more, 5% at 12 to less than 48, 35% at 4 to less than 12, and zero refund below 4 hours. Resolve flat amount/base/caps under Q25, penalty recipients Q26, provider fees Q17, hold Q19 and legacy adoption without rewriting historic policy. |
| Q02 | **Partially approved U03**: No-show requires appointment start passed plus ten-minute grace, explicit owner/staff confirmation, actor/timestamp/reason and customer notification; never silently cancel. Define scoped confirmer authorization, appeal/correction and notification retry handling, no-show financial treatment, duplicate/excess refund and separate salon-caused refund under L01. Do not infer a no-show penalty from cancellation bands. |
| Q03 | **Partially approved U03**: Exactly 48 hours is flat-fee, exactly 12 hours is 5%, exactly 4 hours is 35%, and strictly below 4 hours is zero refund. Approve trusted receipt-time ingress, rescheduled governing start/policy, effective rollout and exception governance; no exception is selected here. |
| Q04 | **Partially approved U01/U02**: Actual provider charges reduce completed-service salon payout. Approve each other cause/component bearer, taxes, reserve/true-up, deficit/recovery and Q17 cancellation pool choice, with P01 and L02/L03. |
| Q05 | **Partially approved U01/U02**: Retain 48 elapsed hours after service completion and no active dispute for ordinary payouts; new cancellation settlement is admin-controlled and distinct from completion. Resolve Q19 hold scope/origin/duration, Q20 authority, release/later disputes and final entitlement; never fabricate completion. |
| Q06 | **Partially approved U01**: Two-calendar-month trial has no booking cap. Confirm activation versus approval, local calendar/month-end/exclusive boundary, and legacy-salon/cap transition without restarting trials. |
| Q07 | **Partially approved U01**: Seven-day renewal grace blocks new bookings/booking-payment initiation and allows existing bookings to finish; renewal checkout remains available. Approve exact day-count/start/end/trial applicability, direct receipt permission, late captures and legacy mapping. |
| Q08 | **Approval required**: Confirm full online checkout for the approved service/cart total and whether any advance/deposit exception survives. May direct cash receipts be partial? Define handling of old surcharge orders, quote expiry and unpaid-booking release deadlines. |
| Q09 | **Approval required** for tax inclusion, benefits, subscription cancellation/paid-through/refunds and D12 manual renewal. U02 approves salon-specific offers with immutable original/discounted price, effective dates, actor/reason and final-price-only owner projection; resolve Q22 expiration/binding and Q20 authority. No recurring mandate is authorized. |
| Q10 | **Partially approved U01**: No cancelled-booking service commission and immutable booked snapshot source. Approve gross/net basis, rate/rule selection, earning event, precedence/weights, no-show, reversals, separately typed time compensation and authorized recovery under L04. |
| Q11 | **Approval required**: Specify buffer/minimum notice/same-day cutoff values and scope, overnight/recurring closures, and post-expiry reschedule/repricing policy. No unstated numeric defaults. |
| Q12 | **Partially approved U05**: PostgreSQL availability and SQL-only booking fallback are selected when Redis is unavailable; never require unavailable Redis to commit cancellation or fabricate hold success. Are healthy holds mandatory, and what actor/churn/renewal limits apply? Review operational outage recovery under Q28/Q30. |
| Q13 | **Partially approved U02**: Admin controls cancellation payout approval/timing and custom offers, but concrete admin roles/stages/scopes/limits and D11 model remain open under Q20. Define independent transfer evidence, automation, audit durability and dispute/reversal/correction authority; common manual/automatic checks remain mandatory. |
| Q14 | **Approval required** plus Cashfree confirmation P01-P06: Select verified products/account capabilities/schedules and demonstrate delayed settlement/manual funding without double payout, informed by L03. Keep activation blocked until sandbox evidence exists. |
| Q15 | **Partially approved U01**: Encrypt/tokenize payout data; no plaintext raw credentials. Select concrete solution, decryptor/rotation authority and reviewed plaintext/replica/backup cleanup under P04/L05. |
| Q16 | **Approval required**: Approve retention/erasure, legal holds, provider references/keys, unresolved obligation handoff and post-payout funding/recovery. Include U02 cancellation/report/offer evidence under Q24/L05; no statutory period is invented. |

### 13.1 Additional U02 approval questions

These U02 questions remain recorded with U03 updates: Q17 still leaves provider
fees open; Q18 now records the selected 35% band at equality while base/net refund
mechanics remain open. Other unresolved role, hold, offer, legal and privacy
questions are not approved by U03.

| ID | Exact approval question |
| --- | --- |
| Q17 | **Approval required**: How are provider fees treated in each U03 cancellation band and any no-show financial policy: reduce retained funds, reduce a beneficiary share, or platform-absorbed? Define actual cost/tax evidence, reserve, true-up and deficit funding; Q26 beneficiaries are unresolved and historical U02 70/30 cannot select them. |
| Q18 | **Partially approved U03**: Exactly four hours is in the 35% penalty band, not the below-four-hour zero-refund band. Approve the percentage base, rounding/caps and actual refundable balance under Q25/Q17; do not assume an extra full refund, a zero refund or a fixed net cash amount. |
| Q19 | **Approval required**: What dispute-hold duration and start event govern cancellation settlement? Is any prospective change requested to U01's 48-hour completed-service hold? Define dispute scope/release/later claims without rewriting historical holds. |
| Q20 | **Approval required**: Which admin payout approval roles, permission scopes, amount limits, independent stages and automated delegation may approve and schedule cancellation payouts or custom offers? Approval/timing cannot bypass common financial checks. |
| Q21 | **Approval required**: Approve the owner-visible payout allowlist (eligible amount, status, payout date, admin message), exact scheduled/actual date semantics, message sanitization and history/export scope. Platform percentage and internal formula remain forbidden. |
| Q22 | **Approval required**: What offer duration, timezone and expiration boundary apply? Define overlap/precedence, revocation, existing quote/order expiry and final checkout price binding; no old invoice/subscription may be repriced. |
| Q23 | **Approval required**: What legal wording, advance notice, customer consent, dispute/statutory remedy and cause scope are required for zero-refund late cancellation? Product approval does not establish enforceability or override mandatory rights. |
| Q24 | **Approval required**: What financial retention and erasure rules cover cancellation allocation, reports, payout/audit history and offer actor/reason/price evidence? Define lawful basis, durations/holds, access, scrubbing, backup/key destruction and open-obligation handoff with Q16/L05. |

### 13.2 Additional U03 monetary decisions

| ID | Exact approval question |
| --- | --- |
| Q25 | **Approval required**: What exact flat cancellation fee applies at 48 hours or more? Define currency, percentage penalty base for the 5%/35% bands, rounding/caps, partial/unpaid captures and refund calculation without negative refund or double provider-fee deduction. |
| Q26 | **Approval required**: Who receives each cancellation penalty or retained amount in every U03 band, including below-four-hour zero refund? Specify beneficiary, allocation and funding authority per band; do not inherit U02 70/30 or invent staff compensation. |

### 13.3 U04 cancellation and recovery review

| ID | Exact approval question |
| --- | --- |
| Q27 | **Partially approved U05**: Customer cancellation is forbidden after check-in; owner/scoped admin checked-in cancellation requires reason and atomic audit. Approve remaining scope/consent/state/replay enforcement, preserving completed/no_show/rejected prohibitions and no duplicate effects. Monetary treatment is Q29; no staff checked-in grant is selected. |
| Q28 | **Partially approved U05**: Durable database outbox invalidation/retry, independent cancellation commit and fresh PostgreSQL/SQL-only outage fallback are selected. Review exact storage, lease/fencing, dead-letter/repair, primary-read/cache-generation validation, safe hold cleanup and notification scope. Numeric retry budgets/alerts and recovery access are Q30. |

### 13.4 U05 remaining review decisions

| ID | Exact approval question |
| --- | --- |
| Q29 | **Approval required**: For owner/admin checked-in cancellation, choose cause-specific customer refund/partial-service remedy, fee bearer, fund reservation, beneficiary and payout hold/release with legal review. Do not apply U03 pre-start customer penalties or U02 70/30 automatically; define already-paid or uncertain transfer recovery without automatic bank debit. |
| Q30 | **Approval required**: Select outbox retry/backoff/jitter bounds, lease duration, attempt/age budget, dead-letter alert/response targets and scoped repair authority. Review repair/replay evidence and optional cache-fence representation; no numeric limit, new schema or deployment is chosen by this review. |

### 13.5 Final technical approval defaults - recommendations only

Prepared 2026-10-19 (Asia/Calcutta). **Every TA01-TA10 item is Approval required.**
The user authorized documenting recommended defaults, not approving their values,
creating infrastructure, configuring services or implementing them. No approver,
selected technical package, rollout date or environment is recorded. Earlier
U01-U05 evidence remains historical business direction; repeating an aligned
restriction here does not supply new technical approval or revoke earlier facts.
In particular, the additional owner-to-admin approval gate below is a proposal,
not a silently approved extension of U05 owner cancellation authority. These
technical IDs supplement Q15/Q16/Q20/Q24/Q27-Q30; they do not resolve them.

The full decision/alternative/consequence/owner/dependency record is in the
[final technical approval register](../migrations/payment-subscription-booking-designs/APPROVAL_REGISTER.md#final-technical-approval-defaults---recommendations-only).

| ID | Topic | Recommended default / approval boundary | Status |
| --- | --- | --- | --- |
| TA01 | Checked-in monetary remedy | Manual finance/legal remedy review; restrict affected captured funds from new payout while undecided. Reserve/dispatch only an explicitly approved, capture-capped refund asynchronously. No automatic zero/full refund, customer late penalty, 70/30 payout or bank debit. No monetary amount recommended without cause/partial-service policy. | Approval required: Q29/Q17/Q19/Q25/Q26/L01-L03. |
| TA02 | Owner/admin cancellation authority | Customer cancellation after check-in forbidden; owner submits a reasoned request requiring scoped admin approval before actual cancellation. Admin cancellation/approval requires reason and atomic audit; no new staff or finance grant. Request alone leaves booking checked_in/occupied until valid approved cancellation commits. | Approval required: extra admin gate and exact scopes/stages/independence Q20/Q27; prior U05 restriction is preserved as evidence, not approval of this package. |
| TA03 | Retry count/backoff | Five retries after the initial dispatch, with delays 1m, 5m, 30m, 2h, 12h from the preceding failed attempt. Proposed interpretation is up to six total dispatch attempts, not five total. Permanent validation errors may dead-letter earlier. | Approval required: Q30 must confirm retry-count interpretation, failure accounting, jitter/age budget and timeout classification. |
| TA04 | Outbox lease | Five-minute lease per delivery claim, database time and fencing identity. No booking/payment row locks during external I/O; stale worker cannot acknowledge or overwrite a new lease. | Approval required: timeout/heartbeat/renewal, crash reclaim and clock details Q28/Q30. |
| TA05 | Dead-letter | Durable retained failed-delivery state on retry exhaustion or permanent error, with attempt/source history and alert. Stop automatic poison-job retries; continue primary fallback and financial reconciliation. Audited repair/requeue uses original logical identity; dead-letter is not completion or deletion. | Approval required: classification, repair/requeue budget and evidence Q28/Q30. |
| TA06 | Alert targets | Sentry plus admin email for dead-letter and recovery incidents; sanitized job/source IDs, failure class and correlation only. Neither channel receives credentials, hold tokens, bank details or raw payloads. | Approval required: recipients/on-call routing, escalation/dedup/response targets, channel data retention and delivery Q20/Q24/Q30. No Sentry project or address is configured. |
| TA07 | Repair authorization | Scoped finance/admin repair access with two-person approval by distinct current authorized people; no self-approval. Repair limited to targeted invalidation, canonical rebuild and original-job requeue; no refund/transfer initiation, financial edits, global flush or cancellation reversal. | Approval required: named permissions/actors, separation of proposer/approver/executor, MFA, emergency procedure and limits Q13/Q20/Q30. Role label alone grants no access. |
| TA08 | Outbox retention | 90 days for successfully delivered or verified superseded operational delivery evidence, measured from that terminal resolution, not creation. Unresolved/dead-letter/legal-hold items require restricted exception review, not automatic 90-day disposal or unbounded retention. | Approval required: start clock, lawful basis, cleanup/erasure, backups, open-obligation exceptions and dedup continuity Q16/Q24/L05. No new financial-row hard-delete permission. |
| TA09 | Financial audit retention | Separate finite legal/finance-approved schedule by field/purpose; preserve necessary accounting/source facts and minimize/scrub identifying details under reviewed erasure. No numerical audit duration proposed; do not inherit 90-day outbox window. | Approval required: lawful duration, holds/reviews, actor/reason evidence, access and destruction Q16/Q24/L02/L05. |
| TA10 | Encryption/key-management storage | Managed authenticated envelope encryption or adequate provider tokenization; encrypted restricted payload and key/version reference in database, wrapping/master keys in separately managed KMS, provider/application secrets in a managed secret store. No plaintext payout credentials, raw keys or secrets in tables, Git, logs, outboxes, cache, replay or backups. | Approval required: concrete KMS/secret/tokenization products, region, access/decryptors, rotation, key recovery/destruction, backup handling and plaintext transition Q15/P04/L05. No key/credential access or service provisioning. |

Retry-budget interpretation: the proposed five-delay schedule applies once per
original logical delivery. Persist attempt start before dispatch; timeout, lost
acknowledgement or crashed/abandoned dispatch retains attempt history and consumes
its recorded budget position, rather than silently resetting on lease reclaim.
Success acknowledges only the current fenced lease; delivery remains at-least-once
and idempotent, not exactly-once network execution. Do not call the delays an
approved exponential/jitter formula: this proposed discrete schedule and any
jitter/absolute-age cap require explicit Q30 selection. Manual repair cannot
silently restart an unlimited retry cycle; approve/audit any new bounded cycle.

Lease safety: external action timeouts must fit the approved lease/revalidation
strategy. Optional heartbeat/renewal is not selected by five minutes alone.
After expiry a stale worker may finish network work, so side effects must remain
idempotent/generation-safe and acknowledgement fenced; a lease does not by
itself cancel network I/O or protect newer Redis holds.

Retention boundary: 90 days is a proposed operational delivery window only.
Keep required minimal dedup/source linkage under its own approved schedule before
scrubbing payloads; loss of outbox history must not permit duplicate booking,
refund or transfer. Pending/unknown/dead-letter jobs cannot disappear while
obligations remain; assign a named lawful exception/periodic review and minimized
handoff rather than invent indefinite retention. Do not reuse financial audit
facts as a raw payload archive. Current historical finance/erasure protections
remain, and no cleanup/backfill/key destruction occurs in this phase.

Approval must name TA ID, selected values, reviewer/evidence, current roles and
scopes, effective version/environment, legacy/open-job treatment and dependent
legal/security/provider conditions. Until explicit sign-off, recommended values
stay inert and are not configuration fallbacks. The customer/admin restrictions
listed here do not authorize any runtime change or new endpoint.

## 14. Phase 1 exit criteria

Only this specification, approval register, cancellation design, slot-hold/concurrency design and the existing closure/reschedule availability design are revised. Run only Markdown link/anchor, numbering and whitespace checks; no app imports, tests/lint, SQL/revision checks, database/Redis/provider access or infrastructure operations.

The document separates owner-approved rules, recommended defaults, Cashfree-dependent confirmation and legal/accounting review, with every pending item labeled **Approval required**. U04 approves immediate slot release after valid committed cancellation, not proposed actor/state/storage details or implementation. U03 bands and the no-show process select business scope only; exact flat fee, beneficiaries, dispute hold and provider fees remain open. Review does not authorize Phase 2, live/provider operations, shared-state changes or deployment. Stop after this revision and report file changed, unresolved decisions, recommendations, risks and documentation-only checks. No commit or push is authorized.
