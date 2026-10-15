# Mumbai reconciliation — least privilege

Preparation update: actual repository revisions 0038–0040 now replace the standalone
drafts below. See [current forward plan](../../docs/migrations/MUMBAI_FORWARD_RECONCILIATION.md).
The latest security revision has zero positive grants, removing the two redundant
server grants described in this earlier proposal. No migration or stamp was executed.

Review-only for `wqjlgpnbiapcrlkxumcp`, ap-south-1. **Nothing executed.** No stamp,
history insertion, Sydney/GCP/Docker/Cloud Run/production action. This replaces the
combined draft and removes its global future-function change.

| Deliverable | Exact file |
| --- | --- |
| Schema-only migration draft | [01-schema-only.sql](migration-mumbai-review-2026-10-15/01-schema-only.sql) |
| Security/grant migration draft | [02-security-grants.sql](migration-mumbai-review-2026-10-15/02-security-grants.sql) |
| Signup-trigger migration draft | [03-signup-trigger.sql](migration-mumbai-review-2026-10-15/03-signup-trigger.sql) |
| Alembic history plan | [04-alembic-history-plan.md](migration-mumbai-review-2026-10-15/04-alembic-history-plan.md) |
| Rollback plan | [05-rollback-plan.md](migration-mumbai-review-2026-10-15/05-rollback-plan.md) |
| Exact differences | [differences.md](migration-mumbai-review-2026-10-15/differences.md), [JSON](migration-mumbai-review-2026-10-15/exact-differences.json) |
| Every proposed privilege | [privilege-matrix.csv](migration-mumbai-review-2026-10-15/privilege-matrix.csv) |

These are standalone SQL migration **drafts outside the Alembic chain**, not release-ready
Alembic revisions. Head remains `0037_customer_processing_charge`; destination history
remains empty. Do not execute the standalone files and later replay duplicate revisions.

## Privilege decisions

No ALTER DEFAULT PRIVILEGES statement remains in the new drafts: neither global nor
schema defaults change. No broad function grant, client grant, role membership, schema
grant, extension ACL change or table DML grant is proposed. Postgres is the current
backend connection/owner and needs no additional grant.

The only positive grants explicitly restate existing server rights:

| Object | Grantee | Privilege | Reason | Existing only | Future objects |
| --- | --- | --- | --- | --- | --- |
| public.create_booking(uuid,uuid,uuid[],timestamptz,text,text,public.booking_source,text) | service_role | EXECUTE | Preserve server-only booking RPC contract (0024); already granted | Yes | No |
| public.get_available_slots(uuid,date,integer) | service_role | EXECUTE | Preserve server-only availability contract; already granted | Yes | No |

No WITH GRANT OPTION. These add zero authority on observed Mumbai; they preserve the
reviewed server contract, not a claim the postgres-based backend needs a new grant.
Other existing owner/service-role ACLs remain unchanged. This is not a claim that the
existing privileged runtime account or every retained service-role grant is minimal;
reducing those requires a separate backend/worker call-contract review.

For each of 44 named tables, revoke all table privileges from PUBLIC, anon and
authenticated. For each of 52 named application functions, revoke EXECUTE from those
three grantees. The CSV expands every object/grantee/privilege individually (1,214 rows
including two positive grants). Current client rights are already absent: these
statements codify the restricted model. Preconditions reject unexpected owners,
extension membership, object kinds and column ACLs; postconditions reject inherited
effective client privileges. No extension members or future objects are targeted.
The security draft captures postgres/service_role effective application table/function/
sequence access in transaction-local metadata before revokes and aborts if any retained
right is lost afterward. This includes inherited rights; no persistent setting is added.

Existing global postgres function defaults already deny PUBLIC EXECUTE. This draft
does **not** undo that setting, since undoing it could reopen future functions. Existing
public defaults grant service_role future rights; these pre-existing defaults are
captured and unchanged. "Future objects: no" in the matrix describes the proposed
statements, not absence of existing default ACLs.

Each future function's own migration must revoke PUBLIC/client EXECUTE and grant only
the exact named server role on its exact signature within the same transaction. Do
not rely on global defaults for safety. Existing-object GRANT and future-object defaults
are separate; schema defaults cannot subtract global grants.
[PostgreSQL default privileges](https://www.postgresql.org/docs/17/sql-alterdefaultprivileges.html).

## Remaining gates

Classify both cancellation fields for account erasure, including pre-existing values,
before creating actual revisions. Free text is potentially personal data; current
Mumbai has no bookings. Update the approved erasure contract/function/tests before
promoting the schema draft. The draft preserves fields, authorizes no new application
writes and does not itself implement a privacy-policy change.

All 43 RLS policies remain unchanged. blocked_slots USING(true) is not permission to
expose fields. Direct client/Realtime reads remain denied pending separate review.
Keep R2; Supabase Storage remains unused.

After separate design approval, prepare reviewed revisions, perform authorized disposable
PG17 schema/ACL/trigger/erasure tests, compare exact expected head with Mumbai including
effective/default ACLs, then request separate execution/stamp approval as applicable.
No migration was executed even locally this turn. The applicable
[Alembic skill](../../../.claude/skills/alembic-migration/SKILL.md) says: "Never auto-run. Never run
against anything but a local/throwaway DB. Show the command and let the user run it."

**Next approval:** approve or revise the separate drafts and object-level matrix for
promotion into repository revisions. Execution and stamping remain explicitly excluded.
