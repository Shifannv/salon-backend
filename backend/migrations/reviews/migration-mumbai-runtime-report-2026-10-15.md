# Mumbai runtime validation — 2026-10-15

**Runtime validation only. No migration, schema SQL, grant SQL, signup-trigger DDL or
Alembic stamp was executed.** Both extra columns remain intact. Sydney, GCP, Docker,
Cloud Run, production environment and traffic were not accessed or modified.

Final run: **54 passing result entries, 2 blocked entries, no unexpected final SQL
errors or runtime failures**. Counts describe recorded checks, not a full test suite.
Earlier harness failures and limitations are disclosed below.

## Passed

| Requested check | Actual evidence |
| --- | --- |
| Transaction rollback | All 44 public-table row counts plus auth.users/auth.sessions counts compare equal before/after. Synthetic Auth users/profiles absent after rollback. |
| Schema-only SQL validation | Read-only assertions confirm both proposed compatibility-column definitions already exist: nullable text, no default/domain/collation/identity/generated expression. Complete fresh catalog matches prior audit. No ALTER was tested or run. |
| Security/grant SQL validation | Read-only checks of current effective managed-role permissions match the draft's deny-by-default target and its two existing server grants. Static bundle validation passes. No GRANT/REVOKE was tested or run. |
| Function search_path | All 52 app functions have configuration; all 21 SECURITY DEFINER functions have fixed configuration, with none unset. Signup and promotion functions use search_path=public. All owners postgres; 31 functions are invoker. Config/body catalog unchanged afterward. |
| Signup trigger | Three fresh synthetic auth.users inserts created exactly matching profiles, including trusted customer/owner role provisioning. Existing enabled AFTER INSERT trigger used unchanged. All three identities/profiles rolled back. No Auth HTTP API/signup/session/email action. |
| Customer access | Current authenticated table read denied with expected 42501; own API booking read passed. |
| Owner access | Current authenticated table read denied with expected 42501; own API booking reads/collections passed; foreign-salon support read returned expected 404. Foreign salon fixture has no owner; no second owner identity was provisioned. |
| Service-role booking | SET LOCAL ROLE service_role verified current_user, called real create_booking successfully, then rolled back its savepoint. This is distinct from postgres/API testing. |
| Availability | Real service-role get_available_slots returned 17 remaining slots; API availability initially returned 18. |
| Booking | API creation/replay returned 201 with same ID; duplicate returned 409; PayAtSalon daily-limit and no-show restriction enforced. No direct INSERT into bookings/booking_services from Python. |
| Owner collection | CASH and UPI_DIRECT collection passed; completion before collection rejected; completion after collection passed. Customer collection rejected. |
| Audit | Twelve booking audit rows asserted within transaction; one collection ledger row per payment method. |
| Worker database | Email claim/ack processed one row; notification drain attempted four events; subscription sweep ran within rollback transaction. Providers fake/disabled, no delivery claimed. |
| Effective ACL comparison | Current client app-table rights=0 across tested privileges and roles; client app-function EXECUTE=0. Named service booking/slots EXECUTE=true. Complete raw public relation/column/function ACLs, global/schema defaults and memberships equal before/after. |
| Migration inventory | All 37 source revisions inventoried against selected current final-state requirements; none missing. Full fresh catalog has zero drift from prior head-comparison destination catalog. No revision execution inferred. |

Additional business checks passed: service/staff creation, public listings, quote,
cancellation before cutoff, early/past no-show rules, repeated-no-show restriction,
expired-trial visibility/slots/history, support create/reply and OpenAPI.

## Failed attempts and SQL errors

The initial sandbox attempt failed to download the public CA (ConnectError), before any
database action. Reviewed network execution then reached Mumbai.

First SQL attempt stopped with SQLSTATE **22000**: the new test harness passed a string
to a typed date parameter. Corrected to a Python date/datetime. Its rollback and unchanged
catalog/ACL/row-count checks passed. See first-attempt evidence.

Second SQL attempt passed service-role SQL but stopped at owner-access HTTP 500. The
synthetic example.invalid mailbox was rejected by the API response email validator.
Changed only the fixture to a valid-format example.com address; no mail was sent. Its
rollback checks also passed. This is not recorded as a production-data/API regression.

The final rerun completed with only expected SQLSTATE **42501** twice, for direct
authenticated customer/owner booking reads. Each denial was isolated with a savepoint;
the outer test transaction continued safely. No unexpected final SQL error remains.
No raw database error text, SQL parameter values, user rows or credentials were printed.

## Blocked / untested

1. **Customer and owner RLS row-filter evaluation:** table privileges deny SELECT before
   row policies can run. These two checks are BLOCKED, not passed. Testing positive
   direct-client row filtering requires a separately approved read/grant contract or
   disposable reference environment. No temporary grant, role creation or RLS bypass
   was introduced to manufacture a pass. API business authorization is separate evidence.
2. **Executing/compiling the three DDL/grant migration files:** prohibited by the user.
   Target-state assertions and static boundary checks passed; migration SQL runtime
   semantics and rollback behavior were not validated by executing those files.
3. **Effective clean-head ACL reproduction:** the older clean-head structural comparison
   excluded ACLs. Current effective ACLs and before/after equality are verified, but
   this does not prove exact ACL equality with a fresh repository head/default environment.
4. JWT verification, Google login, real email/push delivery, deployed API/browser and worker
   scheduling were not tested. API actor extraction was explicitly injected for synthetic
   identities so no non-rollbackable Auth sessions were created. Existing Auth/SMTP/TLS/
   staging blockers from the completion report are not resolved by this run.
5. Historical data migrations/backfills cannot be proven executed by schema inspection;
   no production-data reconstruction or destructive erasure/retention job was attempted.

## Rollback and scope proof

Outer SQLAlchemy connection transaction owns all fixtures. Request/worker sessions bind
that same connection using create_savepoint, so repository commits release savepoints
without committing the outer transaction. The outer transaction is rolled back in finally.
Service-role and denied-role probes have nested rollback boundaries. A SQL execution hook
rejects top-level CREATE/ALTER/DROP/GRANT/REVOKE/TRUNCATE/COMMENT before execution.

No migration SQL file is loaded by the runtime runner. No DDL is sent. Auth identities
are synthetic SQL inserts inside the same transaction; no Auth HTTP mutations or external
delivery occurred. Persistent local env/app/Alembic sources were not modified. Existing
Mumbai credentials were used in memory under prior authorization, without output.

Independent project-scoped Mumbai MCP SELECT after the run found: profiles=2,
salons=0, bookings=0, alembic rows=0, six language seeds and the six expected plan codes.
Publication remains blocked_slots, booking_action_requests, bookings. This independently
agrees with the runner's rollback result. Baseline existing test identities were retained.

Client ACL findings refer to application functions. Managed btree_gist functions retain
their existing extension privileges. No managed/default ACL was changed. API base used
was http://mumbai-rollback-runtime, in-process ASGI with real Mumbai Postgres, not deployed.
Client TLS retained the previously disclosed strict-X509 compatibility exception while
verifying CA/hostname; this run does not resolve strict certificate/upstream TLS readiness.

## Extra columns and Alembic

Preserved public.bookings.cancellation_reason_code and cancellation_reason_text. Neither
is defined by current repository migrations. **Yes: adopting them as supported persistent
schema requires a reviewed forward migration documenting both**, with erasure classification
and tests for potentially personal content before release. They must not be dropped to
force 0037 equality. Existing cancellation_reason from 0009/0014 is a different column.

Head remains **0037_customer_processing_charge**; public.alembic_version remains empty.
Known differences remain: two extra columns, promotion function search_path hardening,
restricted app ACLs/default environment. PG18 NOT NULL catalog records and the equivalent
CHECK cast formatting remain version artifacts, not missing migrations. Fresh destination
catalog matches the earlier audit exactly; app/test/migration sources remain unchanged
from the reference used for the clean-head comparison.

Every revision has a review row with selected current objects, source hashes, external
SQL references and supersession notes. This satisfies a revision-by-revision final-state
inventory; it does not substitute for executing an authorized disposable expected-head
build and comparing every final definition/effective ACL. No missing historical migration
was established, and no fabricated execution history was written.

**Exact safe next action:** review/promote the separate schema, security and signup drafts
into future sequential repository revisions after resolving column erasure treatment;
then, only with separate authorization, validate their expected head in disposable PG17
with representative Supabase roles/defaults. Compare fresh Mumbai definitions and effective
ACLs to that approved expected state. Keep existing default ACL differences explicitly
accounted for without introducing global future-function changes. Stop on any mismatch.

Once an actual approved new head matches Mumbai, present the exact unexecuted stamp
command for that head and obtain separate stamp approval. Stamping records a restored
matching baseline; it does not claim the historical upgrades ran. Never insert 37 fake
history rows, replay base-to-head against restored objects, or stamp 0037 now.

**Migration approval still needed:** approval of the three forward revision designs,
column erasure contract and explicit object-level privilege matrix. Runtime-only approval
does not authorize creating/applying a production revision, running any SQL draft or
stamping. No execution action is requested or taken by this report.

## Evidence

- [Final runtime results](migration-mumbai-runtime-results-2026-10-15.json)
- [Fresh sanitized catalog](migration-mumbai-runtime-catalog-2026-10-15.json)
- [Independent post-rollback check](migration-mumbai-runtime-independent-check-2026-10-15.json)
- [All 37 revisions](migration-mumbai-runtime-revision-review-2026-10-15.md)
- [Revision evidence / complete catalog bridge](migration-mumbai-runtime-revision-review-2026-10-15.json)
- [First SQL attempt](migration-mumbai-runtime-first-attempt-2026-10-15.json)
- [Second SQL attempt](migration-mumbai-runtime-second-attempt-2026-10-15.json)
- [Least-privilege reconciliation plan](migration-mumbai-reconciliation-plan-2026-10-15.md)
- [Runtime runner](../../../migration_mumbai_runtime_20261015.py)

Focused Ruff and static bundle validation pass. No unrelated backend/full-suite rerun
was needed: backend code, tests and real revision files were unchanged by this task.
