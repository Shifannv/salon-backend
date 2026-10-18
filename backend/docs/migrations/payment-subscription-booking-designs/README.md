# Payment, subscription and booking migration designs

Revised 2026-10-19 (Asia/Calcutta). **Design review only; not execution-ready.**

These nine provisional review groups use the
[payment-subscription-booking specification](../../verification/payment-subscription-booking-spec.md)
and [Mumbai reconciliation report](../MUMBAI_SCHEMA_HISTORY_RECONCILIATION_2026-10-18.md).
The reconciliation report remains a preserved historical input. This authorized
U02 documentation update also revises the specification and approval register.
Owner-approved C01-C21 scopes do not resolve remaining Q01-Q24 subquestions,
provider P01-P06 or legal/accounting L01-L05. No missing value becomes a default.

## U02 business-policy update and precedence

[Specification](../../verification/payment-subscription-booking-spec.md#4-cancellation-allocation-and-refunds-decision-gate)
and [approval record U02](APPROVAL_REGISTER.md#policy-approval-record-u02) govern
current target policy. U01 refund-first/20%-platform/80%-salon is superseded only
for newly governed late cancellations; historical policies never change. New
late cancellation is strictly less than four hours before start, equality on-time
unless explicitly marked otherwise, zero customer refund and 70% salon / 30%
platform distributable split. Provider fees remain separate; requested captured
less approved costs pool versus platform absorption is explicitly pending Q17.
Equality refund is Q18; cancellation hold and admin roles are Q19/Q20.

Admin controls cancellation approval/timing and receives payout/report/audit and
custom-offer capabilities. Owner must not receive platform percentage/formula;
exact eligible-amount/status/date/message projection remains Q21. Salon offers
preserve original/discounted price, effective dates, actor/reason and unchanged
default plan/old invoices/subscriptions. Owner receives only final payable offer
price, no margin; duration/expiration is Q22, legal no-refund wording Q23 and
retention/erasure Q24. These directions select business scope, not implemented
permissions, schema, provider capability or execution. G03/G04/G07 reflect the
new requirements; exact offer persistence design/artifacts remain later review.

U01's ordinary 48-hour completion hold, uncapped two-calendar-month trial,
restricted seven-day renewal grace, zero completed-service platform commission,
completed-service actual-cost bearer, staff cancellation exclusion and immutable
snapshots, and payout-data encryption remain selected scopes. Exact calendar/
legacy/receipt and key details remain open. Cancellation has its own hold/origin;
no fabricated completed service or automatic use of the ordinary hold is allowed.

Only the specification, approval register and directly affected design Markdown
change in this task. No runtime policy change occurs. No SQL, Alembic command, executable
revision/sidecar, database/provider access, approval manifest, executable policy change,
deployment, commit or push is authorized. Existing provider-independent ports
and [isolated fake evidence](../../verification/provider-agnostic-mock-results-2026-10-18.md)
remain separate; mock observations cannot verify real money or provider capability.

## Reconciliation evidence and remaining gate

The report completed read-only inspection of Mumbai staging only:
public.alembic_version had zero rows; four Supabase restore/hardening history
entries existed; 44 public tables and 52 application functions were observed;
all 43 previously proposed new tables were absent. Prepared 0040 effects
appeared present but independent expected-PG17-0040 equivalence and historical
backfill provenance were not established. No applied Alembic revision or
executable starting point is certified.

This phase reads that report locally. It does not repeat live inspection or
promote static source head to applied state. Source graph remains 40 revisions,
with prepared head `0040_fastapi_only_access`; portable CI remains limited to
`0037_customer_processing_charge`. Empty restored history still fails the
[Mumbai policy](../MIGRATION_POLICY.md); no stamp, replay or guard removal is
permitted. Reconciliation/history approval and independent reference proof
remain gates before executable preparation/execution.

Historical pre-U02 specification input SHA-256 (not the current revised file):
`0771fae99607a4cb35e82a07d592e58a2332622f72c4e3bbe67c027264c37965`.
Historical command/restore evidence stays in the report and sealed review files;
no new runtime, settings or environment read occurs here.

## Revised provisional review order

G01-G09 are **review-group labels**, distinct from the specification's D01-D15
recommended policy decisions. They are not Alembic IDs, parent values or an
executable chain. Historical numeric filenames remain stable link locators and
do not assign deployment order. Previous proposed IDs/parents are withdrawn
from this active bundle; no replacement revision IDs are assigned.

| Order | Group and design | Schema dependency / staged ownership |
| --- | --- | --- |
| 1 | [G01 — Audit and authority foundation](0048-admin-financial-audit.md) | Existing approved parent tables only; commands, authority, audit/seals, approval contexts and financial-event envelope; no future payout FK |
| 2 | [G02 — Provider-fee reconciliation](0041-provider-fee-reconciliation.md) | G01; adds charge evidence/allocations, postings and balanced accounting seals to G01 financial_events |
| 3 | [G03 — Cancellation policy and refund obligations](0042-cancellation-policy-versions.md) | G01/G02; immutable terms/outcomes, logical refund caps and delivery bindings |
| 4 | [G04 — Payout/dispute records](0043-payout-dispute-records.md) | G01-G03; installs typed payout/destination/dispute audit and approval-generation links after those parents exist |
| 5 | [G05 — Payout schedules](0044-payout-schedules.md) | G01/G04; capability/schedule/restriction identity and command audit |
| 6 | [G06 — Staff commission ledger](0045-staff-commission-ledger.md) | G01/G02 and existing refund authority; G03 where cancellation bindings apply |
| 7 | [G07 — Subscription lifecycle](0046-subscription-lifecycle.md) | G01 plus existing purchase/access authority; G02 for accounting effects |
| 8 | [G08 — Closure/reschedule support](0047-business-closure-reschedule.md) | G01/G03/G07 and applicable G02/G04 financial effects; common G09 guards before activation |
| 9 | [G09 — Slot-hold and concurrency support](09-slot-hold-concurrency-support.md) | Reuses existing/G08 booking state; integrates common locks/SQL guards across G01-G08 and ephemeral Redis coordination; no permanent hold table |

[ERASURE_CLASSIFICATION.md](ERASURE_CLASSIFICATION.md) is the shared exact
43-field treatment design. It does not add a tenth migration group.

## Foundation, integration and activation order

G01 now owns the `financial_events` identity/envelope formerly described in the
fee group. G02 owns `financial_postings` and `financial_event_finalizations`;
G01's `financial_audit_finalizations` seals audit assertions, not balances or
provider movement. G01 also proposes `financial_command_identities` for immutable
command/replay scope. The revised bundle therefore describes **45 distinct new
tables** (43 prior proposals plus two foundation tables), not 45 inspected or
implemented objects. G09 adds no permanent table.

Early G01 approval tables have command/stage/execution context without FKs to
future payouts/destinations. G04 installs those typed columns/composite FKs and
generation bindings once its parents exist. G05/G07/G08 install their mandatory
command audit links; G03/G06 corrections use G01/G02 event linkage. Optional
historical NULLs never authorize newly governed actions. Each owner group must
validate its exact same-command/source/salon/currency/environment bindings.

The global locking/concurrency contract applies from the first new writer.
G09 is last in review order, not permission to postpone safety. Implementation
may require an approved early helper split and later integration; final artifact
boundaries and exact table ranks are **Approval required**. No G01 financial-event
writer activates before G02 accounting seals, and no financial/approval/schedule
writer activates before applicable G09 guards, typed links, authority separation,
erasure treatment and required audit are installed and verified.

A server-enforced schema/audit capability gate must reject incomplete new-mode
initiation/finalization; feature flags alone are insufficient. Old/new API and
workers must be coordinated. Verified incoming money/refund observations still
need durable receipt and original-operation reconciliation when new commands
are disabled. Reordering is no execution or history approval.

## Shared design conventions

Each design inherits these rules in addition to its own security/erasure section.
All names, types and constraints below are proposals awaiting implementation review.

- New tables live in `public`, with UUID primary keys generated using the existing
  `gen_random_uuid()` convention. No new extension is proposed. Existing
  `btree_gist` supports the proposed temporal exclusions; verify availability later.
- Each table has `created_at timestamptz NOT NULL` with database time. Mutable
  projections also have `updated_at timestamptz NOT NULL`, `row_version integer
  NOT NULL DEFAULT 1` (positive, distinct from a policy/version sequence)
  for compare-and-swap, and the existing timestamp/audit convention where its
  column shape matches. Append-only tables have no mutable financial columns.
- A column is NOT NULL unless marked `?` (nullable). `id` is implicit on every
  new table unless a different primary key is stated. References identify exact
  parents; all new non-profile financial FKs use explicit `ON DELETE RESTRICT`
  unless the design says otherwise. No financial cascade deletion.
- All new `actor_id`, `approved_by`, `requested_by` and similar identity columns
  are nullable UUID FKs to `profiles(id)`, explicitly `ON DELETE NO ACTION`.
  They are indexed and cleared before profile deletion by the existing
  `erase_profile_references(uuid)` single-column-FK mechanism. Update erasure
  inventories/tests; do not assume FK detachment scrubs text or evidence.
- Money uses `numeric(18,2)`, INR, explicit finite nonnegative/positive checks,
  and Decimal/half-up paise rounding. Signed postings use a separate direction
  and positive magnitude. Legacy `numeric(10,2)` columns stay unchanged; reject
  linked values outside their bounds rather than truncating. Rates use
  `numeric(7,4)` or integer basis points with explicit bounds, never floats.
- `text` state columns use named allowlist CHECKs, not new Postgres enum values.
  UUIDs, finite amounts, states and timestamps require explicit nullability.
  Every optional reference has a named FK and index. Composite cross-salon
  consistency uses parent composite unique keys/FKs where possible; otherwise
  a documented locking trigger validates the relationship. A CHECK cannot
  enforce a cross-row sum, another table's state, timezone validity or authority.
- Financial corrections append a linked reversal/replacement event. An
  update/delete guard protects facts; narrowly permitted erasure only nulls
  identity FKs or scrubs separate sensitive data, never amounts, dates, policy
  facts, financial-parent source links or outcomes. The only additional operational
  detach exceptions here are G03 `booking_cancellation_outcomes.action_request_id`
  and G08 `business_closure_operations.holiday_id`/`blocked_slot_id`, which may
  become NULL when those erasable operational parents are deleted. Their other
  facts/financial links remain unchanged. Guards must compare every other column
  and verify the reviewed erasure path; a session flag alone is not authority.
- Policies, rules and schedule configurations use `is_active boolean` for soft
  retirement. Evidence/ledger records are never hidden from totals by an
  `is_active` switch. Mutable operational statuses do not erase original events.

## RLS and effective privileges

Retained Mumbai evidence: all 44 tables have RLS; client application-table,
column and app-function rights were zero. service_role had broad mutation and
TRUNCATE/TRIGGER rights with BYPASSRLS; postgres owned objects and bypassed RLS.
No dedicated API/accounting/executor/erasure principal was identified; deployed
runtime identity was not established. FORCE RLS does not constrain BYPASSRLS.
postgres and supabase_admin creator defaults differ; the latter can reintroduce
client rights. Existing extension function exclusions and managed-role ACLs are
not a reason for sweeping revocations. **Approval required** for the concrete
principal/entry-point/privilege separation; no least-privilege enforcement is
claimed while new finance writers use owner/bypass credentials with broad rights.
No new realtime financial/evidence publication is proposed. These observations
are from the report, not a fresh database check in this phase.

Enable RLS and revoke all privileges from `PUBLIC`, `anon` and `authenticated`
on every new table in the same future migration. Do not add browser policies or
Data API grants. Explicitly review inherited/default ACLs on new objects, sequence
rights if any, schema rights, triggers, functions, views and server roles. Table
RLS and SQL grants are separate controls; see [Supabase RLS guidance](https://supabase.com/docs/guides/database/postgres/row-level-security).

Use the existing backend role only after verifying its effective rights. A
privileged/table-owner connection may bypass RLS; therefore RLS alone is not proof
of tenant isolation or immutable ledgers. Authorize current DB profile roles and
ownership in use cases; scope repositories; derive actor context from verified
JWTs. No new role or unconditional server `GRANT ALL` is assumed by these designs.
Prefer invoker functions with pinned search paths; revoke function execution
from client roles and `PUBLIC`. No new SECURITY DEFINER bypass is proposed.
An existing definer function may only be replaced after its caller/privilege
contract is reviewed. No new public views are required.

## Minimum-rights contract

These are proposed least-privilege ceilings, not new grants, existing rights or
approval of finance delegation. **Approval required** (Q13) for actors, scope,
limits, stage policy, automation and authority-management procedures. Until then,
new sensitive commands fail closed. `finance` is a proposed permission assignment
from current profiles/authority records, not a new DB/JWT role. All human access
below is through scoped backend use cases; customer/owner/staff/finance/admin
receive no SQL grants on the new tables.

| Principal | Permitted ceiling after required approval | Forbidden by default |
| --- | --- | --- |
| Customer | Own sanitized booking, payment/refund/dispute status; own eligible cancellation/reschedule requests | Accounting writes, fee evidence, payout approval/execution, destination secrets, staff/other-customer finance |
| Owner | Own salon reports, staff-rule proposals, supported schedule selection, permitted refunds/closures and renewal commands | Cross-salon access, arbitrary actual fees, accounting finalization, finance delegation, platform payout approval or erasure overrides |
| Staff | Assigned operational work and, if approved, own sanitized commission history | Customer PII in finance reports, payout/destination controls, platform finance or authority management |
| Finance delegate | Only named permissions such as `accounting.finalize`, `payout.approve`, `dispute.resolve`, restricted by salon, amount and approval stages; MFA for admin-finance actions | Self-granting, self-verifying evidence, direct ledger edits/deletes, unrelated scopes or privacy override |
| Super admin | Approved permission-specific financial review/authority administration with verified `aal2`, reason and audit | Implicit unlimited finance rights from role alone, self-elevation, bypass of holds/reservations/independent review |
| Ordinary API service | Approved scoped reads; append command intent through reviewed entry points; safe projection updates | Grant/revoke authority, blanket table mutation, direct finalized-posting insertion, financial hard delete |
| Accounting worker | Finalize only evidence-backed, conserved events through guarded finalization operations; append provider outcomes/reconciliation | Human payout approval, authority changes, PII scrub, provider-capability invention |
| Payout executor | Submit the exact approved, reserved execution generation; reconcile the same external operation | Approve its own generation, change amount/destination, select another funding product or retry an unknown transfer under a new ID |
| Erasure worker | Only classified identity/payload scrubbing and operational detachments in a verified deletion request | Change amount, source financial links, policy/outcome facts, authority grants or fabricate transfer/refund finality |
| Supabase `service_role` / database owner | Administrative capability must be inventoried and isolated; not a human finance principal | No claim that RLS or a broad credential alone enforces any of the ceilings above |

Accounting finalization requires the named `accounting.finalize` authority or a
separately approved reconciliation-worker authority and the same evidence guards.
Payout approval requires `payout.approve` under Q13's approved stages; executor
credentials confer no approval. Only the erasure worker may perform the narrow
scrub, after validating deletion/retention authority. Authority changes require
`authority.manage`, an audited current grantor and Q13's bootstrap/independence
procedure; no self-grant/self-expansion or inferred authority from JWT metadata.
No eligible grantor/bootstrap policy means the command remains disabled.

Future SQL rights must distinguish reads, staging append, finalization, execution
and erasure. Revoke direct UPDATE/DELETE/TRUNCATE on immutable facts and direct
INSERT on finalized children from ordinary runtime principals; restrict mutable
updates to named projection columns. Invoker entry points still require their
caller's underlying rights: if exact required rights cannot be separated using
reviewed privileges/guards, block enablement and review a narrowly scoped adapter
or privilege design rather than quietly add SECURITY DEFINER or GRANT ALL.
Do not change Supabase-managed roles here. If runtime credentials remain owner or
BYPASSRLS credentials, record that residual risk and require a reviewed separation
plan before claiming least-privilege enforcement. No blanket service-role grant
is authorized by this document.

## Provider provenance contract

Every provider-derived charge, posting, entitlement, destination capability and
execution generation must bind immutable `provider`, `provider_account_scope`,
`provider_environment` (mock/sandbox/live) and provenance. Account scope is an
internal identity namespace, not proof of an account or FK to erasable onboarding
rows. It is unique per provider/account/environment. Mock scopes cannot be
relabelled or linked to a real scope. Internal cash/adjustment events have a
separate `internal` origin and cannot masquerade as provider observations.

Only trusted ingestion/statement-review entry points may attest
`provider_observed` provenance, with source integrity evidence and a named
verification method/authority. A client body, synthetic reference, non-NULL
ciphertext, caller-supplied label, or `provider_verified=true` is not attestation.
Sandbox evidence can support sandbox verification only; it is not live settlement.
Mock evidence is immutable `mock`, remains in isolated test namespaces, and cannot
finalize provider-actual fees, fund real entitlements, verify KYC/capabilities or
confirm a real payout. All source/event/posting/payout joins must preserve scope,
environment and origin. Unknown provenance fails real financial eligibility.
**Approval required** (P01-P06/Q14) for provider-specific evidence mappings and
capabilities; no live/account-dependent predicate is satisfied by these designs.

## Privacy and account erasure

The [43-field treatment design](ERASURE_CLASSIFICATION.md) assigns one proposed
primary category to every unresolved field identified in the Mumbai report:
26 retain, 6 anonymize, 3 delete, 3 encrypt, 2 digest only and 3 conditional
provider-required retention. **Approval required** applies to all 43 entries.
This does not update runtime erasure, COLUMN_TREATMENT or existing snapshot guards.
Every new field in G01-G09 also needs explicit classification before implementation.

The [account deletion workflow](../../ACCOUNT_DELETION.md) retains inert salons,
bookings and financial facts, while deleting provider-account mappings and payout
details. New references must not prevent those existing erasure steps. Each
design specifies its exceptions to the default RESTRICT rule.

Separate erasable explanation/contact data and restricted encrypted provider
evidence from immutable accounting facts. Never persist raw webhooks, bank
details, KYC, tokens or customer/staff names in these ledgers. Internal detached
UUIDs and keyed provider-reference digests are **pseudonymous**, not proven
anonymous. Q15/Q16/L05 must approve encryption, lawful retention, legal holds,
eventual anonymization and key destruction. No design creates a new legal
exception or indefinite retention entitlement. Existing immutability triggers
that allow `app.account_erasure` need an explicit column-level review.

Identity detachment and operational SET NULL exceptions never clear a financial
source/binding. Sensitive evidence/digest scrubbing needs an explicit per-column
plan under Q15/Q16/L05 (**Approval required**), including legal holds, key rotation,
backups and uniqueness/deduplication after anonymization. Do not destroy a digest
key and thereby permit duplicate transfers; retain a restricted lawful linkage
or another approved deduplication mechanism. Do not call pseudonymous UUIDs or
encrypted references anonymous. These corrections authorize no data retention
period or new hard-delete exception.

## Shared lock-order contract

G09 owns verification/integration of this cross-cutting contract even though it
is reviewed last. No earlier writer activates before it complies. The exact
per-table rank map, FK/unique/trigger lock review and shared helper split are
**Approval required** before executable preparation.

This is the required future mutation contract, not a statement that current
functions/repositories implement it. All workflows use the same helper/ordering;
local per-design locking descriptions below inherit it and may not invert it.
Read-only slot queries need no reservation lock and remain nonbinding snapshots.

1. Read identifiers without row locks to discover the complete affected set.
   Acquire transaction advisory profile gates for all acting/deleting/affected
   identities, sorted by UUID, using the namespace `profile:<uuid>`, hash seed 0.
   These gates serialize profile deactivation and authority changes with use.
2. Acquire any applicable existing per-customer booking guard locks, UUID-sorted,
   using the existing customer UUID text and hash seed 3715. Never acquire these
   for the first time from a late booking trigger after salon/row locks.
3. Acquire every affected salon advisory lock, UUID-sorted, using the existing
   salon UUID text and hash seed 0. Then acquire `subscription:<salon_uuid>` locks
   with seed 0, in the same salon order, for all affected salon mutations. This
   explicitly coordinates the currently distinct closure/subscription namespaces.
4. Acquire provider funding-scope advisory locks, sorted by canonical
   `(provider, environment, account_scope)`; namespace
   `funding:<provider>:<environment>:<account_scope>`, seed 0. Any multi-salon
   payout batch obtains all earlier salon keys before any funding key.
5. Acquire existing-row locks by category rank, then table name, then primary key:
   identity/authority; salon/access/subscription/billing; staff/service mapping;
   booking/schedule/closure requests; payment/cancellation/refund obligations and
   deliveries; canonical charges/components; financial events/postings;
   entitlements; payout/generation/reservation/attempt; approval/audit records.
   The implementation must publish the exact table-rank mapping before SQL review.
   Source parent and revision lineage checks happen under their category locks.
6. Revalidate ownership, active/deletion state, policy, authoritative clock/access,
   affected-set version, funds and current approval before writing. If discovery
   missed an earlier-ranked key, release/rollback and retry discovery; never add
   that lock out of order. Stale user-confirmed previews require renewed consent.
   Commit intent/reservation/audit before any external I/O. Reconciliation starts
   a fresh transaction with the same ordering and original operation identity.

Booking creation, reschedule, closure, payment/refund planning, subscription
activation/expiry/cancellation, payout and dispute transitions, authority changes
and account-deletion phases must participate. Triggers must see earlier gates
already held or be revised to acquire them before any conflicting row lock.
Workers cannot hold a claimed business row while waiting for earlier gates: use
an independently committed queue lease, then discover/lock/revalidate. Large
erasure/batch sets need a reviewed bounded-phase plan with durable progress and
the inactive-account barrier; no external call holds these locks. Legacy writers
must be coordinated before activation; retries handle deadlock/serialization
failures with stable idempotency, never a new transfer key.

## Locking, compatibility and future verification

Initial migrations should be additive and empty, with no guessed historical
backfill. Existing-table additions are nullable or metadata-only defaults after
version/size review. Build large existing-table indexes concurrently in a
separate, reviewed nontransactional step; use bounded lock/statement timeouts,
add eligible FK/CHECK constraints NOT VALID then validate separately. Unique and
exclusion constraints need their own conflict scan/build plan; NOT VALID is not
a shortcut for them. See [Postgres constraints](https://www.postgresql.org/docs/current/ddl-constraints.html).

No historical amounts/statuses/policy versions are rewritten. No arbitrary
`IF NOT EXISTS` may conceal an incompatible restored definition. Future review
must compare exact columns, FKs, functions, grants and triggers to the authorized
target before deciding which additive operation is appropriate.

Do not activate mixed writers: old payment, subscription or booking code can
bypass new semantics. Review all API/worker paths together. New money commands
need G01 audits, verified signatures/replay gates, transactionally committed
intent/reservation before external I/O and stable external operation references.
No provider call belongs inside a database row-lock transaction.

Later tests require separate authorization for a verified disposable database;
the present instruction forbids SQL even locally. Per-design verification plans
are **not executed tests**. No pytest suite is run because integration tests can
execute migrations/SQL; document checks and revision-graph inspection are the
only verification in this phase.

## Readiness and approval gates

All nine design groups are **prepared for review**, **not implemented**, **not applied**,
and **not ready for migration execution**. Required gates are:

1. Owner decisions Q01-Q16, selectively per dependent workflow; provider evidence
   P01-P06 and legal/accounting review L01-L05 remain separate approvals.
2. Design/constraint/erasure review, including Q15 encryption and Q16 retention.
3. Later authorization to write Alembic/SQL artifacts and meaningful tests.
4. Disposable-database migration/concurrency/security/erasure/downgrade evidence;
   synthetic provider sandbox checks only under separate authorization.
5. Independent Mumbai restored-history reconciliation and a target-specific
   reviewed execution plan. Existing policy does not authorize these design groups
   or a new history path; extending it needs separate review, never guard removal
   or automatic stamp.
6. Coordinated application rollout and explicit execution/deployment approval.

Rollback normally stops new initiation while preserving reconciliation, refund,
dispute, evidence and encryption reads. Never restore plaintext, broaden grants,
reprice old payments, erase obligations or cross irreversible 0040. Each design
defines the narrower empty-schema downgrade and data-bearing forward-repair path.

## Design-review record and remaining approvals

This review replaces the earlier eight-group ordering while retaining the
financial conservation, source deduplication, sealed posting, immutable snapshot,
uncertain-operation and erasure safeguards in the individual designs. It expands
the early audit contract, stages later typed links, adds G09 and proposes treatment
for all 43 existing unresolved fields. No executable migration artifacts exist
for these groups.

**Approval required** before dependent implementation:

- Q01-Q05/Q08: remaining cost/base/causes/exception/ingress, fee bearers,
  holds/reserves, funding and legacy/open-order transition. U02 late R=0,
  strict/on-time equality and 70/30 are selected; Q17/Q18 still gate costs/refunds.
- Q06-Q09: selected no-cap trial/grace calendar and legacy details, receipt access,
  late captures, checkout/deposits and subscription tax/benefits/renewal mode.
- Q10-Q12: staff basis/rules/weights/reversals, schedule/buffer/notice/cutoff and
  hold mandatory/outage/limit/renewal behavior; no unstated numeric defaults.
- Q13/Q20: actual admin actors/permissions/scopes/limits, stage and independence rules,
  bootstrap, automation, failed-audit durability and enforceable runtime rights.
- Q14/P01-P06: account-specific pricing/evidence mappings, KYC/destination,
  schedules, hold/release, finality, retry identity and duplicate-safe fund flow;
  owner approval alone cannot establish a provider capability.
- Q15/Q16/Q24/L05: every 43-field treatment and all new field classifications,
  encryption/tokenization, keys/rotation, finite retention/holds, erasure,
  backups, dedup continuity and unresolved-obligation handoff.
- Q17-Q24: fee-pool branch, equality refund, cancellation hold, admin roles,
  owner projection, offer expiration, no-refund legal wording and retention.
- L01-L04: refund/dispute terms, fee/tax/accounting recognition, permitted fund flow
  and staff compensation/recovery. No statutory rule or accounting treatment is
  silently selected by a schema proposal.
- Independent PG17 expected-head/restored-history proof and approved history
  strategy; final group/artifact dependencies and IDs only after that review.
- Exact per-table lock ranks and implicit-lock analysis, scoped FK/privilege/
  erasure design; explicit later authorization for executable files and disposable
  database tests. Database/provider access, migration/history mutation and
  deployment remain distinct later approvals.

Approvals must name decision/field/artifact, selected values, approver, effective
version/date and legacy treatment. Silence or a design recommendation is not
approval. Unresolved choices block only their dependent new workflows; existing
money and erasure obligations remain owned and reconciled.

## Verification in this phase

The U02 documentation task runs only Markdown link/anchor, numbering and
whitespace checks on the six changed Markdown files. It does not repeat earlier
AST/revision-graph, hash, secret-pattern, catalog or field-coverage inspections.
Prior static results and the historical specification hash are historical review
evidence only, not fresh checks of this revised policy bundle. No new table
count is certified for the not-yet-designed offer persistence capability.

The reconciliation report, executable migration sources/sidecars/policy,
application/tests, environment files and sealed evidence remain untouched.
No app imports, pytest/lint, SQL validation/execution, database/Redis/provider
access, migrations/stamping, infrastructure/frontend changes, deployment, commit
or push occur. Stop after documentation update; all groups remain design-only,
not implemented/applied or ready for execution.
