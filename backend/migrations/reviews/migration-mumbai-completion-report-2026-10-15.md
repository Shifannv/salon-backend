# Mumbai staging readiness audit — 2026-10-15

Reconciliation proposal update: the [revised least-privilege plan](migration-mumbai-reconciliation-plan-2026-10-15.md)
supersedes this report's earlier combined draft/global-default approval item. New drafts
do not change any future-object defaults. Audit results below remain historical evidence.

Mumbai is **not yet fully ready**. API/database business tests passed, but exact
schema/head reconciliation, Auth delivery/callbacks, TLS review and deployed staging
verification remain outstanding. No Alembic migration or stamp ran in this completion
audit. The reconciliation SQL is an unexecuted review draft.

Scope: `wqjlgpnbiapcrlkxumcp`, `ap-south-1`, independently verified through the Mumbai
connector. Sydney, its credentials, GCP VM, Docker, production environment, deployment,
traffic routing and Cloud Run were not accessed or changed. No production data was used.
Local app/environment files were not changed. Test helpers use process-only settings.

## Phase ledger

| Phase | Status | Evidence / remaining gate |
| --- | --- | --- |
| 1. Connection | Partial | Project-scoped pooler works; identity and read-only transactions verified. Strict certificate compatibility and upstream TLS need review. |
| 2. Inventory/comparison | Completed with differences | Fresh catalog and backup hashes checked; prior clean-head comparison reused against unchanged migration sources. Exact equality does not pass. |
| 3. Alembic reconciliation | Blocked | Head `0037_customer_processing_charge`; destination version table empty. No missing migration established; known extras/hardening prevent safe stamp. |
| 4. Permissions/RLS | Partial | Current clients denied app-table/function access; API ownership/negative tests passed. Earlier rollback-only scoped policy tests passed; current completion run introduced no grants. Realtime client contract remains unresolved. |
| 5. Business tests | Passed within stated scope | 54 recorded checks/results; real Mumbai DB/Auth with synthetic fixtures and outer rollback. External providers disabled/faked. |
| 6. Auth/providers | Partial / failures | Tokens, refresh/logout and Google authorization routing pass. Recovery 429, sender unverified, web redirect absent from supplied list; real delivery/Google login unverified. |
| 7. Storage/Realtime | Decision recorded / partial | User chose existing R2; Supabase Storage intentionally unused. Publication membership verified. R2 end-to-end and live subscription delivery not tested. |
| 8. Backend contract | Passed locally; deployed blocked | Real Mumbai through in-process FastAPI. No verified Mumbai deployed API or complete salon QR URL. |
| 9. Report | Completed | This report, sanitized JSON artifacts, reconciliation plan and unexecuted SQL draft. |

## Connection and latency

Sanitized pooler: host `aws-0-ap-south-1.pooler.supabase.com`, port `5432`, database
`postgres`, username `postgres.wqjlgpnbiapcrlkxumcp`. The shared pooler hostname alone
does not identify a project; project-scoped username plus independent management lookup
provide the scope verification. Current database/user: `postgres`/`postgres`; PostgreSQL
17.11. Each read-only transaction asserted the read-only flag.

Configured local database host remains `db.wqjlgpnbiapcrlkxumcp.supabase.co`; Windows
DNS resolution failed. Tests override the host/user only in process to use the pooler.
The persistent local configuration has not been repaired or proven deployable.

Client-to-pooler TLS requires CA verification and hostname verification. Python's
default strict X509 validation failed because the intermediate lacks Key Usage.
The test-only context loads Supabase's public CA and disables VERIFY_X509_STRICT,
while retaining CERT_REQUIRED/check_hostname. This is not a strict-default TLS pass.
`pg_stat_ssl` reports `ssl=false` for the database backend connection, which is the
pooler-to-database hop, not evidence that client-to-pooler encryption was absent.
No TLS configuration was changed. Review both hops with the platform owner.
References: [Python SSL](https://docs.python.org/3/library/ssl.html#ssl.create_default_context),
[PostgreSQL pg_stat_ssl](https://www.postgresql.org/docs/17/monitoring-stats.html#MONITORING-PG-STAT-SSL-VIEW),
[Supabase SSL enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement).

Windows measurements, 10 samples each; nearest-rank p95 is the maximum for n=10.
These are small-sample observations, not load tests or deployed API latency.

| Operation | Median ms | p95 ms |
| --- | ---: | ---: |
| New pooler connection | 280.647 | 361.656 |
| SELECT 1 | 88.491 | 106.790 |
| Simple languages count | 91.036 | 100.963 |
| Read-only transaction | 274.113 | 284.336 |
| FastAPI /health/db | 138.529 | 190.088 |
| FastAPI /v1/salons | 233.808 | 474.206 |

## Schema inventory and reconciliation

Present: 44 public tables, all RLS enabled; 540 columns; 9 enums; 148 indexes;
290 constraints (44 primary keys, 112 foreign keys, 21 unique, 112 CHECK, 1 exclusion);
52 application functions; 74 noninternal triggers including Auth signup; 43 public
policies; no public sequences or views. Catalog artifacts include names/definitions,
roles, memberships, schema/table/function grants and global/schema default privileges.

Extensions: btree_gist 1.7, pg_stat_statements 1.11, pgcrypto 1.3, uuid-ossp 1.1,
supabase_vault 0.3.1, plpgsql 1.0. Realtime publication includes blocked_slots,
booking_action_requests and bookings with FULL replica identity.

| Category | Finding |
| --- | --- |
| Present | Required tables, columns, indexes, enums, policies, triggers and function bodies matched the prior clean-head structural comparison. Fresh table names and all 52 function-body hashes match the verified backup. |
| Missing | No missing repository migration established. Alembic history is absent. Supabase Storage objects are intentionally absent by user decision. |
| Extra | Nullable text bookings.cancellation_reason_code and cancellation_reason_text, both without defaults; unused by current app/migration source. |
| Mismatched | Mumbai fixes is_subscription_promotion_active search_path; clean head recreates it in 0030 without that setting. Mumbai client grants/defaults are intentionally stricter. |
| Comparison artifacts | PG18 NOT NULL catalog entries versus PG17 and equivalent array-cast CHECK deparsing are version differences, not missing objects. |
| Dangerous if enabled | blocked_slots SELECT policy uses USING(true); granting broad SELECT could expose blocked-slot fields. Keep denied pending policy/contract review. |
| Requires review/approval | Forward-only adoption of legacy columns, erasure classification, hardened ACL/default design including global future-function scope, exact expected-head comparison; stamping remains separate. |

Lineage: schema SQL restore plus reviewed supplements, not execution of all 37 Alembic
revisions. Supabase records four restore/hardening migrations; these are not Alembic
history. `public.alembic_version` has zero rows. Source migrations/app/tests are unchanged
from the reference used for the earlier clean-head comparison. No destructive rebuild
or repeated historical migration was run in this audit.

**Stamp is unsafe. No stamp command is proposed while known differences remain.**
The plan preserves both compatibility columns and proposes a future forward revision
after 0037. No new revision was added; head remains 0037. Migration review found the
proposal safe to circulate unexecuted, subject to schema/ACL tests and explicit decisions.

Backup SHA256, matching both verified copies:

- roles.sql: `168a95a9c745af5ed4679751f90419ac9dc434240a213b03e32a06d5664c2308`
- schema.sql: `2506c4fc8da90d63a7cbfb7a0b727df9e492f5e65e6b09bff4c7136a3d273eef`

SQL-aware scanning previously verified 1,650 top-level statements with no dumped
COPY/INSERT/UPDATE/DELETE/MERGE/TRUNCATE data statements. Function-body DML is logic.
Earlier restricted restore removed broad client privileges after the original proposal
was rejected; original role restore also needed a compatible version for managed-role
permissions. Those failures and successful replacements remain in the progress report.
No customer/salon/Auth/booking/payment/support/notification/audit source rows were copied.
Only six language rows and six subscription-plan rows were copied from reviewed repo
seeds, plus two freshly created controlled test identities/profiles.

## Permissions, ownership and business tests

Current application-table grants to PUBLIC/anon/authenticated: zero. Client execution
of application functions: zero. Existing extension function permissions are retained:
188 btree_gist functions per client role, 376 effective role/function pairs. This does
not mean all functions in public are inaccessible. No client grants changed in this
completion audit. No explicit public column ACLs were found. service_role retains
table DML and application function execution; its key is used only by test/backend code.

Earlier rollback-only policy probes established own profile/booking visibility and
unrelated-row isolation under temporary scoped test grants. They do not authorize
actual grants. Current API negative tests reject customer collection, owner access to
another salon's support ticket, and invalid JWTs. The foreign salon fixture has no
owner; a distinct second-owner account was not created. Full live Realtime/client
read access is not proven while its grants are deliberately disabled.

Business checks passed: owner salon onboarding, service/staff creation, synthetic
availability, public salon/service/staff listings, DB slots, quote, booking creation,
same-key replay, duplicate rejection, PayAtSalon daily limit, party reads, CASH and
UPI_DIRECT collection, completion guard and completion after collection, cancellation
before cutoff, early no-show rejection, past no-show processing, repeated-no-show
restriction, expired-trial visibility/slots/history, support flow and audits.
Early no-show returns the existing 422 validation contract; this is an expected rejection.
Bookings were created through FastAPI and the DB booking function, never direct inserts.
Approval state/availability/timing fixtures were provisioned within the rollback only.

Worker database checks: email claim/ack processed one row using fake delivery;
notification drain attempted four events with fake push; subscription sweep executed.
Twelve audit rows and one collection ledger row per payment method were asserted.
All were rolled back. Actual worker deployment/scheduling, email/push delivery, online
payments, paid subscription provider lifecycle and destructive retention/erasure jobs
were skipped. These checks do not certify production worker readiness.

Final independent Mumbai MCP counts: zero salons/bookings and zero Storage objects;
two controlled profiles remain. Earlier post-rollback counts also showed zero services,
staff, payments, support/messages, notifications/outbox/email events and audit rows.
The original fresh Auth accounts remain; no production identities were imported.

Advisors: 19 informational RLS-enabled/no-policy findings (deny-by-default tables),
public btree_gist extension warning and leaked-password-protection-disabled warning.
References: [RLS no policy](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy),
[public extension](https://supabase.com/docs/guides/database/database-linter?lint=0014_extension_in_public),
[password protection](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

## Auth, Storage and staging contract

Two fresh customer/owner identities and signup-created profiles were verified earlier;
owner role provisioning was an explicit controlled fixture step. Password login passed
earlier. Current magic-link generation/verification and refresh returned 200 for each;
global logout returned 204. These generated-link tests do not send confirmation emails.
JWT validation passed; invalid tokens returned 401. Public email-confirmation signup,
Google interactive login and mailbox recovery completion remain unverified.

Google/email providers enabled; phone disabled. Google authorization returned 302 to
Google with the callback targeting Mumbai. One password-recovery attempt returned
429 over_email_send_rate_limit; no repeated delivery attempts were made.
Resend domain-list request returned 401; this establishes unauthorized lookup, not a
definitive diagnosis of the SMTP credential. Tools cannot inspect/update SMTP settings.

User-confirmed settings: Site URL http://localhost:8081/; redirect list
salonowner://auth-callback, http://localhost:3000/auth/callback,
http://127.0.0.1:3000/auth/callback and http://localhost:*/auth/callback.
The supplied list contains no Vercel callback. Sender name is Salon Booking, sender
uses gmail.com, domain verification NOT VERIFIED. No secret settings were requested.
A mailbox address is not a verifiable sending-domain configuration. Resend requires
a domain the sender controls, excluding shared/public domains; choose and verify one
before testing Resend SMTP with a sender on it.
[Resend verified domains](https://resend.com/docs/dashboard/domains/introduction).

User explicitly chose to keep existing Cloudflare R2. Supabase Storage remains unused:
zero buckets, objects and policies; bucket/privacy/upload/read/delete/URL tests are
not applicable to this destination. No buckets/policies were created and no R2 settings
were changed. Existing R2 staging upload/read/delete/object URL tests remain unverified.
Realtime publication presence passes; live client event delivery/isolation was not run.

API base used: `http://mumbai-local-test`, an in-process HTTPX ASGI target using real
Mumbai Auth/Postgres, not a deployed endpoint. Health, database readiness, OpenAPI,
auth, discovery, slots, quote, booking, collection and support passed. Tests used Mumbai
Supabase URL/JWKS and accepted Mumbai public/server keys. Database target was the
process-only Mumbai pooler override. No executed test path targeted Sydney; deployed
GCP/frontend configuration was not inspected and cannot be certified from these tests.

Earlier Playwright: Vercel homepage 200 and requires a salon QR link; /s returned 404. Requests that
might reach an unverified backend were blocked. Root URL alone is not a full Mumbai
salon QR link. A verified Mumbai staging API base and complete QR URL are still needed
for end-to-end browser booking tests. No deployment or frontend changes were made.

Verification: focused Ruff checks passed; earlier same-session backend suite recorded
878 passed, 62 skipped and one dependency warning. App/tests/migrations remain unchanged
from that run. Audit/test helpers and report files are local working-tree changes;
README changes belong to the user and were left untouched. No commit was created.

## Required actions and next approval

1. Review the linked reconciliation plan and unexecuted draft. Resolve both legacy
   column erasure classifications and explicit global future-function-default scope
   before a real revision. Prove effective ACLs, inheritance, extension compatibility
   and exact schema equality against the reviewed expected head.
2. Resolve client strict-certificate conformance and pooler upstream TLS with supported
   Mumbai platform settings; no production or Sydney changes are authorized.
3. Configure the intended staging Site URL and exact frontend callback after verifying
   the deployed application's route. Verify an owned Resend sending domain/sender and
   Mumbai SMTP configuration; then test real confirmation/recovery mail and Google login.
4. Verify R2 staging media, live Realtime permissions if required, worker runtime/jobs,
   and a Mumbai-only deployed API/browser flow. No deployment is authorized by this audit.

**Exact next approval:** approve the forward-only compatibility/hardening design,
including its documented global future-function default scope, for preparation of a
reviewable repository revision. This is not approval to execute SQL or stamp. The
repository Alembic skill requires migration commands to be handed to the user; no
remote migration will be auto-run. Separate stamp approval is only meaningful after
the expected schema/head matches. Stop before production environment/deployment/traffic.
The applicable [Alembic skill](../../../.claude/skills/alembic-migration/SKILL.md) states:
"Never auto-run. Never run against anything but a local/throwaway DB. Show the command
and let the user run it." This constrains future migration execution; the current
design review gate also follows the user's explicit requirement to review first.

## Evidence

- [Reconciliation plan](migration-mumbai-reconciliation-plan-2026-10-15.md)
- [Unexecuted SQL draft](migration-mumbai-reconciliation-DRAFT-2026-10-15.sql)
- [Fresh catalog and timings](migration-mumbai-completion-audit-2026-10-15.json)
- [Migration lineage](migration-mumbai-completion-lineage-2026-10-15.json)
- [54 business/API results](migration-mumbai-completion-business-2026-10-15.json)
- [Auth results](migration-mumbai-completion-auth-2026-10-15.json)
- [Provider results](migration-mumbai-completion-provider-2026-10-15.json)
- [Process configuration checks](migration-mumbai-completion-config-2026-10-15.json)
- [Final read-only preflight](migration-mumbai-completion-final-preflight-2026-10-15.json)
- [Earlier full restore ledger](migration-mumbai-progress-2026-10-15.md)
