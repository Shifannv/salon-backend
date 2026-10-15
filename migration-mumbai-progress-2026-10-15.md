# Mumbai destination migration — 2026-10-15

Sydney recovery is paused. This run did not connect to Sydney, request or inspect its
database password, access the GCP VM, restart containers, change production settings,
deploy anything, or switch traffic. The existing inspection report describes earlier
work; it is not evidence of actions taken in this run.

## Step ledger

| Requested step | Status | Evidence / remaining work |
| --- | --- | --- |
| Supabase MCP access | Complete | This Codex session successfully used `salon-booking-app -mumbai`, connection `link_6ad09c1faa748191bb4dafcde08c5940`, for project lookup, SQL and migrations. No local `.mcp.json` claim or workaround was used. The separate unscoped MCP connection was not called. |
| 1. Destination identity and region | Complete | Project ref `wqjlgpnbiapcrlkxumcp`, URL `https://wqjlgpnbiapcrlkxumcp.supabase.co`, region `ap-south-1`, initially ACTIVE_HEALTHY, PostgreSQL `17.11.0.003`. |
| 2. Backup hashes | Complete | Both supplied locations match each other and secure `checksums.txt`; hashes below. Original backups unchanged. |
| 3. Exclude dumped rows | Complete | SQL-aware scan of 1,650 top-level statements: zero COPY, INSERT INTO, UPDATE, DELETE, MERGE or TRUNCATE statements; no psql metacommands. Function-body INSERT statements are schema logic. |
| 4. Roles/schema restore | Complete with documented restrictions | Compatible roles restore and restricted schema restore succeeded. Original roles grant failed; two schema proposals were rejected before execution. No original broad client grants were applied. |
| 5. Exclude source personal/business rows | Complete | No source rows queried/copied in this run. Before fresh accounts, only six language and six subscription-plan rows existed. Customer, salon, Auth, booking, payment, support, notification and audit source rows were not restored. |
| 6. Signup trigger | Complete | Inspected the existing reviewed draft and restored function body/security. Added only its Auth-trigger section, including preconditions. Verified `t_on_auth_user_created AFTER INSERT ON auth.users`. Actual fresh signup produced profiles. |
| 7. Booking grant review | Complete; client access intentionally restricted | Broad client TRUNCATE/TRIGGER/REFERENCES/MAINTAIN grants rejected and excluded. All public application table/sequence/function access for PUBLIC/anon/authenticated revoked pending precise grant review. Direct client booking table and create_booking calls denied in role tests. Realtime subscriptions/direct app Data API reads are consequently not ready. |
| 8. Reconcile Alembic with head | Compared; reconciliation decision still blocked | Built clean head `0037_customer_processing_charge` on disposable local PostgreSQL. All head tables, indexes, policies, triggers, enums and required column definitions match. Mumbai has two extra booking columns; client ACLs and function search_path also intentionally differ. No destructive reconciliation or new revision was invented. See continuation below. |
| 9. Stamp only after match | Deliberately not done | No stamp, no fabricated revision row, no replay of historical migrations on restored objects. |
| 10. Non-personal seeds | Complete for known repository seeds | Listed in chat before insertion; six languages and six plans inserted from baseline/revision 0031. Categories/subcategories remain empty pending a content decision. |
| 11. Project configuration | Partial | Required extensions and Realtime publication membership verified. User reports Google configuration updated; public Auth settings independently confirm Google and email enabled, signup enabled, email confirmation required. Site URL/redirect allowlist, actual Google login, Supabase Resend SMTP and delivery are unverified. Local Resend variables do not prove Supabase SMTP configuration. Storage API returns zero buckets; repository media uses R2. No arbitrary bucket/policy or R2 change made. |
| 12. Fresh accounts | Complete with fixture caveat | Two controlled Gmail aliases created through Mumbai Auth admin API, confirmed for password tests. Both received profiles. Owner profile initially defaulted to customer despite trusted Auth owner metadata; only that fresh test profile was provisioned to owner using guarded SQL and actor context. Owner-access API behavior remains untested. |
| 13. API/RLS/Auth/Storage/booking/Playwright | API/Auth/booking/RLS tests passed; remaining integrations blocked | Pooler unblocked real API/database tests using process-only configuration. Actual booking creation, replay, duplicate rejection, party-scoped reads and RLS ownership/negative reads passed with rolled-back synthetic fixtures. Auth login/JWKS/refresh/logout passed. Storage bucket-list API passed; uploads/policies untested. 878 pytest tests passed, 62 opt-in tests skipped; Ruff passed. No staging frontend URL supplied, so Playwright remains unrun. |
| 14. Windows latency | Auth HTTPS and DB round trips measured | Auth JWKS median 168.407 ms across 10 HTTP 200 responses. Verified-TLS Session pooler SELECT 1 median 83.746 ms across 10 samples; setup 334.623 ms. API timings recorded separately, with cold/session/auth overhead; no production/load/Sydney-comparison claim. |
| 15. Stop before production changes | Respected | No deployment, production environment change, container restart, GCP access or traffic switch. |

## Backup and restore details

| Original file | Bytes | SHA-256 |
| --- | ---: | --- |
| roles.sql | 370 | `168a95a9c745af5ed4679751f90419ac9dc434240a213b03e32a06d5664c2308` |
| schema.sql | 269098 | `2506c4fc8da90d63a7cbfb7a0b727df9e492f5e65e6b09bff4c7136a3d273eef` |

`roles.sql` initially failed with permission denied for parameter `log_min_messages`.
Catalog inspection verified the destination's supabase_realtime_admin already has SET
and the managed postgres role lacks grant option. The compatible copy omits only that
already-satisfied grant and applies the role settings. Verified resulting timeouts:
anon 3s, authenticated 8s, authenticator 8s; existing authenticator settings preserved.

Automatic approval review rejected the original schema because of dangerous client
table grants/defaults. A second proposal removed dangerous table privileges but kept
client DML, function and sequence grants; review rejected that too. Neither executed.
The successful restricted copy removes 490 client GRANT/default-GRANT statements,
then explicitly revokes public application privileges/defaults. Privileged backend
postgres/service_role access remains. Extension-owned routines retain managed ACLs:
188 btree_gist functions per client role remained executable; zero of the 52 application
functions were client-executable. Do not claim all extension ACLs were changed.

Verified restored objects: 44 public tables, all 44 RLS enabled; 43 policies; 73 public
triggers; 148 indexes; 52 application functions, each exact prosrc body matching backup.
These counts/body matches do not prove full schema/head equality. Required extensions:
btree_gist 1.7, pg_stat_statements 1.11, pgcrypto 1.3, supabase_vault 0.3.1, uuid-ossp 1.1.
Realtime publication contains public.blocked_slots, public.booking_action_requests and
public.bookings; client grants still block subscription use.

Security advisors initially reported 19 informational RLS-enabled tables without policies,
one mutable search_path warning and btree_gist in public. The search_path was subsequently
reconciled to the exact configuration required by repository revision 0024 and verified
as `search_path=public`. No broad policy was added
to silence deny-by-default internal-table findings. See official remediation:
[no-policy tables](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy),
[search_path](https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable),
[extension placement](https://supabase.com/docs/guides/database/database-linter?lint=0014_extension_in_public).

## Seeds and test accounts

Languages: en English, ml Malayalam, hi Hindi, ta Tamil, ar Arabic, kn Kannada.
Plans: growth_1m INR349, growth_6m INR1499, growth_12m INR1999;
premium_1m INR599, premium_6m INR2499, premium_12m INR3499.
Intervals/features match repository revision 0031; no purchase/subscription rows copied.

Fresh customer: `7alonbooking+mumbai-customer-20261015@gmail.com`,
ID `81163183-2757-464e-8f92-b7f5dafe61fa`.
Fresh owner: `7alonbooking+mumbai-owner-20261015@gmail.com`,
ID `cd974685-f3ba-43f6-b00e-cd103935fc28`.
Generated passwords and tokens stayed in process memory and were discarded. Both
accounts were logged out. Use a verified password-reset flow later; no passwords were
written to reports, environment files or scripts. Admin confirmation means these tests
did not verify signup confirmation emails/SMTP. The initial owner profile mismatch is
recorded rather than hidden by fixture provisioning.

An initial account-test proposal containing a super_admin metadata spoof test was
rejected by automatic approval review before execution. The successful account requests
contained only ordinary customer/owner roles; no super-admin account was created.

## Local configuration and remaining inputs

After the user confirmed replacing local credentials, a redacted local inspection verified
SUPABASE_URL, SUPABASE_JWKS_URL and database host point to Mumbai. Legacy anon/service-role
JWT payloads identify Mumbai (payload attribution alone is not signature validation);
modern publishable/secret keys actually passed the appropriate remote requests.
Local ENVIRONMENT remains local. No local environment file was edited. This does not
verify any deployed configuration or any other repository's settings.

Initial blockers before continuation (the pooler was later supplied): a verified Mumbai
Session pooler hostname (port 5432) because the configured
direct db hostname fails DNS on this Windows host; confirmed staging Site URL/redirects;
dashboard evidence/configuration of Google OAuth and Resend SMTP; a precise reviewed
client-grant allowlist; a disposable clean-head schema for full comparison; and an
isolated staging frontend/API target for complete functional and Playwright testing.
Never request Sydney credentials or modify shared production OAuth configuration.

The initial restore phase did not run pytest/Ruff; the pooler continuation subsequently
ran the backend suite (878 passed, 62 skipped, one dependency deprecation warning) and
Ruff over app/tests/migrations plus the three verification scripts (passed). Tests used
isolated process settings, never a production DSN. No Docker or VM operations were run.

## Local artifacts

- `migration-mumbai-roles-reviewed-2026-10-15.sql`: successful compatible roles SQL.
- `migration-mumbai-schema-restricted-2026-10-15.sql`: successful restricted schema SQL.
- `migration-destination-review-2026-10-15.sql`: pre-existing draft; only its signup section applied.
- `migration-mumbai-reference-seeds-2026-10-15.sql`: executed safe repository seed statements.
- `migration-mumbai-evidence-2026-10-15.json`: post-restore/pre-trigger catalog snapshot,
  exact function-body comparisons, Windows latency samples and Auth test results.
- `migration-mumbai-schema-reviewed-2026-10-15.sql` and
  `migration-mumbai-grant-review-2026-10-15.json`: rejected intermediate proposal, NOT applied.

All new artifacts remain uncommitted. Original backups and pre-existing report/draft
were not modified. Successful MCP migration names: mumbai_roles_compatible_restore_20261015,
mumbai_schema_only_restricted_restore_20261015, mumbai_reviewed_auth_signup_trigger_20261015,
mumbai_reconcile_0024_function_search_path_20261015.

## Continuation after the user supplied the Session pooler

User supplied `aws-0-ap-south-1.pooler.supabase.com:5432`, database postgres,
username postgres.wqjlgpnbiapcrlkxumcp. The existing local Mumbai password was used
in memory without printing it, modifying it or writing a replacement connection string.
The original direct hostname still fails on this Windows host; no environment file
was changed. Normal local startup does not automatically receive the test overrides.

The pooler initially failed CA validation. After loading the public Supabase CA,
Python 3.14.4 rejected its intermediate with `CA cert does not include key usage extension`.
The test-only SSL context disabled VERIFY_X509_STRICT while retaining CERT_REQUIRED
and hostname verification. This is an explicit compatibility exception, not a validated
default-Python-3.14 configuration. No global trust store, server SSL setting or product
configuration was changed. A guessed public download route returned HTTP error; the
working CA came over HTTPS from
`https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt`.
PEM file SHA256: `700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7`.
See [Python SSL defaults](https://docs.python.org/3/library/ssl.html#ssl.create_default_context)
and [Supabase SSL verification guidance](https://supabase.com/docs/guides/platform/ssl-enforcement).

Successful DB probe: postgres database/current_user postgres, two profiles, zero bookings,
empty Alembic table. Connection setup 334.623 ms. Ten warm SELECT 1 round trips in ms:
84.318, 86.745, 83.462, 82.703, 81.095, 84.030, 80.754, 81.513, 92.105, 84.745.
Median 83.746 ms; range 80.754–92.105 ms. This includes the Windows-to-pooler round trip.

The in-process ASGI checks used the real FastAPI app, real Mumbai Auth and real Mumbai
Postgres. Health/db/readiness, salon listing, both accounts' auth/me and customer booking
listing returned 200. Invalid tokens returned 401. Owner booking listing before fixture
setup returned the expected 403 because there was no active approved salon workspace.
Test sessions were created using admin-generated magic links without sending email,
kept in memory and globally logged out for the two test accounts after the checks.

Inside a rollback-only outer DB transaction, fresh synthetic salon/category/subcategory/
staff/service fixtures exercised availability (18 slots), booking creation (201),
idempotent replay (201 and same ID), duplicate booking rejection (409), and customer/owner
booking reads (200, expected booking present). All bookings were created by create_booking
through the API; no direct booking/booking_service inserts were made. External push
delivery was stubbed at its gateway boundary; SQL guards/audits were real and rolled back.

RLS tests granted only SELECT on profiles/bookings/booking_services/staff/salons and
EXECUTE on is_super_admin/owns_salon inside that same uncommitted transaction. Staff and
salon reads are dependencies of existing policies. Customer and owner each saw one own
profile and their one booking; an unrelated UUID saw zero profiles/bookings. No policy
was disabled or changed. The test grants rolled back; persistent client booking SELECT
and TRUNCATE remain false. The persistent client allowlist is still outstanding.

Initial harness failures were a fixture UUID/text parameter mismatch and a missing
staff/salon SELECT dependency during RLS tests. Both were corrected in the harness;
the final live tests passed. Independent MCP verification after rollback confirmed zero
salons, bookings, booking_services, booking audits, notifications, email events and test
categories. Only the two Auth/profile test accounts and approved non-personal seeds remain.

### Clean-head comparison and stamping gate

PostgreSQL 18.6 was already installed locally. Disposable localhost-only instances were
used to build the repository head with minimal Supabase Auth prerequisites, using the
same consolidated-baseline experience-column adjustment as the existing integration
fixture and preserving revision 0034 enum autocommit boundaries. Initial Windows pipe
capture, merged SQL/log output and enum-transaction harness failures were corrected.
All four local instances were stopped; their exact verified temporary directories were
removed. No Docker, existing PostgreSQL service or production database was restarted.

Comparison result is saved in `migration-mumbai-head-comparison-2026-10-15.json`:

- No missing/extra/changed tables, enums, indexes, policies or triggers.
- All required column definitions match; Mumbai additionally has
  `bookings.cancellation_reason_code` and `bookings.cancellation_reason_text` from the backup.
- All 52 function bodies match after whitespace normalization. One function configuration
  differs: Mumbai has search_path=public on is_subscription_promotion_active.
- Correction to the earlier provisional interpretation: the clean head shows revision
  0030 recreates this function after 0024 and clears its search_path. The Mumbai change is
  intentional security hardening beyond head, not restoration of missing head state.
- The local PG18 catalog lists 317 NOT NULL constraints that PG17 stores differently;
  all column not_null flags match. One plan-interval CHECK has a deparser-only cast/array
  representation difference with the same four accepted intervals. See the
  [PostgreSQL 18 catalog change](https://www.postgresql.org/docs/18/release-18.html).
- ACLs were intentionally excluded from structural equality: Mumbai remains more
  restrictive. Extensions/managed schemas have separate inventories and are not proven
  equivalent by comparing the public application catalog alone.

No columns were dropped, no backup was rewritten, no new migration revision was invented,
and Alembic remains unstamped. Decide how to reconcile the two extra columns and document
the accepted security deviations before considering a stamp.

Remaining: persistent client-grant allowlist, staging Site URL/redirect allowlist and actual
Google login, Supabase Resend SMTP/delivery, any explicitly required Storage bucket/policy
and upload tests (the backend uses R2), Realtime subscriber testing, staging frontend URL
and Playwright flows. Python Playwright is not installed in this backend venv; this does
not prove it is unavailable elsewhere. No browser test was claimed. Production remains
untouched and cutover remains unapproved.
