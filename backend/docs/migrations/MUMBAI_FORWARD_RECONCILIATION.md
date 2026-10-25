# Mumbai forward reconciliation — prepared, not executed

Only project `wqjlgpnbiapcrlkxumcp` is in scope. Earlier execution approval allowed
backup and SQL transaction preflight; exact 0038–0040 SQL was tested and rolled back,
including a corrected 0040 parser error. No migrations were committed to the database.
The latest user instruction holds all migrations uncommitted and unapplied until
customer/owner refresh passes staging tests. No Alembic stamp is authorized. Sydney,
production environment and all infrastructure remain untouched.

Current findings: [refresh audit](../verification/mumbai-refresh-audit-2026-10-15.md),
[two designs and staging gate](../verification/mumbai-refresh-designs-2026-10-15.md),
[execution preflight report](../verification/mumbai-execution-hold-2026-10-15.md).

Business reads/writes stay in FastAPI. Client application-table grants remain zero;
direct-client SQLSTATE 42501 is expected. Test ownership through FastAPI; do not add
grants to make direct-client row-filter probes pass. RLS stays as defense in depth.

## Prepared chain and expected schema

| Revision / SQL file | Parent | Repository 0037 before | Approved target | Current Mumbai |
| --- | --- | --- | --- | --- |
| 0038_cancellation_compatibility | 0037_customer_processing_charge | Both legacy columns absent | Both nullable text, no default; pre-existing definitions must match | Already present |
| 0039_promotion_search_path | 0038_cancellation_compatibility | Promotion helper config unset after 0030 | search_path=public, same body/owner/invoker/immutable | Already hardened |
| 0040_fastapi_only_access | 0039_promotion_search_path | Some client RPC/read grants and creator-dependent defaults | Revoke client rights on 44 named tables and 52 app functions | App client rights already absent |

The Python files in migrations/versions load their same-named SQL files from migrations/sql/.
These are forward revisions, not a new baseline. All use Alembic's transaction, bounded
lock/statement timeouts and separate execute calls per SQL statement. No positive grants,
future-object default changes or extension ACL changes. Existing server effective rights
are captured/checked to avoid accidental privilege loss through PUBLIC/inheritance.

No new signup-trigger revision is needed: the existing reviewed Auth trigger is present
and functionally verified using rollback-only SQL Auth rows. Do not replace it or replay
the old draft. No account-erasure SQL function replacement is needed: erase_profile_references
handles FK detachment, while the adapter must clear these free-text values first.

## Erasure classification and behavior

| Field | Classification | Customer deletion | Owner deletion | Retention reason |
| --- | --- | --- | --- | --- |
| bookings.cancellation_reason_code | Scrubbed / potentially personal arbitrary text | NULL on their bookings before customer FK detaches | NULL on all bookings in their owned salons | No value retention justification supplied |
| bookings.cancellation_reason_text | Scrubbed / potentially personal free text | Same | Same | Same |

Neither field has an allowlist, so even code can contain personal text. Do not retain
arbitrary values as legal/audit identifiers or copy them into a new archive. Records,
booking IDs, amounts and existing approved financial metadata remain under the existing
account-deletion contract. An unrelated customer's bookings outside the erased scope
remain unchanged. Owner deletion also clears these fields on retained customer history
because the fields may contain owner/staff-written personal content. Null stays null;
retries are idempotent. No bulk backfill or migration-time scrub is proposed.

The account-deletion adapter clears both fields before erase_profile_references nulls
customer/owner references; otherwise identity linkage could be lost before scrubbing.
The owner UPDATE predicate explicitly includes either field being nonnull, including
rows whose existing rejection/cancellation fields are already empty. Financial rows
and business state are not rewritten by this new field handling.

Apply/reconcile the schema before deploying the changed adapter to a database that lacks
these columns. Preparing this code does not authorize deployment. The existing wider
classification guard predates several post-0028 tables; unrelated classification gaps
are a separate release risk and must not be mislabeled as complete coverage.

## Rollback / execution gate

No committed migration or stamp execution occurred. SQL preflight ran inside a transaction
and rollback was verified. Before COMMIT, the owning transaction can be rolled back.
After a committed deployment, preserve columns and security restrictions; all three
downgrades refuse destructive schema/privilege reversal. Use separately reviewed forward
repairs. Never resurrect erased personal values or restore broad client grants. If code
must be rolled back, retain the new scrub behavior or stop erasure processing; reverting
to old scrub logic could retain these fields. No infrastructure action is authorized here.

## History reconciliation

Exact source baseline remains 0001_baseline applying 001_supabase_schema.sql. Mumbai is
not that bare baseline: it is a schema-SQL restore of a 0037-shaped database plus two
legacy columns, hardening and four Supabase migration-history supplements. Its empty
public.alembic_version does not prove missing upgrades and must not be fabricated.

The earlier 37-revision review and fresh catalog bridge are evidence about final effects,
not historical execution/backfills. New repository head is 0040_fastapi_only_access only
because these prepared source files exist; Mumbai history remains empty. Existing head
comparison was against 0037, not an executed/reproduced 0040 reference.

Never stamp 0037 while differences remain. Before proposing any stamp: independently
build the reviewed expected 0040 head in an authorized disposable PG17 environment,
resolve consolidated-baseline replay limitations, compare every final object definition,
owner/config, constraints/indexes/triggers/RLS, effective/inherited/column/default ACLs
and extension exclusions with fresh Mumbai metadata. Existing global/schema defaults
must be explicitly accounted for; these revisions intentionally do not change them.
No equality proof exists yet, so no stamp command is supplied. If exact approved head
equality is later proved, present its exact unexecuted command and seek separate approval.

Next approval concerns migration execution only after code/security/privacy review and
expected-head proof; the current approval covers preparation and rollback-only tests.

The prepared [privilege matrix](../verification/mumbai-forward-privileges-2026-10-15.csv)
expands all 1,212 existing-object revocations by object/grantee/privilege. There are no
positive grants; the two redundant service grants in the earlier standalone proposal
were removed because those rights already exist and are preserved by assertions.

## 24 October: independent expected0040 reference (preparation only)

A disposable PostgreSQL17.11 reference replayed the portable0037 fixture followed
by the exact0038-0040 sidecars. The generic fixture initially lacked Supabase's
explicit service_role function execution grants, so the0040 guard correctly
refused it. Matching grants were added only to that disposable bootstrap; the
second replay passed. No guard was weakened and no remote grant was issued.

Fresh Mumbai SELECT-only catalog evidence covered44 tables,540 columns,148 indexes,
52 functions,73 triggers,43 policies,290 constraints and7 default ACL records.
Columns, normalized function definitions/configuration, indexes, triggers and RLS
policies matched the reference. Twenty-four tables differed only in raw ACLs,
including additional explicit Supabase service_role rights. Seven managed default
ACL entries require explicit classification. One subscription interval constraint
differs in array-element cast placement and needs semantic equivalence review.

This is not complete expected-head equality or historical backfill proof. Effective
inherited/schema/column/sequence privileges and extension exclusions still need
reconciliation. Empty remote Alembic history remains unchanged; no stamp/upgrade
command is authorized by these results. Prepared0041-0046 are not applied.

Local ignored evidence: `backend/.artifacts/release-remote-catalog-20261024.json`,
`backend/.artifacts/native-pending-20261024/expected-0040-catalog.json` and
`reference-0040-diff.json`. The disposable reference container was removed.

## 25 October: effective privileges and current data invariants

Fresh read-only Mumbai metadata was compared with a newly replayed disposable
PostgreSQL17.11 reference through exact0040. For anon/authenticated, all44 application
tables,540 columns and52 application functions have zero effective table/column/EXECUTE
rights. This includes inherited/PUBLIC effects through PostgreSQL privilege helpers.
There are no memberships for the three reviewed roles and no non-extension public
sequences. Application function EXECUTE privileges match the reference for all three
roles. No remote privilege changes occurred.

Remaining effective differences are explicit: service_role has managed BYPASSRLS,
extra rights on24 tables/296 columns, and schema USAGE on auth/storage/extensions;
the minimal local fixture lacks part of that managed platform setup. Seven managed
default ACL records remain outside the fixture. These must be classified/preserved
under an approved adoption plan; copying the production grants into the reference
would not independently prove historical migration execution. No comparison result
authorizes a stamp, replay from baseline or weakening of the migration guard.

The single interval CHECK difference is cast placement: individually cast varchar
array elements versus a varchar-array-to-text-array cast. A SELECT-only comparison
covered four accepted values, NULL, empty, mixed-case, invalid and trailing-space
inputs:9 cases,0 truth-value differences. This supports semantic equivalence of
that expression and is not general normalization of arbitrary constraints.

Current payment-state audit followed the existing0037 calculation: all20 bookings
have zero mismatches in paid_amount, refunded_amount and payment_status versus the
ledger. This establishes those current invariants only; it does not recreate every
historical backfill/seed or authorize0041–0046 execution. Real-data backup, remaining
history adoption proof and the approved release procedure remain gates.

Ignored evidence: `.artifacts/remote-effective-acl-20261025.json`,
`.artifacts/effective_acl_catalog_20261025.sql`,
`.artifacts/acl-reference-20261025/expected-effective-acl.json` and
`effective-acl-diff.json`. No remote migration/history mutation occurred.

## 25 October: original-grant recovery and actual-data forward rehearsal

The actual encrypted current Mumbai archive was restored into a network-isolated
Supabase PostgreSQL17.6.1 container **with original owners and ACLs enabled**. Its
platform bootstrap needed a local NOLOGIN `supabase_realtime_admin` role and the
database owner `postgres`, confirmed independently by a source SELECT. After
these prerequisites, archive restore exited0. A clean restore's effective roles,
tables, columns, functions, schemas, sequences, memberships and seven default ACL
entries matched the captured Mumbai metadata with zero differences. This closes
the earlier recovery omission; it is not an independent historical-execution proof.

The exact prepared SQL sidecars0041→0046 then replayed successfully, in order and
in separate transactions, on a restored real-data copy. Original row counts stayed
14 profiles/10 salons/20 bookings/20 booking_services/14 Auth users. Removed fields,
duplicate active image URLs and over-limit galleries all counted0 afterward;
no financial/change-history rows were invented. Alembic history remained empty.
Hashes and acceptance are in `.artifacts/restored-forward-chain-20261025.json`;
grant recovery is in `restored-acl-comparison-20261025.json` and
`real-backup-ownership-20261025.json`. No remote sidecar or stamp was executed.

Read-only migration review still identifies these release blockers:

1. History adoption must be reviewed as adoption of a verified current state,
   preserving the enumerated managed-platform ACL differences, not a claim that
   all historical upgrades/backfills executed. Existing policy supports neither
   stamp nor0041–0046 execution; do not weaken it or bypass it with remote SQL.
2. The account-erasure integration suite targets an older schema. The immutable
   change/finance tables introduce JSON/text and staff identifiers not covered by
   its current classification. Prove full-head erasure and retention behavior
   before releasing that broader chain; passing booking/finance tests alone does
   not close this privacy gate.
3. Coordinate compatible API/client deployment around irreversible field removal.
   A previously successful narrow hotfix does not validate a full-source release.

An acceptable adoption proposal must seal the source, expected-head comparison,
managed-role/default-ACL exceptions, current backfill invariants and fresh tested
backup. It must identify the exact approved adoption operation and forward tranche,
then pass the migration policy and obtain the operator's approval. No executable
remote-adoption command is supplied while those gates remain open. Cashfree
activation and provider-money operations remain deferred by the user.

## 25 October: approved audit privacy transformation prepared as0047

The user resolved the new audit retention decision: remove personal text and hash
request/reference identifiers, preserving amounts and dates. Forward0047 and the
compatible erasure adapter are prepared locally. Populated0046 fixtures first
reproduced retained personal text; head0047 checks now exercise both account roles,
immutable financial history, real service-role execution, client denial, typed JSON
scrubbing, rollback and reference/key uniqueness across raw and hashed values.
No historical migration or existing approval evidence was edited.

The exact0041–0046 restored-real-data rehearsal above remains evidence for that
specific tranche, not0047. New0047 is exercised against synthetic local data and
still needs inclusion in the sealed candidate/release review. The explicit new
two-table privacy classification does not close broader legacy schema/worker
acceptance. Do not adopt history, apply the forward chain or activate erasure from
this note. Source head47 remains outside currently authorized migration policies.

The legacy Sydney project is user-confirmed paused, with source continuity still
unverified. This is not a deletion decision and does not alter recovery gates.
