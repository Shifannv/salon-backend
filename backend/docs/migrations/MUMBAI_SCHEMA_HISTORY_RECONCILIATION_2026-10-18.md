# Mumbai schema/history reconciliation — 2026-10-18

**Inspection complete; migration/history reconciliation remains unapproved.**
Mumbai is a restored, populated schema with empty Alembic history. No applied
Alembic revision is established. The prepared 0040 effects appear present, but
independent expected-0040 equivalence has not been proved. All financial migration
labels, IDs and dependencies remain provisional.

Only this report was created. No executable migration, SQL sidecar, approval
manifest, application change or memory update was created by this inspection.

## Scope and evidence limits

- Target: Supabase project `wqjlgpnbiapcrlkxumcp`, verified region
  `ap-south-1`, status ACTIVE_HEALTHY, PostgreSQL 17.11
  (platform version 17.11.0.003). Only the Mumbai connector and this explicit
  project ID were used; no project enumeration or other project access.
- Live catalog collection began at 2026-10-18 20:46:57 IST; final catalog
  fingerprints/history check: 20:52:09 IST (15:22:09 UTC).
- Successful catalog batches explicitly used REPEATABLE READ, READ ONLY
  transactions. Separate batches are separate snapshots, not one global snapshot.
  Read-only status was observed as `on`. Management metadata/history
  lookup was read-only. Inspection role was `postgres`; no runtime
  database credential or deployed runtime role was inspected.
- One initial metadata query had a syntax error and produced no catalog evidence;
  it was corrected. No business function, provider operation, DML, DDL,
  privilege mutation, Alembic command or migration runner was executed.
- Only catalog definitions, history metadata/hashes, aggregate financial row
  counts and nonpersonal plan catalog values were read. No personal business
  rows, raw migration statement bodies, environment files, credentials, connection
  strings or provider configuration were collected into this report.
- Source checkout: `6f097ce00572228c738ef6ec2488751b373a0166`,
  branch `thameem/provider-agnostic-payments`. Existing uncommitted
  provider work/designs were preserved.
- Inputs: [specification](../verification/payment-subscription-booking-spec.md),
  [eight designs](payment-subscription-booking-designs/README.md),
  [existing forward reconciliation](MUMBAI_FORWARD_RECONCILIATION.md),
  [migration policy](MIGRATION_POLICY.md), Alembic configuration/environment,
  revision/SQL sources, account-deletion adapter and classification inventory.
- No disposable database was built: this phase authorizes read-only inspection
  only. No application tests were run because they can create databases or run
  migrations. Catalog analysis and standard-library source/document checks
  provide inspection evidence, not behavioral/concurrency/provider proof.

## 1. Actual Mumbai migration/history state

| History source | Observed state | Interpretation |
| --- | --- | --- |
| public.alembic_version | Table exists; zero rows at initial and final checks | No recorded current Alembic revision. Neither base nor 0037 nor 0040 is established. |
| supabase_migrations.schema_migrations | Four rows, listed below; one stored statement per entry | Supabase restore/hardening ledger, not an Alembic ancestry ledger. |
| Repository graph | 40 registered revisions; one source head: 0040_fastapi_only_access | Static AST inspection only; no 0041–0048 executable revision is registered. |
| Managed histories | auth.schema_migrations, realtime.schema_migrations, storage.migrations exist | Platform histories are separate; their contents were not used as application migration evidence. |

| Supabase version | Recorded name |
| --- | --- |
| `20261015100439` | `mumbai_roles_compatible_restore_20261015` |
| `20261015100737` | `mumbai_schema_only_restricted_restore_20261015` |
| `20261015100828` | `mumbai_reviewed_auth_signup_trigger_20261015` |
| `20261015101623` | `mumbai_reconcile_0024_function_search_path_20261015` |

The names describe a roles-compatible restore, restricted schema-only restore,
reviewed signup trigger and function search-path reconciliation on October 15.
They do not prove historical data backfills or execution of revisions 0001–0040.
The schema contains later booking/payment features and eight payment rows, so
replaying the baseline or earlier upgrades from an assumed empty database is
unsafe. Historical application data provenance is not recoverable from these
four ledger names alone.

Current Alembic behavior was read from source:

- `backend/alembic.ini` points to `migrations`; raw SQL is loaded by
  revision files from `migrations/sql/`; no ORM autogeneration metadata.
- `migrations/env.py` takes the explicit process URL for mutations and
  normalizes its driver. It invokes target policy before connecting/emitting SQL.
  No application settings were imported in this inspection.
- Portable CI is limited to explicit disposable-loopback ancestry through
  `0037_customer_processing_charge`. Prepared 0038–0040 are Mumbai-specific.
- Implicit head, unapproved/unknown destinations, stamp, ensure-version, prepared
  downgrade and ambiguous routing are refused. Mumbai requires project identity,
  reviewed source/evidence hashes and an approved manifest.
- The online Mumbai guard additionally requires exactly one known current
  revision. Mumbai's empty version table fails that requirement before revision
  traversal. Merely approving an upgrade does not solve the restored-history gate.
- Existing manifests/policy cannot authorize proposed financial revisions.
  Neither removing the guard nor treating an empty table as stamp permission is
  a reconciliation strategy.

## 2. Differences from repository head 0040

### What the fresh comparison establishes

The live catalog was compared with the retained
[October 15 catalog](../../migrations/reviews/migration-mumbai-forward-catalog-2026-10-15.json).
There were **zero missing, extra or changed objects** in all eight comparable
categories: tables, columns, constraints, indexes, application functions,
triggers, policies and enums. All 52 exact function-body SHA-256 values match;
other definitions use the historical whitespace-only normalization. Column
type/null/default/generated/identity attributes are included in that comparison.

This is a fresh match to a historical Mumbai snapshot, not to a newly built 0040
reference. The earlier
[0037 comparison](../../migrations/reviews/migration-mumbai-head-comparison-2026-10-15.json)
used PostgreSQL 18 as reference and excluded ACLs. Source comparison against its
reference commit `1b471dca6a70a245d193635d481f1086d10b875a` found
no semantic revision changes through 0037: the baseline, 0035 and 0037 loaders
only gained the SQL directory path, and both relocated later SQL sidecars match
after newline normalization. The raw baseline hash also matches retained evidence.
This strengthens the historical bridge but does not establish executed history.

| Area | Live Mumbai result | 0040 assessment |
| --- | --- | --- |
| Tables/columns/indexes/triggers/RLS | 44 / 540 / 148 / 74 / 43 policies; historical catalog match | No new structural drift detected against retained restored schema. |
| 0038 compatibility columns | bookings.cancellation_reason_code and cancellation_reason_text: nullable pg_catalog.text; no default/domain/collation, identity or generation | Requested final definitions already present. No need inferred to add, retype or backfill them. |
| 0039 promotion helper | Existing signature; postgres owner; SECURITY INVOKER; immutable; boolean; search_path=public; body matches historical hash | Requested configuration effect already present. No need inferred to replace its body. |
| 0040 named objects/access | All 44 named application tables and 52 function identities present; zero effective client application rights | Requested access restriction effects already present. Does not prove the revision ran or all pre/post assertions pass. |
| Indexes/constraints | All 148 indexes valid/ready; all 290 constraints validated | No disabled/unvalidated enforcement detected; definitions must still be compared to authorized PG17 reference. |
| Auth signup | Enabled auth.users trigger points to reviewed public.handle_new_user | No duplicate signup revision or trigger replacement indicated. |
| History | Alembic zero rows versus a source graph ending at prepared 0040 | Unresolved reconciliation difference. Never fill automatically. |
| Fresh expected-head proof | No independently built PG17 0040 reference in this phase | Full equality is NOT VERIFIED; no revision/stamp or executable starting point approved. |

Two catalog representation differences from the older PG18 reference must not be
misreported as missing enforcement: its 317 NOT NULL constraint entries are
represented by matching column NOT NULL flags on Mumbai PG17, and its
subscription-plan interval CHECK deparses array casts differently while allowing
the same monthly/quarterly/semiannual/yearly intervals.

There is also a physical-order caveat: Mumbai's legacy cancellation columns are
at bookings ordinals 32/33. A clean 0037 schema with those columns appended by
0038 would place them after the older columns (41/42). The historical comparison
keys columns by name and omits ordinals; the expected order is a source-derived
inference, not a fresh build result. Review row-composite/SELECT-star consumers
and record any accepted order difference; do not rebuild the table to manufacture
byte equality. Column order cannot justify stamping.

Owners/configuration, effective/inherited/column/default ACLs, extension
exclusions, publication attributes, physical representation and historical data
effects were not all included in the old clean-head proof. They require an
explicit PG17 acceptance comparison. Static compatibility with the intended
0038–0040 effects is favorable; canonical 0040 equality remains unresolved.

## 3. Existing objects reusable by the proposed designs

| Foundation | Objects and live properties | Reuse limit |
| --- | --- | --- |
| Payment authority | booking_payments, payment_refunds, payment_webhook_events, payment_idempotency_keys, payment_anomalies | Reuse capture/refund/replay authority; do not create a second success ledger. |
| Actual cost placeholders | booking_payments.provider_fee_amount/provider_tax_amount: nullable numeric(10,2) | No six-component actual-cost evidence, allocation or finality is implied by these scalar fields. |
| Historical snapshots | commission fields; gateway_fee_percent/gateway_fee_amount; online_processing_charge; stored generated service_amount = amount - online_processing_charge; checkout_policy_version | Preserve estimates, commissions and surcharge history. Do not relabel them actuals or recompute old receipts. |
| Existing guards | tg_booking_payments_guard, tg_payment_refunds_guard, guard_collection_snapshot, recompute_booking_payment_state and attached triggers | Current identity/amount/commission/fee immutability and derived-state logic can be extended after review; not sealed double-entry accounting. |
| Provider/destination onboarding | payment_provider_accounts (registration_generation), payment_provider_account_audit, salon_payout_accounts/history, salon_payout_account_masked | Onboarding and destination history do not establish verified capability, funds, transfer, settlement or payout finality. |
| Subscription authority | subscription_plans, salon_access, salon_subscriptions, subscription_billing_records, subscription_events, subscription_provider_accounts | Reuse purchase snapshots, paid periods and one-time application; no second purchase ledger. |
| Subscription operations | apply_subscription_billing_record, cancel_salon_subscription_renewal, sweep_lapsed_subscriptions, start_salon_trial, salon_booking_eligible, promotion helper | Existing policy differs from proposals; preserve search-path and access hardening when later replacing functions. |
| Booking/schedule authority | create_booking, get_available_slots, bookings_no_overlap, booking_services composite PK (booking_id, service_id), staff/services mappings | SQL remains creation/availability authority; new reschedule semantics are absent. |
| Closure/audit/outbox | salon_holidays, blocked_slots, salons.accepting_bookings, booking_action_requests, booking_audit_events, notification/email outboxes | Reuse operations and evidence; current state-transition audit is not finance command/approval audit. |
| Erasure mechanism | erase_profile_references, set_audit_actor, actor-only booking audit scrub; owner cascade/provider-reference lists | Reuse only with expanded classification and restricted scrub/handoff checks. |
| Extension support | btree_gist 1.7 in public; pgcrypto 1.3 in extensions | Temporal exclusion support exists; no extension installation justified by this inspection. |

Important existing indexes include unique payment intent/provider-order/provider-
payment keys, one-open-gateway-intent partial uniqueness, actor/scope/idempotency
uniqueness, payment/refund idempotency uniqueness, provider-refund uniqueness,
subscription order/payment/receipt uniqueness, one-open-order per salon,
unapplied-purchase and subscription-eligibility indexes. Reuse their exact
predicates where appropriate instead of adding duplicate indexes.

The live booking exclusion is nondeferrable GiST on staff and the timestamp range
for **pending, confirmed and checked_in**. It must survive reschedule work.
The subscription active-per-salon unique predicate excludes expired, cancelled
and suspended states; it is not a universal one-row-per-salon invariant.

Aggregate evidence at 20:49:03 IST: booking_payments has **8 rows**; payment_refunds,
webhook events, provider accounts/audit, payout accounts/history, anomalies,
subscriptions, subscription purchases/events/provider mappings each had zero.
Payment amounts, people and provider references were not read. These counts do
not prove later emptiness, test provenance, absence of backups or provider activity.

Six active plans already exist:

| Plan | Interval | INR total |
| --- | --- | --- |
| `growth_12m` | yearly | 1999 |
| `growth_1m` | monthly | 349 |
| `growth_6m` | semiannual | 1499 |
| `premium_12m` | yearly | 3499 |
| `premium_1m` | monthly | 599 |
| `premium_6m` | semiannual | 2499 |

All six have tax_inclusive NULL. Existing prices need no new seed or reset.
Tax treatment and benefits are not approved by their presence.

## 4. Missing proposed objects

**All 43 newly proposed tables are absent** from public. No extra application
relations were found in nonmanaged schemas. Existing foundation names are not
partial implementations of these proposed new tables.

| Provisional design label | Absent tables |
| --- | --- |
| 0041 | `provider_charge_identities`, `provider_charge_observations`, `provider_charge_components`, `provider_charge_evidence_links`, `provider_charge_allocations`, `provider_charge_reconciliations`, `financial_events`, `financial_postings`, `financial_event_finalizations` |
| 0042 | `cancellation_policy_versions`, `cancellation_policy_activations`, `booking_cancellation_terms`, `booking_cancellation_outcomes`, `cancellation_refund_obligations` |
| 0043 | `payout_destination_versions`, `salon_financial_entitlements`, `booking_financial_disputes`, `booking_financial_dispute_events`, `salon_payouts`, `salon_payout_generations`, `salon_payout_reservations`, `salon_payout_attempts`, `salon_payout_events` |
| 0044 | `payout_capability_versions`, `salon_payout_schedule_versions`, `salon_payout_restrictions`, `salon_payout_schedule_events` |
| 0045 | `staff_commission_rule_versions`, `booking_staff_commission_snapshots`, `booking_staff_commission_allocations`, `staff_commission_obligations`, `staff_commission_entries` |
| 0046 | `subscription_lifecycle_policies`, `subscription_lifecycle_events` |
| 0047 | `business_closure_operations`, `business_closure_booking_actions`, `booking_reschedule_requests`, `booking_schedule_events` |
| 0048 | `financial_authority_versions`, `admin_financial_audit_events`, `financial_approval_generations`, `financial_action_approvals`, `admin_financial_audit_details` |

The following proposed additions to existing tables are also absent:

| Existing table | Absent columns |
| --- | --- |
| `payment_refunds` | `cancellation_outcome_id`, `cancellation_refund_obligation_id`, `cancellation_delivery_generation` |
| `salon_access` | `lifecycle_policy_id`, `trial_timezone`, `trial_activation_event_id` |
| `salon_subscriptions` | `lifecycle_policy_id`, `renewal_mode`, `renewal_consent_event_id` |
| `subscription_billing_records` | `lifecycle_policy_id`, `purchase_timezone` |
| `bookings` | `schedule_revision` |

Because their parent tables are absent, the designs' new FKs, temporal
exclusions, balance/conservation validators, seals, financial authority checks,
reservation caps, immutable approval/execution bindings, encrypted evidence,
mandatory audit links and same-salon/environment/provenance guards are absent.
No reschedule_booking application function exists among the 52 inspected
functions. Later audit/payout/schedule links to the proposed tables are likewise
not installed. There is no persisted six-field provider-fee mapping or verified
transfer/settlement-reference store from the in-memory fake implementation.

## 5. Conflicting objects and semantics

There are **no detected table-name collisions** with the 43 new table proposals.
Final constraint/index/function names are not executable specifications yet, so
absence of table collisions is not proof that a future migration will compile.

| Conflict | Evidence / required treatment |
| --- | --- |
| Source head versus history | Empty restored history cannot traverse the current Mumbai Alembic guard. Resolve provenance/equality and approve a separate history path before any financial migration. |
| Actuals versus estimates | Legacy monetary columns and immutable gateway estimates already exist; provider actuals need canonical economic-charge identity and evidence, not reuse by name or duplicated expense. |
| Surcharge/commission | Current checkout-policy stamp uses customer_processing_v1; historical surcharge and configurable commission snapshots remain. New no-surcharge/zero-completed-commission rules need a new approved policy and coordinated writers, not a column addition. |
| Refund identity/caps | Current refund guard freezes kind/deduction/amount and caps per payment, but does not implement proposed cancellation root/obligation/delivery bindings or aggregate outcome-wide reservation. Add reviewed binding and locking semantics; never attach old refunds automatically. |
| Trial/access | Current start_salon_trial uses two months and a 120-booking cap; salon_booking_eligible enforces counted-booking limits and active paid periods. Unlimited trial, timezone anniversary/grace/expiry behavior cannot be inferred. |
| Subscription locking | apply_subscription_billing_record locks subscription:<salon_uuid>; closure guard locks salon UUID; checkout trigger obtains salon_access/customer locks later. The proposed shared total ordering is not implemented. |
| Hours/slots/reschedule | get_available_slots coalesces staff hours over salon hours rather than intersecting them, and steps by duration. Closure guard fires on INSERT only. Proposed buffers/notice/intersection/schedule-update protections require bounded SQL design. |
| Finance authority/audit | Existing super-admin helper and transition audits do not supply scoped authority, dual approval, command generations, durable denied-action audit or sealed postings. |
| Secrets/retention | salon_payout_accounts.bank_account_number is plaintext-capable text; history JSON can snapshot personal destination fields. Masked reads do not encrypt storage. Current zero rows do not settle backup/other-environment retention. |
| Scope/provenance | Existing payment/purchase/provider-reference uniqueness lacks the proposed immutable account-scope/environment/origin binding. Legacy references cannot be assumed live, mock, settled or safely relabelled. |
| Money width | Existing money is generally numeric(10,2), proposals numeric(18,2). Explicit boundary/finite-amount and projection compatibility is needed; no automatic widening or historical rewrite. |

The closure/customer/salon/subscription lock-order discrepancy is a static
concurrency risk, not a reproduced deadlock. Later implementation must publish
the complete table-rank mapping and coordinate every legacy API/worker path,
including erasure and authority changes.

## 6. RLS and privilege risks

All 44 public tables are postgres-owned with RLS enabled; none FORCE RLS.
All 74 noninternal triggers inspected (including the Auth signup trigger) are
enabled. There are 43 policies; missing policies on backend-only tables mean
deny-by-default for ordinary RLS subjects, not broken access requiring grants.

| Principal | Effective public application rights |
| --- | --- |
| anon | 0 table privilege hits across SELECT/INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER/MAINTAIN; 0 column hits across SELECT/INSERT/UPDATE/REFERENCES; 0 of 52 app functions executable. |
| authenticated | Same zero effective table/column/app-function access. |
| service_role | All eight inspected table privileges on all 44 tables; all four column privileges over all 540 columns; EXECUTE on all 52 app functions; BYPASSRLS. |
| postgres | All application objects owned by this role; BYPASSRLS; administrative role memberships. Inspection used this role, not evidence of deployed runtime identity. |

Effective checks include PUBLIC and inherited privileges. No explicit column ACLs
were present. All three roles have public schema USAGE but no CREATE. There are
no public sequences or views/materialized views. There are 240 public functions:
52 application functions and 188 btree_gist extension functions; client EXECUTE
on the 188 extension functions remains an intentional exclusion. Do not revoke
extension/managed rights merely to produce a zero across the whole schema.

**High risk before finance activation:** RLS does not constrain BYPASSRLS
service_role or owner sessions. Broad INSERT/UPDATE/DELETE/TRUNCATE/TRIGGER
rights cannot enforce immutable-fact separation or prevent bypass of finalization
and approvals. No separate application/accounting/payout/erasure principal is
present in the inspected role inventory. This does not identify which credential
the deployed service actually uses; runtime identity remains unverified.

Twenty-one application functions are SECURITY DEFINER, owned by postgres. All 52
have pinned paths (public, pg_catalog, or public plus pg_catalog); clients cannot
execute them now. A future grant could expose owner-privilege behavior, so no
function replacement/grant is authorized here. Review each new entry point,
underlying rights and ability to set custom GUCs; app.account_erasure,
app.subscription_system and app.payment_recompute flags are not independent
authority against an already broadly privileged caller.

**Future-object risk:** postgres has a global function default excluding PUBLIC;
its public defaults give service_role access without client grants. In contrast,
supabase_admin's public defaults grant clients table, sequence and function rights.
Default ACLs depend on creator; no global/default grants were changed by 0040.
A new object created under another principal can silently reopen client access.
Each eventual migration must assert/restrict its own exact ACLs in the same
reviewed transaction and preserve managed infrastructure privileges.

**Latent RLS risks if access is reopened:** public read policies such as
blocked_read/staff_services_read use true; customer booking UPDATE policy checks
ownership rather than limiting updates to cancellation; profiles_self_update has
no column-level role protection. Those routes are currently inaccessible to
client roles, but these policies are not a safe substitute for FastAPI policy.
Do not add client grants to make direct-client probes pass.

The three realtime-published application tables are bookings, blocked_slots and
booking_action_requests. Publication presence does not grant SELECT; current
client restrictions must be preserved. New financial facts/evidence must not be
added to publications casually. This catalog review did not test Data API,
GraphQL, Realtime delivery or authenticated API ownership behavior.

## 7. Account-deletion and retention risks

1. The live erase_profile_references function sets the erasure flag and detaches
   only single-column NO ACTION/RESTRICT profile FKs; it does not classify or
   scrub arbitrary text, JSON, ciphertext, keyed digests or detached UUIDs.
   Composite profile references would require separate handling.
2. The source adapter already clears both legacy cancellation text fields before
   identity detachment, including owner-scoped retained bookings. Their live
   definitions support that code. Deployment/worker execution was not verified.
3. The current live cascade-to-salon inventory has six tables: blocked_slots,
   salon_access, salon_holidays, salon_images, salon_payout_account_history and
   salon_payout_accounts. It matches the adapter's explicit deletion list.
   Salons are retained shells, so cascade declarations alone never erase those
   children. Provider mappings are removed by a separate explicit list.
4. **43 live text/varchar/JSON/array columns are absent from COLUMN_TREATMENT**,
   excluding alembic_version. Full inventory is in Appendix C. This is a
   classification/test-coverage gap, not proof that every value contains PII
   or that every erasure fails.
5. Concrete retention concerns: payment_provider_account_audit retains vendor_ref
   and free-form detail after its actor FK is detached; owner-related support
   subject/messages can survive customer-owned ticket retention; anomalies,
   billing benefits/receipts/provider references and provider-session fields need
   explicit treatment. email_events cascades when its recipient profile is
   deleted, but that does not prove removal of erased-owner details embedded in
   another customer's retained email. No residual data scan was performed.
6. Current booking-audit immutability permits only actor-to-NULL changes with
   every other field equal. Preserve that narrow behavior. Do not reuse an
   unrestricted erasure flag to change financial amount/source/outcome facts.
7. Existing owner erasure deletes payout destination/history and live provider
   mappings. Future immutable financial source links must not depend on those
   rows or block their removal. Operational request/holiday/block references
   need reviewed SET NULL semantics; booking/salon financial shells are retained.
   The current workflow also deletes salon_access; future trial/lifecycle history
   must survive independently without resurrecting access.
8. The current worker's capped refund-wait/unknown-refund behavior does not provide
   the future handoff for disputes, payout reservations, unknown transfers,
   provider evidence, key custody and recovery. Erasure cannot release uncertain
   funds or change an unknown operation to failed merely to complete deletion.
9. Detached UUIDs, financial references, encrypted evidence and keyed digests are
   pseudonymous/restricted data, not proof of anonymization. Q15/Q16/L05 must
   approve per-column retention, legal holds, access, backups, key destruction
   and deduplication after scrub. No retention duration or new hard-delete
   exception is authorized by this report.

## 8. Required forward-only reconciliation plan

The following is a future plan, not executable authorization:

1. Freeze the reviewed source/design versions and preserve existing restore
   evidence. Keep Mumbai's version table untouched. Record explicit accepted
   restoration provenance and separately classify data/backfill uncertainty.
2. Obtain authorization for an isolated, identity-verified disposable PG17
   reference and its harness. Resolve consolidated-baseline replay overlap
   (including staff.experience) in the reference strategy without rewriting
   deployed baseline/revision history. Current portable policy stops at 0037;
   a reviewed reference method must represent 0038–0040 and managed prerequisites
   without silently disabling production guards.
3. Build the approved expected schema and compare every final object with fresh
   Mumbai metadata: columns including null/default/generated/identity/order,
   owner/config/body/language/security, all constraints/index predicates and
   validity, trigger definitions/order/enabled status, RLS policies, enums,
   effective/PUBLIC/inherited/column/default/schema rights, extension exclusions,
   publication state and data effects/seeds. Formally accept deparse/order-only
   differences, rather than hiding them with IF NOT EXISTS.
4. Present the exact remaining differences. Prepare only separately authorized,
   narrowly scoped **forward repairs** for incompatible final definitions.
   Preserve existing financial/history data, hardening and erasure behavior.
   No unconditional create/replay/backfill, duplicate plan seed or conversion of
   an estimate/mock observation into verified actual money.
5. Review a restored-history transition independently. Even exact final-state
   equality does not prove historical migration execution. The existing runner
   cannot start from an empty table. The owner must approve the explicit history
   recording strategy and corresponding guarded tooling after equality/data
   review. Any future stamp consideration requires a new explicit approval and
   policy review; none is proposed or authorized here, and no stamp command is
   supplied.
6. Resolve the dependent business, finance-authority, provider-evidence,
   encryption/retention and locking designs. Split the minimum audit foundation
   as described below; produce the final dependency graph only after review.
   Do not confirm IDs/down_revision values from the current design labels.
7. Only after preparation approval, author additive, initially inert executable
   artifacts with exact preconditions, explicit client revocations/RLS,
   least-privilege guards, erasure coverage and bounded lock/statement timeouts.
   Review large indexes/concurrent build phases and FK/CHECK validation separately.
   No guessed historical financial or policy backfill.
8. Obtain separate authorization for disposable PG17 migration, cross-connection
   concurrency, privilege/role denial, conservation/idempotency, erasure,
   history-guard, empty-downgrade refusal and data-bearing forward-repair tests.
   Mock results cannot validate real provider capability or movement.
9. Independently review source-hash-sealed artifacts, backup/recovery evidence,
   staged validation and the still-required customer/owner refresh gate.
   Prepare an explicit coordinated API/worker rollout and forward recovery plan.
   New writers must fail closed without required audit/schema capabilities;
   incoming verified payment/refund evidence and old obligations remain durable.
10. Require new, target-specific staging execution approval for the exact reviewed
    artifacts/history strategy and a separate deployment approval. Recheck
    target, history, schema, grants and data counts immediately beforehand.
    Execution, deployment, provider access and later environments are outside
    this phase.

## 9. Should the audit foundation move before 0041?

**Yes.** The live booking and payout-account histories do not provide the proposed
finance authority/command/approval foundation, and service_role currently has
broad powers. Creating accounting/payout writers before their required authority
and audit relationships would leave an avoidable dependency gap.

Split the provisional last design: install minimum financial authority versions,
command/audit identity and restricted erasable detail storage before accounting
finalization. Keep that minimum foundation independent of future payout,
dispute, posting and destination parents. Add typed object FKs, payout/approval
generations and mandatory cross-workflow links after their parents exist.
Resolve bootstrap/independent authority under Q13; seed no implicit super-admin
or service credential entitlement.

This recommends dependency order only. It assigns no revision number and may
require more than eight executable revisions. If the foundation is kept late,
every new finance writer must remain server-blocked until complete audit and
authorization constraints are installed and verified. Feature flags alone are
insufficient. Financial observation intake must still preserve verified incoming
outcomes for reconciliation.

## 10. Exact approvals before executable migration preparation

No approval is requested or inferred in this inspection. A later approval must
identify scope, decision/artifact, approver, selected values, effective policy
version/date and legacy/open-operation treatment.

| Approval | Required decision before dependent preparation |
| --- | --- |
| A01 — bounded preparation scope | Explicitly authorize writing executable Alembic revisions/SQL/tests for the reviewed Mumbai reconciliation and selected finance groups; preparation only, no execution/stamp/deployment. Approve source/design versions and a focused branch. |
| A02 — baseline/history proof plan | Approve disposable PG17 reference build/replay strategy, managed prerequisite representation, catalog acceptance criteria, restoration provenance and treatment of unknown historical backfills. History mutation remains a distinct later approval. |
| A03 — dependency/guard plan | Approve audit-foundation split, final graph and only then final IDs/parents; review extending target policy beyond 0040 without weakening Mumbai identity, evidence or history guards. |
| A04 — security and privacy architecture | Approve exact runtime/accounting/executor/erasure authority separation, object/entry-point privilege matrix, audit availability/denial behavior, custom-GUC restrictions, key custody, column scrubs and obligation handoff. |
| A05 — executable preconditions/verification design | Approve global lock order including table ranks and legacy writers; amounts/rounding, provenance and source identities; additive/disabled rollout, no guessed backfill, bounded validation/index work and forward-repair plan. |
| A06 — unresolved dependency disposition | For each group below, resolve the policy/evidence/legal decisions it encodes. An unresolved choice must remain inert. Any preparation of schema-only scaffolding before all dependent decisions needs explicit bounded approval and must not bake in a default or enable a workflow. |

The exact owner questions remain those in
[specification section 13](../verification/payment-subscription-booking-spec.md#13-exact-questions-requiring-owner-approval):

| ID | Decision to record |
| --- | --- |
| Q01 | Cancellation A or B; exact late refund formula R and split base; no double allocation. |
| Q02 | Early/salon-caused refund, no-show/duplicate rules, late salon decision and correction authority. |
| Q03 | Exactly-four-hour boundary, trusted receipt timestamp, governing start/policy after reschedule. |
| Q04 | Each fee/tax bearer by cause; unknown-fee reserves, allocation/true-up, deficit funding/recovery. |
| Q05 | Completion hold duration, dispute scope/release/later disputes and any cancellation-compensation exception. |
| Q06 | 120-booking cap retain/remove; activation trigger, calendar/timezone/month-end/exclusive boundary and legacy grandfathering. |
| Q07 | Paid-period grace duration/privileges, trial grace, existing direct receipts/completion and late captures. |
| Q08 | Full online checkout versus advance/deposit; partial direct receipts; old surcharge/open-order/quote and unpaid-release rules. |
| Q09 | Subscription tax/benefits, cancellation/paid-through/refund policy and manual-renewal launch mode; no automatic mandate inferred. |
| Q10 | Staff basis, selection/earning time, precedence/weights, reversals, compensation categories and correction/recovery authority. |
| Q11 | Buffer/notice/same-day cutoff values/scopes, overnight/recurring closure, expiry rescheduling/repricing. |
| Q12 | Hold mandatory/optional behavior, outage fallback and per-customer hold limit. |
| Q13 | Finance actors/permissions/scopes/limits/independence, dual approval/stages, authority bootstrap, automation and manual transfer evidence review. |
| Q14 | Verified product/account/schedule/funding choice, delayed settlement and duplicate-transfer protection. |
| Q15 | Encryption/tokenization solution, decryption/rotation powers and plaintext/backups/replicas transition plan. |
| Q16 | Retention/erasure/holds, references and keys, unresolved obligation ownership, post-payout refund/fee/chargeback funding and recovery. |

Provider-dependent predicates additionally require P01 (fee/tax evidence and
canonical-charge mapping), P02 (withholding/release/hold feasibility), P03
(schedule/calendar capability), P04 (KYC/destination handling), P05
(signature/finality/retry evidence) and P06 (funding product and cross-method
transfer deduplication). Legal/accounting decisions L01–L05 cover refund/dispute
terms, fees/tax/recognition, permitted fund flow, staff compensation and
retention/erasure. These require named reviewer sign-off; owner approval alone
cannot establish provider capabilities. No provider credentials or account
access are needed or authorized to complete this read-only report.

| Provisional group | Primary unresolved dependencies |
| --- | --- |
| Provider fees / postings | Q04, Q08, Q13, Q15, Q16; P01, P05; L02, L03, L05. |
| Cancellation | Q01–Q05, Q08, Q11, Q13, Q16; P01, P05; L01–L03, L05. |
| Payout/dispute | Q04, Q05, Q13–Q16; P01–P06; L01–L03, L05. |
| Schedules | Q05, Q13–Q16; P02, P03, P06; L03, L05. |
| Staff ledger | Q04, Q10, Q13, Q16; L02, L04, L05. |
| Subscription lifecycle | Q06–Q09, Q13, Q16; L01, L02, L05; attested purchase provenance before real activation. |
| Closure/reschedule | Q02, Q03, Q07, Q08, Q11–Q13, Q16; L01, L05. |
| Audit foundation / coverage | Q13, Q15, Q16; P05, P06 where execution evidence is encoded; L02–L05. |

Later authorizations remain separate: disposable database writes/tests, provider
sandbox/account evidence, exact executable artifact review, history change,
Mumbai staging migration execution, coordinated deployment and any other
environment. This report grants none of them.

## Appendix A. Live object inventory and comparison fingerprints

All public relations below are ordinary tables, postgres-owned, RLS enabled and
not forced. Counts include PK/unique/exclusion-support indexes. Trigger count
here is public-only; the overall 74 includes one Auth signup trigger.

| Table | Columns | Indexes | Constraints | Triggers | Policies |
| --- | --- | --- | --- | --- | --- |
| `account_deletion_challenges` | 16 | 2 | 8 | 0 | 0 |
| `account_deletion_requests` | 15 | 5 | 3 | 0 | 0 |
| `alembic_version` | 1 | 1 | 1 | 0 | 0 |
| `api_rate_limits` | 3 | 1 | 1 | 0 | 0 |
| `blocked_slots` | 15 | 3 | 8 | 2 | 2 |
| `booking_action_requests` | 14 | 4 | 14 | 2 | 1 |
| `booking_audit_events` | 7 | 2 | 3 | 1 | 0 |
| `booking_payments` | 41 | 9 | 30 | 7 | 1 |
| `booking_services` | 7 | 2 | 5 | 1 | 1 |
| `bookings` | 42 | 11 | 21 | 11 | 4 |
| `customer_booking_restrictions` | 3 | 1 | 3 | 0 | 0 |
| `device_tokens` | 8 | 3 | 3 | 0 | 1 |
| `email_events` | 15 | 4 | 4 | 0 | 0 |
| `languages` | 2 | 1 | 1 | 0 | 1 |
| `notification_deliveries` | 6 | 4 | 4 | 0 | 1 |
| `notification_outbox` | 10 | 4 | 6 | 1 | 0 |
| `notifications` | 10 | 3 | 3 | 1 | 1 |
| `payment_anomalies` | 12 | 3 | 8 | 0 | 0 |
| `payment_idempotency_keys` | 9 | 3 | 3 | 0 | 0 |
| `payment_provider_account_audit` | 10 | 2 | 5 | 0 | 1 |
| `payment_provider_accounts` | 11 | 2 | 7 | 2 | 1 |
| `payment_refunds` | 21 | 5 | 16 | 4 | 1 |
| `payment_webhook_events` | 13 | 3 | 5 | 0 | 0 |
| `profiles` | 12 | 5 | 5 | 3 | 2 |
| `salon_access` | 9 | 2 | 7 | 0 | 0 |
| `salon_holidays` | 11 | 3 | 4 | 2 | 3 |
| `salon_images` | 11 | 4 | 4 | 4 | 3 |
| `salon_payout_account_history` | 8 | 2 | 4 | 0 | 1 |
| `salon_payout_accounts` | 11 | 1 | 11 | 3 | 1 |
| `salon_reports` | 8 | 3 | 6 | 0 | 1 |
| `salon_subscriptions` | 14 | 6 | 5 | 2 | 0 |
| `salons` | 29 | 7 | 10 | 8 | 2 |
| `service_categories` | 11 | 2 | 4 | 3 | 2 |
| `service_subcategories` | 12 | 3 | 5 | 3 | 2 |
| `services` | 15 | 4 | 7 | 3 | 3 |
| `staff` | 13 | 3 | 5 | 3 | 3 |
| `staff_service_languages` | 2 | 2 | 3 | 0 | 2 |
| `staff_services` | 11 | 4 | 8 | 2 | 2 |
| `subscription_billing_records` | 27 | 8 | 18 | 3 | 0 |
| `subscription_events` | 10 | 3 | 2 | 0 | 0 |
| `subscription_plans` | 16 | 2 | 8 | 2 | 0 |
| `subscription_provider_accounts` | 7 | 2 | 3 | 0 | 0 |
| `support_messages` | 5 | 2 | 4 | 0 | 0 |
| `support_tickets` | 7 | 2 | 5 | 0 | 0 |

Constraint totals: 44 primary keys, 112 foreign keys, 112 CHECK constraints,
21 unique constraints and one exclusion constraint. All validated. Nine enums
have 34 labels in total:

| Enum | Live labels |
| --- | --- |
| `approval_mode` | `auto`, `manual` |
| `booking_source` | `app`, `manual_walkin`, `qr_walkin` |
| `booking_status` | `pending`, `confirmed`, `rejected`, `completed`, `cancelled`, `checked_in`, `no_show` |
| `payment_method` | `cash`, `online` |
| `payment_status` | `unpaid`, `paid` |
| `salon_approval_status` | `pending`, `approved`, `rejected` |
| `subscription_event_processing_status` | `received`, `processing`, `processed`, `failed` |
| `subscription_status` | `pending`, `trialing`, `active`, `past_due`, `cancelled`, `expired`, `suspended` |
| `user_role` | `super_admin`, `owner`, `staff`, `customer` |

The following hashes fingerprint the final read-only catalog using PostgreSQL
jsonb text serialization, UTF-8 and SHA-256. They are not schema-equivalence
approvals or executed-migration evidence. This fingerprint excludes ACLs,
owners, physical column order and extension functions; those were inspected
separately as described above. Function definitions are present in this final
fingerprint; exact body hashes are listed separately below.

| Category | Objects | SHA-256 of PG jsonb text |
| --- | --- | --- |
| enums | 9 | `c44c8b384b06f9566343783a4824fbd5afb836f475a1177d1626d5ab3fcf8948` |
| tables | 44 | `3784d8a0edb5eeb58d1014d2aed56c98a2d8d2baac9df0df46c7ec249ff6fa28` |
| columns | 540 | `e451669b724c530ef4585f4494b732833f0d63709fc977fe7e8dd93a1e7ff367` |
| indexes | 148 | `40bd30dceb1e334071a0f23df46ef8190bfecf7eb228acce5f13ef5d4fe62cc2` |
| policies | 43 | `6dd5f0170bd42d557d699f9c83bcd9d25d76ab1e087eda66d118b236a5b36fa6` |
| triggers | 74 | `71568e943019a10ae9194b4797755e3a41fe708bcee7783ce5d4bf4be56a2cc1` |
| functions | 52 | `81525f955ff65d7d1c09ceea446751b64bbdc8c5474db13ef057149dceb34c13` |
| constraints | 290 | `da2da9e6d37679dc48e6bb98992c59302f15565d3c04ff883104332edfb6ceda` |

History statement-array fingerprints (raw statements were not returned):

| Supabase version | SHA-256 of stored statements array text |
| --- | --- |
| `20261015100439` | `65f026ddb57ae27dfc59973758961d9a77cdeb35b9f3d94481487d7780627f05` |
| `20261015100737` | `f58bd59f54f9c5616325bd0ba5c65e15990739f086fe13ccac15cfb7189afb92` |
| `20261015100828` | `239a3c610fa3248577c3061df7b37171358f05bee5d57b52416b5123f868a1b6` |
| `20261015101623` | `6ab8ea1b1d9f407212272826b8345649c2fc982433083386d6e4b7e39631907b` |

Input specification SHA-256:
`0771fae99607a4cb35e82a07d592e58a2332622f72c4e3bbe67c027264c37965`.

Unchanged raw SQL baseline SHA-256:
`6dcdea0b7e152cc45ba612878beae71279e949309c09bc79c9ff2aaff65cbe36`.

## Appendix B. Current application functions

All functions are postgres-owned; all have pinned search paths; only postgres
and service_role appear in their explicit EXECUTE ACLs. Body hashes below are
exact UTF-8 prosrc hashes, matching the retained October 15 catalog. Function
identity/result/language/volatility/security/config also match that catalog.

| Identity | Security | Volatility | Exact body SHA-256 |
| --- | --- | --- | --- |
| `app_role()` | DEFINER | stable | `5bc5c42711b1c4590c8d82e551a8d99b3faafea284d22a74dd8e021f79b17cf8` |
| `apply_subscription_billing_record(p_record_id uuid, p_grace_days integer)` | INVOKER | volatile | `aed5c8724e3ccfe6a2860ba24fd9e60ae57ac3aabf79d5b339ee6f1366ce40b6` |
| `booking_append_audit()` | DEFINER | volatile | `28f4ea2f664c539415c3e540d510f4f81f569e6c2d25edddf9b50517cca8c47b` |
| `cancel_salon_subscription_renewal(p_salon_id uuid)` | INVOKER | volatile | `95b712183840641f66afa766e82b9855a1f2ad7af73b9ffcd33383337701af33` |
| `create_booking(p_salon_id uuid, p_staff_id uuid, p_service_ids uuid[], p_start timestamp with time zone, p_customer_name text, p_customer_phone text, p_source booking_source, p_notes text)` | DEFINER | volatile | `66071ed490447a90a47ca7c4bd6b3f8a75cc97d084e6f2fc2ecdc28127024079` |
| `deactivate_device_token(p_token text)` | DEFINER | volatile | `6e314c9ec7bf495a3c65fe5f6151226513be7016d2984b33e37fa36d05cc011c` |
| `demote_other_main_images()` | INVOKER | volatile | `38f571a13b8a2f624b3c596334fa28d50d725ada64f9cd0d39637fa92f2c1ab1` |
| `effective_duration(p_staff_id uuid, p_service_id uuid)` | INVOKER | stable | `ba259cbc9d0f33fef2d4d23d9afc59155fac5df2b757d779c0d45da03d3520c1` |
| `enqueue_booking_email()` | DEFINER | volatile | `497f19c2510b0c8bd53460d21b9e632e4be98ea065c41190bba5402049184f1b` |
| `enqueue_verified_payment_receipt()` | DEFINER | volatile | `e7dde37365e019fcfbc0840dea35ec1d70052b85df0b7d3fdb3b6a55d1a98292` |
| `erase_profile_references(p_user uuid)` | INVOKER | volatile | `96ea2e1f00901fde39e5beba1b635a1b7d4867ef6e40acf262079df3d5053c8b` |
| `get_active_tokens(p_user_id uuid)` | DEFINER | stable | `1cfe2254b85a778c82514414eb16263166190be8d6e1313097011e2bd4b16a52` |
| `get_available_slots(p_staff_id uuid, p_date date, p_duration_minutes integer)` | DEFINER | stable | `ddad8320219828ef4548c3c80c1d74b84d07754fb8877f2839442bac1a8a0d67` |
| `get_salon_by_qr(p_qr_token text)` | DEFINER | stable | `adbef86629e09c114926895d013656c1159239e252a08fa4d592c0379fc7672d` |
| `guard_audit_immutable()` | INVOKER | volatile | `2b4b7efe62bf83f13e4400484d3650aebcf88591c86816b7b088243c7e08971c` |
| `guard_booking_against_closure()` | INVOKER | volatile | `6e36a1c59d99c6d60e63554b1689a821b16db6eb4164bbb1001d7f61b38cfd11` |
| `guard_booking_checkout()` | DEFINER | volatile | `f2cd1cb5dc38da536f5396ec9fe18df7ceb4c35567f981274061619aa927018e` |
| `guard_booking_payment_columns()` | INVOKER | volatile | `82c8e6ce130b6818b1d60a0a735ac1eae5edbda5133e5d28518153a87906cf30` |
| `guard_booking_salon_approval()` | INVOKER | volatile | `4e9a1d81ef14447a3ba1ad7c40f730144e26e507cfa29c6656c8f24e866572f5` |
| `guard_collection_snapshot()` | INVOKER | volatile | `7eca04363bf3325ad6339b3aaa3c84f534b2576166259512effb52239f93f728` |
| `guard_media_reference()` | INVOKER | volatile | `3e42e9bf0fae138ee11ca67cfd161aa646e186e7508c791af98c266a00d3dc3a` |
| `guard_salon_approval()` | INVOKER | volatile | `e95ff8ef83b7f0e07eb7cfd23d465fc7cfc77c2c14f4c009b6cb2173894518b2` |
| `guard_salon_discovery_placement()` | INVOKER | volatile | `af47c72d1fbd8e2a05ae48afc3594a92756d301028edc65f43b94a132b3c3362` |
| `guard_salon_display_priority()` | INVOKER | volatile | `079c298af8aa5db223d9b56181145a0554dfc8b718b2a4448d4c3ad47ff5a87e` |
| `guard_subscription_admin()` | INVOKER | volatile | `db11523ee7ff1f9fd8ef06de1d277e5d674ec1714370dc974305b0953374b8f3` |
| `handle_new_user()` | DEFINER | volatile | `431a17c114c4df9ca52ae089e07dacbfaae972529184ad1cbd47e135d7d70be3` |
| `is_subscription_promotion_active(p_status subscription_status, p_current_start timestamp with time zone, p_current_end timestamp with time zone, p_grace_end timestamp with time zone, p_now timestamp with time zone)` | INVOKER | immutable | `2c6f9f13078530c671ff091a0c4db6f41edda40495e338c4e8b74bd94170804b` |
| `is_super_admin()` | DEFINER | stable | `920e2e7d4fd64a989d2fb1245f6303ac91fc5dfb314888e4234b3bdc1d3ae47e` |
| `owns_salon(p_salon_id uuid)` | DEFINER | stable | `e739512504a696ef71d9602aaeda4b1d31a40c17f433cf80ebb21fbc5a5f7638` |
| `payment_append_audit()` | DEFINER | volatile | `219073b5b938ef12c8adea390dbc07e769005beb51a6f7c57c7fabce4bff19f1` |
| `payout_account_snapshot(r salon_payout_accounts)` | INVOKER | immutable | `906e9c01ccb7d31ab1c730e3399cb0990456eb469366574b238736b57699c480` |
| `recompute_booking_payment_state(p_booking_id uuid)` | INVOKER | volatile | `c60cc131f1969a92ccb16ba156ee1739d53ce7c5dbe0155a6314002c22be9cb1` |
| `recompute_salon_trial(p_salon_id uuid)` | DEFINER | volatile | `70a47c185282e1a74da282468ea4c03bd14dfa4776684abc0b410961404c6ca0` |
| `register_device_token(p_token text, p_platform text, p_device_name text)` | DEFINER | volatile | `4b059553479f840ba5a2ee926bbd04f3b3d464680226b27ed3042cb96542eec4` |
| `salon_booking_eligible(p_salon uuid)` | DEFINER | stable | `686a98ddd1446c69da30288834d36321dad53002eb10484a5ec41f7aa984afaf` |
| `salon_payout_account_masked(p_salon_id uuid)` | DEFINER | stable | `6e3e2047e95ab0ccdc65e87f07a35d53c02f7531d20ec82796d29dc2f98407a5` |
| `salon_trial_setting(p_name text, p_default integer, p_min integer, p_max integer)` | INVOKER | stable | `3d4c59503dc12539763b53e9097c279b9146b337f18580c5992c8066416b2817` |
| `set_audit_actor()` | INVOKER | volatile | `ab407f5b457f009cd2554c0d0eafacfde44f00e2e8849e43d9dbc9eed9fad8e4` |
| `set_updated_at()` | INVOKER | volatile | `841a7f70d98dd76c757140230eb8eac2a7d14eaf6c6136bc73ade388165ce43a` |
| `stamp_booking_lifecycle()` | INVOKER | volatile | `3ba4163ab209e2426d4bae85aad490eb59add0e01ded2cfb603a946b62f87369` |
| `stamp_checkout_policy()` | INVOKER | volatile | `aca069b033a6ba102d04e9e1b50d6f4d55f36939093c613e841e36cd847611ab` |
| `stamp_notification_read_at()` | INVOKER | volatile | `952b469188c301072aa55b1d445fd5cb3e9d9a7532336e40c6dbd4a7722d4f6c` |
| `start_salon_trial(p_salon_id uuid, p_at timestamp with time zone)` | DEFINER | volatile | `60b646f31188745a363a029fb53e576e2214c6daec5a9b1b1f19579baeb6274e` |
| `sweep_lapsed_subscriptions()` | INVOKER | volatile | `8b84c89ffbd4c652a068e7eec94bbd6daea379f5047d7e0a458320b99679ab48` |
| `tg_booking_payments_guard()` | INVOKER | volatile | `8d89d52cdbf791642a720672e7308d4e4b530112f682520800438d80bbfc8ceb` |
| `tg_booking_payments_recompute()` | INVOKER | volatile | `110f205f5f5f13f34cef2610cfce43099790254cfcd47ac30e46b5e57dff4a2e` |
| `tg_bookings_recompute_trial()` | DEFINER | volatile | `fc5bab43e860503805280f1103b03fbff98e7ccd18e2da723a69a97de7b1af85` |
| `tg_payment_refunds_guard()` | INVOKER | volatile | `e7979826790c41659cb42d91e91ec9a9a6e5073367b853e59f0c6e763ef2af4d` |
| `tg_payment_refunds_recompute()` | INVOKER | volatile | `c24024f5fa7b708163fa2fcde4b97214528b7a04bc388cb5c0d86249b68c991a` |
| `tg_salon_payout_account_history()` | INVOKER | volatile | `7a064094e981de1623173ccdc77e223f564cc676c6c866117a40dfe67860a3bd` |
| `tg_salons_access_row()` | DEFINER | volatile | `eb490f4a8f1743ea015effdca32fd2cebe21b1da599b7244889ecb9c3ab75bba` |
| `tg_subscription_billing_guard()` | INVOKER | volatile | `c5efc98ef11174d8a17d16a909fa789763b09ac478f8a3f9bd8e1cbb78c631b8` |

## Appendix C. Unclassified live text/JSON/array fields

Compared statically to COLUMN_TREATMENT in
`backend/tests/integration/test_account_deletion_sql.py`. These 43
missing classifications predate the proposed 43 new tables. The two legacy
cancellation fields are already classified for scrub. Missing classification
does not itself determine the lawful action.

- `api_rate_limits.bucket_hash`
- `booking_audit_events.event_type`
- `booking_audit_events.new_state`
- `booking_audit_events.old_state`
- `booking_payments.collection_method`
- `booking_payments.commission_base`
- `booking_payments.commission_policy_version`
- `booking_payments.provider_session_id`
- `bookings.checkout_policy_version`
- `email_events.body`
- `email_events.event_key`
- `email_events.event_type`
- `email_events.last_error_code`
- `email_events.provider_message_id`
- `email_events.recipient`
- `email_events.status`
- `email_events.subject`
- `payment_anomalies.detail`
- `payment_anomalies.kind`
- `payment_anomalies.provider`
- `payment_anomalies.provider_ref`
- `payment_provider_account_audit.action`
- `payment_provider_account_audit.detail`
- `payment_provider_account_audit.new_status`
- `payment_provider_account_audit.previous_status`
- `payment_provider_account_audit.provider`
- `payment_provider_account_audit.vendor_ref`
- `payment_refunds.kind`
- `salon_access.trial_ended_reason`
- `subscription_billing_records.benefits`
- `subscription_billing_records.billing_interval`
- `subscription_billing_records.currency`
- `subscription_billing_records.failure_code`
- `subscription_billing_records.plan_code`
- `subscription_billing_records.provider`
- `subscription_billing_records.provider_order_ref`
- `subscription_billing_records.provider_payment_ref`
- `subscription_billing_records.receipt`
- `subscription_billing_records.status`
- `subscription_plans.features`
- `support_messages.body`
- `support_tickets.status`
- `support_tickets.subject`

## Verification and stopping point

Verified live: Mumbai identity/region, empty Alembic version table, four Supabase
history entries, complete public catalog inventory, application function bodies,
Auth signup attachment, policy definitions, direct/effective client and server
privileges, role memberships/defaults, extension exclusions, publications,
aggregate financial occupancy and existing plans.

Verified offline: 40-revision single-head source graph; unchanged specification
and baseline hashes; 43 proposed table names absent; proposed existing-table
columns absent; historical catalog/category/function-hash equality; 43 existing
erasure classification gaps. No code import, test suite or database-building
runner was needed.

Not established: historical Alembic execution/backfill completeness, independent
expected-PG17-0040 equivalence, deployed runtime role/code behavior, authenticated
RLS/API denial execution, money/concurrency/erasure tests, lawful retention or
provider capabilities/settlement. Those are future approval/verification gates.

No upgrade, downgrade, stamp, DDL, grant/revoke, SQL sidecar, executable revision,
Cashfree access, infrastructure/frontend change, commit or push occurred.
Inspection stops here; migrations and all financial designs remain held.

