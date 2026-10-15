# Mumbai forward revisions — prepared only

Scope: `wqjlgpnbiapcrlkxumcp`, Mumbai. No migration, schema/grant/trigger SQL or Alembic
stamp executed, even locally. Only synthetic rollback DML/runtime tests and read-only
metadata checks ran. Sydney, GCP, Docker, Cloud Run, production environment and traffic
were not accessed or modified. Branch: `thameem/mumbai-forward-reconciliation`; no commit,
push, deployment or PR. Existing unrelated user changes were preserved.

## Deliverables and schema before/after

| Migration file | Exact SQL | 0037 reference before | Prepared target | Current Mumbai |
| --- | --- | --- | --- | --- |
| [0038_cancellation_compatibility.py](../versions/0038_cancellation_compatibility.py) | [0038 SQL](../sql/0038_cancellation_compatibility.sql) | Two columns absent | Nullable text code/text, no defaults, reject conflicting definitions | Already present; preserved |
| [0039_promotion_search_path.py](../versions/0039_promotion_search_path.py) | [0039 SQL](../sql/0039_promotion_search_path.sql) | Promotion helper search_path unset after 0030 | Fixed public path; same body/owner/invoker/immutable | Already matches |
| [0040_fastapi_only_access.py](../versions/0040_fastapi_only_access.py) | [0040 SQL](../sql/0040_fastapi_only_access.sql) | Historical client permissions differ | Explicit existing-object revokes on 44 tables / 52 functions | Clients already denied |

New sole repository head: **0040_fastapi_only_access**. Historical 0001–0037 sources and
baseline unchanged. Prepared revisions use raw SQL, one statement per execute, bounded
timeouts and Alembic-owned transactions. No new baseline, role, policy, table DML grant,
positive function grant, future default, extension ACL change or signup-trigger DDL.
The latter is unnecessary because the existing signup trigger passed runtime validation.

Security applies only where required to codify FastAPI-only access against earlier source
behavior. All app-table/client rights stay zero. Direct-client 42501 is expected; direct
row-policy success is not required by this architecture. Explicit server grants already
exist, so the previous draft's two redundant positive grants were removed. Before/after
effective server checks protect retained inherited access. The
[1,212-row privilege matrix](../../docs/verification/mumbai-forward-privileges-2026-10-15.csv)
names every object, grantee, privilege, reason and existing/future scope. Future scope:
none conferred by these statements. Existing defaults are left unchanged and disclosed.

## Erasure behavior

Both bookings.cancellation_reason_code and cancellation_reason_text are classified
as **scrubbed, potentially personal arbitrary text**. They are erased to SQL NULL:

- Customer deletion: only that customer's bookings, before customer/profile FK detachment.
- Owner deletion: every booking in their owned salons, including retained customer history.
- Unrelated customer/salon records remain unchanged; retries are idempotent.
- Booking IDs, statuses, prices and financial records remain under the existing contract.

No allowlist makes code a trustworthy non-personal identifier. No value retention is
claimed for legal/audit purposes and no archive/backfill is introduced. New handling is
in the account-deletion adapter, not a replacement SQL erasure function: generic
erase_profile_references still detaches FKs after these values are cleared. Owner UPDATE
also matches rows where only the two legacy fields remain nonnull. Both columns remain
in the schema; values are not erased by the migrations themselves.

Canonical integration classification/fixtures/assertions now cover both columns; unit
tests cover forward chain, no client/future grants, preserving columns, scrub-before-
detach ordering and owner predicate coverage. Existing deletion/worker tests remain.

## Validation

**Static/local suite:** 887 passed, 62 skipped, one existing dependency deprecation
warning. Integration DB opt-ins were unset, so tests could not execute migrations on any
database. Unit tests that capture existing migration SQL use mocks rather than database
execution. Initial test collection exposed the local driver configuration; tests were
isolated with an inert process-only asyncpg URL. Two test assertion failures were fixed
(AST values attribute, expected new head), then the complete suite passed. Ruff passes
for app/tests/migrations and relevant validation helpers. Alembic heads reports only 0040.

**Real Mumbai rollback:** 57 passing result entries and 2 not-applicable direct row-filter
entries. Four cross-customer/owner booking reads returned expected 404 using two actual
synthetic owners and two customers. Each account-deletion scenario populated both fields,
ran the real repository erase_database, verified profile removal inside its savepoint,
both fields NULL, retained booking amount/status and unrelated salon values unchanged,
then repeated deletion to prove idempotence and rolled back the scenario. Subsequent
booking/collection/cancellation/no-show/support/audit/worker tests passed.

Auth signup trigger, real service_role availability and booking RPC, and existing fixed
function paths passed. Direct-client reads produced exactly two expected SQLSTATE 42501
errors; no unexpected runtime failure. Email/push use fake providers, and API actor
extraction is injected to avoid persistent Auth sessions. JWT/Google/email delivery and
deployed API/worker scheduling are not proven here.

All synthetic records rolled back. Full public/Auth row counts, schema/function catalog,
ACLs, default ACLs and memberships equal before/after. A fresh independent Mumbai MCP
SELECT confirms: Auth users=2, profiles=2, salons/bookings/payments/audits/email events=0,
alembic rows=0, client application table/function privileges=0. The original two staging
accounts remain; no production data was used. No credentials or personal rows were output.

## Exact baseline, comparison and history

Source baseline is **0001_baseline** → backend/migrations/sql/001_supabase_schema.sql.
SHA256 of that SQL:
`6dcdea0b7e152cc45ba612878beae71279e949309c09bc79c9ff2aaff65cbe36`.
The verified restored backup is a separate, later schema snapshot, SHA256:
`2506c4fc8da90d63a7cbfb7a0b727df9e492f5e65e6b09bff4c7136a3d273eef`.
Mumbai is a 0037-shaped schema-SQL restore plus two legacy columns/hardening, not a bare
0001 database and not proof of sequential execution. Four existing Supabase migration
entries record restore/supplements; Alembic remains empty.

All 37 historical revisions were re-inventoried against fresh Mumbai metadata using
selected per-revision object requirements and the complete catalog bridge to the earlier
head comparison. No missing selected requirements; no catalog drift from the audited
destination. Exact source hashes and supersession notes are recorded. Historical
backfills/execution are not inferred. Known differences from 0037 remain the two columns,
function config and ACL/default environment; PG18 NOT NULL catalog entries and equivalent
CHECK cast formatting are version artifacts.

**A reproduced expected 0040 schema/ACL comparison has not run. Equality is not proved,
and stamping is unsafe. No exact stamp command is supplied.** Preparing source files
changes the repository head; it does not apply them or reconcile destination history.
After separate authorization, a disposable PG17 expected-head build must account for
consolidated-baseline replay limitations and representative managed roles/defaults.
Compare every final column/constraint/index/function/owner/config/trigger/RLS definition,
effective/inherited/column/default ACL, managed extension exclusion and necessary seeds
with fresh Mumbai. Do not silently ignore default differences or claim object counts
alone prove equivalence. Only after matching the actual reviewed head should its exact
unexecuted stamp command be presented for separate approval. Never replay base-to-head
on the restored database or write fabricated historical rows.

## Rollback and exact remaining risks

No migration rollback is needed now. Uncommitted future SQL can roll back in its owning
transaction. All three downgrades explicitly refuse destructive reversal: never drop
these columns, reset hardening, restore broad grants or resurrect erased values. After
commit use a separately reviewed forward repair. Code rollback must retain the new scrub
handling or stop erasure processing under a separately authorized operational plan.

Remaining risks/gates:

1. Migration SQL has not been executed/validated in a disposable reference; complete
   expected-0040 equality and effective ACL reproduction remain unproven.
2. The adapter requires both columns. Schema reconciliation must precede deployment to
   any database missing them. No deployment is authorized by this work.
3. **43 pre-existing text/JSON classification gaps** remain across newer audit/support/
   email/payment/subscription fields. Their exact names are in the baseline evidence.
   Both requested columns are covered, but full-schema privacy/erasure certification is
   blocked; the existing classification guard must remain visible, not silently weakened.
4. Existing global/schema future defaults remain unchanged. Dedicated least-privilege
   runtime-role design and managed-default compatibility are separate reviews; these
   revisions do not claim the existing postgres/service account is minimal.
5. Existing strict-certificate/upstream TLS, Auth sender/redirect/delivery, R2/deployed
   staging/browser and real worker/provider readiness issues remain outside this run.

**Separate approval required for execution:** review the three prepared revisions,
erasure policy/code and matrix, resolve release gates, then explicitly authorize any
disposable migration validation. Mumbai SQL execution and any later stamp remain separate
decisions. Current approval covers preparation and rollback-only DML only. The
[Alembic skill](../../../.claude/skills/alembic-migration/SKILL.md) also states: "Never auto-run.
Never run against anything but a local/throwaway DB. Show the command and let the user
run it." No migration command was run or placed in startup/CI by this task.

## Evidence

- [Current repository plan](../../docs/migrations/MUMBAI_FORWARD_RECONCILIATION.md)
- [Rollback runtime evidence](migration-mumbai-forward-runtime-2026-10-15.json)
- [Independent postcheck](migration-mumbai-forward-postcheck-2026-10-15.json)
- [Fresh metadata catalog](migration-mumbai-forward-catalog-2026-10-15.json)
- [37-revision comparison](migration-mumbai-runtime-revision-review-2026-10-15.json)
- [Baseline hashes and exact classification gaps](migration-mumbai-forward-baseline-2026-10-15.json)
