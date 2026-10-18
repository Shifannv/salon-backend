# G01: Audit and authority foundation

**Design only; Approval required for implementation.** First provisional review
group. No Alembic revision ID or parent is assigned. The historical filename is
retained for existing links; it no longer places auditing last. Inherits the
[shared rules](README.md), [43-field treatments](ERASURE_CLASSIFICATION.md) and
[G09 concurrency contract](09-slot-hold-concurrency-support.md).

## Purpose and compatibility

C12 requires attributed, scoped, append-only command and approval evidence before
any new financial writer. The [Mumbai report](../MUMBAI_SCHEMA_HISTORY_RECONCILIATION_2026-10-18.md)
found transition audits and broad server privileges, not this foundation.
G01 reuses existing payment/refund/purchase authority and durable response
idempotency. It supplies no new capture, refund, payout or provider finality.

This design owns the financial-event envelope previously described in the fee
group. G02 adds its postings and accounting seals. G04 adds payout/dispute/
destination-specific approval links; G05/G07/G08 add their event audit links.
The initial foundation references only existing approved parent tables and its
own tables. It does not require future payout tables or fabricate historical
approvals. All authority bootstrap and runtime-role separation is **Approval
required** Q13; no authority seed or implicit super-admin power is proposed.

## Tables and columns

All names and types are proposals. Shared UUID/timestamp/FK conventions apply.

| New table | Proposed columns in addition to shared timestamps |
| --- | --- |
| `financial_command_identities` | `command_id uuid` PK (no separate id), `operation_id uuid`, `command_kind text`, `actor_scope_key uuid` (detached internal replay namespace), `actor_id uuid?` -> profiles, `actor_kind text` (human/system), `role_snapshot text`, `scope_salon_id uuid?` -> salons, `idempotency_digest bytea`, `digest_key_version text`, `canonical_payload_digest bytea`, `payload_digest_version text`, `execution_generation integer?`, `provider text?`, `provider_account_scope uuid?`, `provider_environment text?`, `provenance text`, `correlation_id uuid`; immutable command identity, not response-cache storage |
| `financial_authority_versions` | `authority_code text`, `version integer`, `actor_id uuid?` -> profiles, `role_snapshot text`, `permission_code text`, `scope_salon_id uuid?` -> salons, `amount_limit numeric(18,2)?`, `currency text`, `dual_approval_mode text?`, `effective_from timestamptz`, `effective_to timestamptz?`, `granted_by uuid?`, `approval_reference text`, `is_active boolean`; authority scope/parameters immutable, retirement a narrow audited projection |
| `admin_financial_audit_events` | `event_key text`, `command_id uuid` -> commands, `action_code text`, `actor_id uuid?` -> profiles, `actor_kind text`, `role_snapshot text`, `permission_snapshot text`, `authority_version_id uuid?` -> authorities, `approval_generation_id uuid?` -> approval contexts, `approval_stage integer?`, `execution_generation integer?`, `reason_code text`, `salon_id uuid?` -> salons, `booking_id uuid?` -> bookings, `payment_id uuid?` -> booking_payments, `refund_id uuid?` -> payment_refunds, `financial_event_id uuid?` -> financial_events, `reference_kind text?`, `before_revision_reference uuid?`, `after_revision_reference uuid?`, `before_facts_digest bytea?`, `after_facts_digest bytea?`, `facts_digest_version text?`, `policy_reference text?`, `outcome text`, `idempotency_digest bytea`, `payload_digest bytea`, `correlation_id uuid`, `effective_at timestamptz`, `observed_at timestamptz`, `corrects_event_id uuid?` and `reverses_event_id uuid?` -> audit events |
| `financial_audit_finalizations` | `audit_event_id uuid` PK -> audit events (no separate id), `immutable_facts_digest bytea`, `digest_version text`, `finalized_at timestamptz`, `finalized_by uuid?` -> profiles; one immutable seal per audit event, including denied/pending events |
| `financial_approval_generations` | `command_id uuid` -> commands, `approval_generation integer`, `execution_generation integer?`, `payload_digest bytea`, `amount numeric(18,2)?`, `currency text`, `reservation_set_digest bytea?`, `authority_policy_version text`, `required_stage_count integer?`; immutable approval instruction, not approval itself |
| `financial_action_approvals` | `approval_generation_id uuid` -> approval contexts, `target_command_id uuid` -> commands, `approval_audit_event_id uuid` -> audit events, `authority_version_id uuid` -> authorities, `approved_amount numeric(18,2)?`, `currency text`, `approver_id uuid?`, `approval_stage integer`, `valid_until timestamptz?`, `decision text` (approved/rejected/revoked), `supersedes_approval_id uuid?` -> approvals; immutable stage decision |
| `admin_financial_audit_details` | `audit_event_id uuid` -> audit events, `sanitized_explanation_ciphertext bytea?`, `message_ciphertext bytea?`, `evidence_locator_ciphertext bytea?`, `key_version text?`, `retention_class text`, `legal_hold_reference text?`, `scrubbed_at timestamptz?`; separately restricted, erasable payload |
| `financial_events` | `salon_id uuid?` -> salons, `booking_id uuid?` -> bookings, `payment_id uuid?` -> booking_payments, `refund_id uuid?` -> payment_refunds, `event_type text`, `event_key text`, `command_id uuid` -> commands, `command_audit_event_id uuid` -> audit events, `currency text`, `provider text?`, `provider_account_scope uuid?`, `provider_environment text?`, `provenance text` (internal/mock/provider_observed), `effective_at timestamptz`, `observed_at timestamptz`, `policy_version text?`, `reverses_event_id uuid?` and `corrects_event_id uuid?` -> financial_events, `actor_id uuid?`, `correlation_id uuid`, `reason_code text`; canonical financial identity/envelope, no postings or spendable balance in G01 |

There are eight proposed foundation tables. Command IDs, audit-event IDs and
financial-event IDs have different meanings. A command may produce several
audit events and several typed financial events; event_key/source uniqueness
prevents recognizing the same economic source more than once, as refined by G02.
A financial-event UUID, command acceptance or audit seal never proves movement.

Stage the cycles explicitly: create tables, add nullable back-reference columns
only after both parents exist, validate exact same-command FKs/guards, and close
the transaction with all required audit seals. A financial event's mandatory
command_audit_event_id points to a sealed authorization/intent audit event.
Its audit event's financial_event_id is an optional outcome back-reference; a
separate subsequent sealed outcome event can reference the financial event.
No nullable legacy escape is permitted for newly governed financial events.
G01 financial-event insertion remains disabled until G02 accounting sealing and
all applicable authority/concurrency gates are installed.

## Financial identity, actor and command contract

- Financial identity is immutable event UUID plus unique non-NULL event_key,
  command, typed source and provider/account/environment/provenance. A retry
  reuses identity; receipt/channel changes cannot create a second economic event.
  G02 owns canonical charge and posting-source deduplication.
- A human command resolves its verified JWT subject to an active current profile
  and current DB role, never user metadata. Record initiating actor on the command;
  each audit event independently records its actual acting actor/role/permission,
  including a distinct approver. System commands use an explicitly approved
  system authority, not a fabricated human JWT.
- Approval attempts record permission sought and the decision basis. A denied
  attempt need not claim a valid authority_version_id; a granted action must bind
  current valid authority. Unknown/inaccessible targets are represented only by
  sanitized attempt context, never invalid FKs or existence leaks.
- command_id identifies one immutable action/payload/scope. operation_id groups
  one business operation across reviewed generations; it does not authorize a
  transfer. Typed parent binding arrives in the owning group.
- The caller's idempotency key is not stored raw here. Persist a keyed digest,
  key version and immutable actor_scope_key/command-kind namespace. Bind the
  canonical payload digest/version. Same key and payload returns the original
  command; changed payload conflicts. Never log the raw key or cache full request
  or response bodies in the immutable audit.
- Reuse the existing durable idempotency response authority. Its erasable cached
  response may disappear on deletion, but pending external-operation deduplication
  must remain under the separately approved restricted command namespace.
  actor_scope_key and keyed digests are pseudonymous; retention/key destruction
  and prevention of replay after erasure are **Approval required** Q15/Q16/L05.
- execution_generation is a positive operation-scoped instruction generation for
  commands that can cause external execution; it is NULL for nonexecution
  commands, not an implicit first generation or bypass. A repeated request or
  unknown timeout cannot increment it. Changed instructions or verified
  nonmovement require a new command and renewed approval/generation where
  approved; never create a fresh transfer identity after an uncertain result.

## Approval stage and before/after references

An approval context binds command, payload, operation/execution generation,
amount/currency and approved authority policy. Q13 must specify required stages,
limits, approver independence, automation and authority bootstrap (**Approval
required**). NULL/unknown stage policy or amount limit blocks dependent approval.
A role, single approval row or execution credential does not imply all stages.

Every decision names a positive stage within that approved policy and its exact
approval context. Its sealed audit event must match command, actor, permission,
scope, amount, payload and execution generation. Decisions are append-only:
one initial decision per generation/stage, at most one successor per decision,
same-stage acyclic supersession. A rejection/revocation preserves prior decisions.
Recheck current authority, MFA, stage completeness and expiry at initiation;
historical seals do not confer perpetual authority.

Before/after references identify immutable internal revision/event facts, not
arbitrary JSON snapshots. reference_kind determines the permitted parent type
and relation validator. UUID existence alone is insufficient: enforce matching
salon, command, source and generation. A missing pre-state is explicit creation;
a denied command has no after-effect. If no immutable version exists, the owning
group must define a controlled financial-facts digest with a versioned field
allowlist. No names, contacts, bank/provider secrets, raw bodies or raw SQL enter
these digests or references. Pseudonymous digests still require Q16 review.
Typed FKs are attached in the group owning each future target before activation.

Corrections/reversals append a new sealed audit/financial event linked to the
original. Links cannot self-reference, cycle, cross scope/currency/environment,
or change the original's actor, amount or outcome. An audit reversal does not
reverse money: G02 requires conserved compensating postings, source linkage and
approved limits; provider execution remains separately confirmed under P05/P06.

## Immutable finalization and failure durability

Audit finalization and accounting finalization are separate:

1. Every inserted audit event receives exactly one financial_audit_finalizations
   seal in the same transaction. Validate mandatory command/actor/decision facts,
   stage relationships, typed references and a versioned canonical digest.
   A deferred guard rejects missing seals at commit. Audit fact fields cannot
   change or gain children affecting the sealed commitment afterward.
2. A requested, pending, denied or failed event can be audit-finalized. That
   freezes the statement recorded at that time; later observations append new
   events. It does not declare the command completed, the payment successful,
   the refund settled, or the transfer paid.
3. G02 financial_event_finalizations alone seal a complete balanced posting set.
   G01 identity and audit seal cannot replace that accounting proof. G04 further
   requires approved reserved instructions and verified transfer finality.
4. Immutable facts/digests exclude the explicitly erasable actor FKs and
   restricted detail payload. Insertion still requires verified actor/authority;
   later only verified erasure can null identity links, with all remaining
   columns equal. It cannot switch actors or recalculate financial facts/seals.
5. Business effect and its audit intent/outcome append atomically. If business
   rollback occurs, record sanitized denial/failure in an independent minimal
   audit transaction or durable security outbox, without FK references to rolled
   back objects. Failure-audit mechanism and availability policy are **Approval
   required** Q13; new admin commands fail closed if durable audit cannot be
   guaranteed. Do not fabricate a seal or success after a crash.
6. Existing verified incoming provider outcomes stay durably receivable even
   when new command initiation/audit is unavailable; later reconcile against the
   original operation. Never drop already-moved-money evidence.

## Indexes and constraints

Unique command_id, financial/audit event keys, command replay namespace
(actor_scope_key, command_kind, idempotency_digest), authority code/version,
approval context (command_id, approval_generation), initial stage and successor
identities, approval audit event, one detail row and one seal per audit event.
Digest-key rotation must preserve logical uniqueness; adding key_version to a
unique key alone cannot permit replay. **Approval required** Q15/Q16 for the
version-transition/deduplication design.

Index every FK plus audit (command_id, observed_at, id), (salon_id, observed_at,
id), (actor_id, observed_at, id), financial events (salon_id, effective_at, id)
and (booking_id, effective_at, id), active authority intervals and operation/
execution lookups. Positive versions/generations/stages, finite bounded amounts,
INR, coherent intervals, ciphertext/key pairs and bounded codes are required.

Lock relationships before validating cross-row authority/approval/lineage.
Publish exact G09 table ranks before executable review; audit/approval rows must
not be locked before earlier affected business/funding gates. No CHECK-only
claim for cross-row sums, authority or lineage. Mutable authority retirement
cannot rewrite its historical scope/permissions. No command identity or audit
backfill imputes approvals to legacy operations.

## Later typed integration ownership

| Group | Additions after its parent tables exist |
| --- | --- |
| G02 | Accounting postings/seals for G01 financial_events; same-command authorization/audit linkage and sealed-source validation |
| G03 | Cancellation correction/refund-obligation audit via G01/G02 financial events, with same booking/root bindings |
| G04 | Nullable indexed payout_id/dispute_id/destination_version_id on audit events, payout_id/destination_version_id on approval contexts/decisions, composite payout/execution-generation FKs and same-command/amount/reservation/destination validation; indexed FK on salon_payout_generations.approval_generation_id; mandatory audit links on payout/dispute events |
| G05 | Mandatory new-mode schedule-event command_audit_event_id and typed before/after schedule/restriction references |
| G06 | Financial corrections via G01/G02 sealed financial events; rule/snapshot administration via G01 sealed audit and immutable rule references |
| G07 | Mandatory new-mode subscription-lifecycle command_audit_event_id and same-salon policy/purchase references |
| G08 | Mandatory new-mode schedule-event command_audit_event_id and typed request/revision/closure references |
| G09 | Shared authority/erasure/booking lock integration and atomic hold behavior; no durable hold as financial evidence |

Future-parent columns are not part of the initial G01 schema. Typed extensions
are installed/validated by their owner group; existing historical rows may stay
explicitly legacy NULL, but new-mode commands cannot opt into that exception.
This staged integration is not a new assigned revision or permission to enable
an incomplete foundation.

## RLS/security impact and minimum runtime privileges

All eight foundation tables are backend-only: RLS enabled and client/PUBLIC
table and function access excluded. No new client policy, new role enum,
SECURITY DEFINER shortcut, blanket service-role grant or authority seed.
Require verified aal2 on admin finance commands even if generic admin MFA is
optional. Proposals below are ceilings, **Approval required** Q13 and exact SQL
privilege/entry-point review; no grants are implemented.

| Principal | Proposed minimum ceiling | Explicit exclusions |
| --- | --- | --- |
| API runtime | Scoped safe reads and guarded command/audit-intent append; named operational projections only | No authority grants, direct finalization/approval insertion, finalized child insertion, financial UPDATE/DELETE/TRUNCATE/TRIGGER or schema CREATE |
| Audit writer/finalizer | Exact audit append and seal operation for validated actual decisions, with denied-attempt support | No business-effect/transfer authority; no fabricated actor/approval, seal rewrite or accounting finalization |
| Accounting worker | Scoped source reads and G02 guarded append/balanced-finalization operations under current accounting authority | No payout approval/execution, authority management, broad erasure or mutable historical amounts |
| Payout executor | Exact G04 approved-generation reads, submit/reconcile projection and append outcome evidence | No self-approval, destination/amount modification, new ID for unknown outcome or chart/authority mutation |
| Authority/approval operator | Permission-specific audited commands within approved scope/limits/independence and MFA | No self-grant/self-expansion, implicit super-admin authority or direct fact edits |
| Erasure worker | Verified request-scoped identity-to-NULL and approved detail scrub/key handling; append sanitized scrub evidence | No financial source/amount/outcome/generation mutation, obligation deletion or arbitrary erasure-flag bypass |

These are process responsibilities, not asserted existing database roles. An
invoker adapter still needs underlying rights; direct table grants plus a generic
entry point cannot claim to enforce an exclusive command path. If exact rights,
guards and principal separation cannot enforce the ceilings, block activation
and review a narrow design rather than add definer privilege or GRANT ALL.

The Mumbai report observed service_role BYPASSRLS and broad privileges,
postgres ownership/BYPASSRLS, creator-dependent defaults, 21 existing definer
functions and latent permissive client policies. This phase has no fresh
database verification. FORCE RLS would not constrain BYPASSRLS. A custom session
flag is not authorization; managed roles/extension ACLs must remain untouched.
No new finance table is placed in realtime publications by this design.

## Account-deletion behavior

Null nullable profile/actor/grantor/approver/finalizer links only after verifying
the deletion request and under the shared identity gates. Existing detachment
covers single-column FKs only; add every new field to classification/verification.
Do not introduce a composite profile FK without explicit detachment handling.

Preserve command/event/source/approval generation identities and nonpersonal
financial facts only under approved Q16/L05 retention. Retire the erased actor's
future authority and block use/replay of that identity without removing the old
decision. actor_scope_key, role/permission snapshots and keyed digests may remain
identifying in context; **Approval required** Q15/Q16/L05 for restricted linkage,
key destruction, legal holds and eventual anonymization without double payment.

Erase or legally restrict separate encrypted details/evidence; do not put
arbitrary messages or before/after PII in immutable event rows. A legal-hold
reference does not authorize its own retention. Identity nulling must preserve
seal verification; no new financial-history hard delete is introduced.
Existing unresolved obligations require durable operator handoff, not account
reactivation or indefinite refusal of erasure. See the 43-field treatment design.

## Downgrade safety and rollback plan

Only empty, unused foundation tables with no dependent links/writers permit
future reviewed structural removal. Refuse once any command, audit, approval,
seal or governed event exists. Stop new initiation, retain denied/outcome
capture, history, encryption reads, erasure and outstanding reconciliation;
repair forward. Never delete evidence or restore broad privileges to roll back.

## Unresolved approval and readiness

**Prepared for design review; not execution-ready.** Q13/Q15/Q16 and relevant
P05/P06/L02-L05: actor matrix, bootstrap, stages/limits/independence, system
authority, canonical idempotency and digest rotation, failed-audit durability,
typed integration, encryption, retention/holds and reconciliation ownership.
No financial command, SQL privilege, provider capability or retention duration
is authorized by this document.

Later verification must prove denial without MFA/permission, cross-salon binding,
same-command/generation/stage matching, concurrent approval/revocation/erasure,
unique retry identities across digest rotation, seal completeness, no post-seal
child insertion, rollback-safe denied audit, identity scrub without fact changes,
and empty-only removal/data-bearing forward repair. None runs in this phase.
