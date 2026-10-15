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
