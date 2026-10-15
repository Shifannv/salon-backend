# Mumbai migration inspection — 2026-10-15

## Continuation results after reconnection request

The following results supersede the earlier snapshot where noted. Destination
`get_project` and `get_project_url` were retried through the available Supabase
connector. Both still returned exactly:
`MCP error -32600: You do not have permission to perform this action`.
Both have `isError=true`, structured `error_code=INVALID_ARGUMENT`.
The local Codex MCP configuration has the correct Mumbai project_ref and requested
features, but this does not prove the connector in this running chat has inherited
that authentication. No alternative token or local DB credentials were used to
bypass this denial. Destination identity/region remain unverified through MCP.

Production diagnosis (read-only): all seven containers are running, none restarting,
zero restart counts and no OOM kills. API and Redis report healthy. The deletion
worker is unhealthy; its last five healthchecks exited 1 with the recognized
missing/stale-heartbeat message. API and deletion-worker DB URLs still target Sydney
transaction pooler port 6543. No environment mismatch to Mumbai was observed.

Filtered deletion-worker logs from the last 30 minutes / 1000-line maximum contain
`InvalidPasswordError` (2 occurrences), `password authentication failed` (4), and
`Account deletion poll failed` (5). These are signature counts, not independent
incident counts. No raw logs, passwords or connection strings were printed.
Fresh asyncpg connections from API and deletion-worker containers failed before
SELECT 1 with `InternalServerError`, SQLSTATE `XX000`. A second API probe recognized
an `authentication` message signature. These probes requested
`default_transaction_read_only=on`; no business queries or writes ran.

Conclusion: the observed DB outage is at the pooler/database authentication
boundary. The worker cannot complete its DB polls, so its heartbeat goes stale.
Stopped containers, Redis outage and Mumbai target mismatch are not observed causes.
No pool-saturation error signature was found in the inspected logs; saturation is
not proven impossible. Invalid/stale credentials versus an upstream pooler Auth
configuration issue remains unresolved. Do not reset Sydney credentials, change
production environment or restart containers without explicit approval. API health
remains 200, DB health 503, Redis health 200. A green process healthcheck does not
establish successful booking API availability.

Prepared `migration-destination-review-2026-10-15.sql` as an UNEXECUTED review draft,
outside the Alembic revision chain. It restores the omitted Auth signup trigger
after checking the restored function's security metadata and rejecting an existing
trigger for manual inspection. It preserves postgres/service_role access, removes
anon/PUBLIC booking-table privileges, and restricts authenticated table access to
SELECT under existing ownership RLS. No trigger or grant changed in any database.
Full function-body comparison, schema CREATE-privilege audit, destination catalog
review and negative tests remain required before approval/execution.

Repository/backup function review: revision 0024 and backup agree that
`handle_new_user` is SECURITY DEFINER, owner postgres in backup, fixed
search_path=public, privileged role assignment only from raw_app_meta_data,
customer default, and client EXECUTE revoked. Signup uses NEW.id, not auth.uid():
Auth-trigger execution can legitimately lack a user JWT subject, so adding a
subject-equality guard would break onboarding. Inspect schema CREATE privileges
before trusting a public search_path. User-editable metadata supplies display
fields only. Baseline trigger definition is AFTER INSERT ON auth.users FOR EACH ROW.

Backup ACL review confirms booking tables already lack anon/authenticated INSERT,
UPDATE and DELETE grants; their excessive privileges are SELECT, REFERENCES,
TRIGGER, TRUNCATE and MAINTAIN. The draft removes all anon access and unnecessary
authenticated privileges, keeping authenticated SELECT for scoped reads/Realtime.
Existing ownership policies and backend authorization must still be tested.

Schema hash was recalculated and still matches the recorded approved hash.
Actual prior verified inventory is 44 tables, 44 RLS tables, 43 policies, 82 explicit
indexes / 148 total including constraint indexes. The approximate 71 indexes / 38
RLS figures in the continuation request are not the verified backup counts.
Trigger/grant hardening will intentionally differ from source schema; those
differences need explicit reconciliation before any stamp.

Validation this continuation:

- `alembic heads`: `0037_customer_processing_charge (head)`.
- Normal full pytest invocation: failed collection with 31 errors because the
  effective local URL selected the psycopg2 dialect but psycopg2 is absent.
- Retried full suite with process-only DATABASE_URL pointing to disposable
  localhost via asyncpg and ENVIRONMENT=test: **878 passed, 62 skipped**, one
  Starlette/AnyIO deprecation warning, 26.08 seconds. No .env file changed.
- Ruff default attempt hit cache-directory access denial; retry with
  `python -m ruff check --no-cache app tests migrations`: **passed**.
- Docker engine available with elevated access, version 29.8.2. Reviewed Dockerfile
  and ignore rules; backend-only local build
  `docker build -t salon-platform-api:mumbai-verification .`: **passed**.
  No image was deployed, and no production container was restarted.
- Skipped opt-in DB/migration tests remain unrun against a disposable database.
  SQL review draft has not been executed or DB-validated. Passing local unit/API
  tests does not establish destination readiness.

Still blocked/not run: destination extension compatibility, pre-restore inventory,
roles/schema restore, Alembic current/stamp, drift verification, destination advisors,
fresh-user RLS tests, Auth/Google/SMTP configuration, Storage tests, staging E2E,
Mumbai latency benchmarks. No source rows were copied or queried in this
continuation. No source Supabase MCP calls were made; production checks used SSH.
No production cutover has occurred.

Files changed this continuation: this report and the new SQL review draft only.
Additional repository files read: deletion worker/health, DB session module,
revision 0024, baseline trigger, backup signup-function/booking ACL definitions,
Dockerfile and .dockerignore. Original application code and backups are unchanged.

## Original inspection snapshot

Status: read-only preflight completed in part; restore blocked. No database writes,
production restarts, deployments, environment edits, commits, payments, or emails ran.
This report is a local, uncommitted artifact. Original backups were not changed.

## Immediate findings

- Source `puuptxogwtylbutosqek`: connected project inspection confirms
  `salon-booking-app`, `ap-southeast-2`, `ACTIVE_HEALTHY`, PostgreSQL 17.6.1.155.
- Destination `wqjlgpnbiapcrlkxumcp`: connected `get_project` returned
  `You do not have permission to perform this action`. Mumbai region, version,
  identity, emptiness, extensions and schema inventory could not be independently
  verified. No write was attempted. Enable connector access to this project first.
- GCP production API and all five workers still point to Sydney, as verified from
  their running container environments. They were not switched to Mumbai.
- VM `/health` and `/health/redis`: HTTP 200. `/health/db`: HTTP 503 on two
  read-only checks. This is an existing Sydney-connected backend connectivity
  failure, not evidence of a Mumbai cutover. Cause is unverified; investigate
  sanitized database connection errors, pooler reachability, credentials and pool
  pressure before any release. No production restart was attempted.
- Account-deletion worker is unhealthy. API and Redis containers report healthy;
  other worker processes are running, which does not prove their work succeeds.

## Environment inventory (values omitted)

| Environment | Database / Auth URL / JWKS | Public key | Privileged key | Payments |
| --- | --- | --- | --- | --- |
| Local backend `backend/.env` | Mumbai | Legacy anon attributes to Mumbai; new publishable configured, project attribution unverified | Legacy service-role attributes to Mumbai; new secret configured, attribution unverified | `PAYMENT_PROVIDER=none`, `CASHFREE_ENABLED=false` |
| Running GCP API and all five workers | Sydney | Legacy anon attributes to Sydney; publishable unset | Legacy service-role attributes to Sydney; new secret unset | `PAYMENT_PROVIDER=none`; `CASHFREE_ENABLED` unset (repository default false; deployed behavior not independently tested) |
| Customer Expo local `.env` | Sydney | `EXPO_PUBLIC_SUPABASE_ANON_KEY`, Sydney | No privileged variable observed in inspected env file | Cashfree false |
| Owner Expo local `.env` | Sydney | `EXPO_PUBLIC_SUPABASE_ANON_KEY`, Sydney | No privileged variable observed in inspected env file | Cashfree false |
| Next.js website local `.env.local` | Sydney | `SUPABASE_ANON_KEY`, Sydney, server configuration | No privileged variable observed in inspected env file | Cashfree false |

Local backend also contains `NEXT_PUBLIC_SUPABASE_URL`,
`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, and `SUPABASE_KEY`; application code does
not consume these. Do not infer new opaque key project ownership from its prefix.
Legacy JWT payload attribution above is inspection only, not signature validation.

Compose uses `${COMPOSE_ENV_FILE:-.env}` for API/workers. Running container labels
identify `/home/hafizmuhammedk9080/salon-backend/backend/.env`. Direct reading of
that file was denied to the SSH account; its current on-disk contents remain
unverified even though container runtime targets were read successfully.
Secret Manager, deployed website configuration, CI secret values, and released
mobile bundles were not inspected. Local files do not prove their deployed values.

## Canonical mapping before edits

| Scope | Intended canonical names | Current implementation / required transition |
| --- | --- | --- |
| Backend + workers | `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_JWKS_URL`, `SUPABASE_JWT_AUDIENCE=authenticated` | Already consumed; configure all for the same verified project |
| Backend public Auth calls | `SUPABASE_PUBLISHABLE_KEY` | Currently only `SUPABASE_ANON_KEY` is consumed |
| Backend privileged Auth calls | `SUPABASE_SECRET_KEY` | Currently only `SUPABASE_SERVICE_ROLE_KEY` is consumed |
| Next.js website | Currently `SUPABASE_URL`, `SUPABASE_ANON_KEY` on server | Actual Next.js website uses server-side Supabase clients and HttpOnly cookies; do not blindly add browser `NEXT_PUBLIC_SUPABASE_*` variables |
| Browser, if direct Supabase access is introduced | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Publishable only; current inspected server implementation does not require these |
| Customer + owner Expo | `EXPO_PUBLIC_SUPABASE_URL`, `EXPO_PUBLIC_SUPABASE_ANON_KEY` | Actual names consumed; keep names until an explicit coordinated rename; verify SDK publishable-key compatibility |
| CI/GCP staging rollout | Same backend variables, private secret storage | Do not alter production until staging passes and cutover is explicitly approved |

New backend key variables are currently ignored by Settings (`extra="ignore").
No Supabase alias conflict check exists. Retain legacy keys until adapters and
configuration are updated and tested. Admin and token Auth adapters currently put
legacy keys in both `apikey` and `Authorization: Bearer`; new opaque keys are not
drop-in JWT replacements. Implement canonical key selection and reject conflicting
alias configuration before removing legacy variables. Do not weaken bearer user
authentication or expose privileged keys to clients.

JWT verifier uses local JWKS signature validation, issuer, audience, and expiry
validation, with a 3600-second cache and refresh for unknown key IDs. It does not
call remote `get_user` for every verification. Destination endpoint reachability,
fresh destination tokens and missing-claim behavior were not tested.

## Backup integrity and object inventory

Both locations contain identical non-empty approved schema/role files:

- `D:/salon-secure-backups/supabase-schema-2026-10-15`
- `D:/salon/salon-backend/supabase-schema-backup`

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `roles.sql` | 370 | `168a95a9c745af5ed4679751f90419ac9dc434240a213b03e32a06d5664c2308` |
| `schema.sql` | 269098 | `2506c4fc8da90d63a7cbfb7a0b727df9e492f5e65e6b09bff4c7136a3d273eef` |

Hashes match secure backup `checksums.txt`. Backup git commit and current checkout
both equal `1b471dca6a70a245d193635d481f1086d10b875a`.
`history_schema.sql` is empty; `history_data.sql` is 41 bytes. Neither is a valid
Alembic-history backup; neither will be restored. Backup files are untracked.

Dollar-quoted function bodies were excluded from the top-level data scan:
zero top-level COPY and zero INSERT INTO statements. Fourteen INSERT statements
inside function definitions are schema logic, not dumped row data. Pattern scans
found no secret-key prefixes, JWT-like tokens, database URLs, or Resend-key patterns;
this is not proof against every possible hardcoded credential.

| Object | Backup | Sydney live | Mumbai |
| --- | ---: | ---: | --- |
| Public tables | 44 | 44 | Not accessible |
| RLS-enabled public tables | 44 | 44 | Not accessible |
| Public policies | 43 | 43 | Not accessible |
| Application functions | 52 CREATE FUNCTION statements | 52 excluding extension-owned functions | Not accessible |
| Noninternal public triggers | 73 | 73 | Not accessible |
| Explicit CREATE INDEX statements | 82 | — | Not accessible |
| Total public indexes | 148 inferred: 82 explicit + 44 PK + 21 unique + 1 exclusion | 148 | Not accessible |
| CREATE TYPE statements | 9 | Not separately counted | Not accessible |
| CREATE SEQUENCE / CREATE VIEW statements | 0 / 0 | Not separately counted | Not accessible |
| ADD CONSTRAINT statements | 178 | Not separately counted | Not accessible |
| GRANT statements | 958 | Not separately counted | Not accessible |
| CREATE EXTENSION statements | 5 | Five matching extensions plus built-in plpgsql | Not accessible |

Required extensions: `btree_gist` in public, `pg_stat_statements` and `pgcrypto` in
extensions, `supabase_vault` in vault, `uuid-ossp` in extensions. Destination
support/versions remain unverified. Extension-owned `gbt_*`, key input/output,
and distance functions are distinct from the 52 application functions. Do not
manually modify extension internals or drop arbitrary ACL statements after errors.

`roles.sql` defines no custom application roles. It changes timeouts for managed
anon/authenticated/authenticator roles and grants a parameter privilege to
supabase_realtime_admin. Omit it from restore; no custom-role restore is needed.

Important completeness gap: source has `t_on_auth_user_created` AFTER INSERT on
`auth.users`, calling `handle_new_user()`. Backup contains the function but omits
the Auth-schema trigger. Recreate the trigger in a separately reviewed destination
step, using the baseline definition. Never restore Auth user rows.

## Alembic

Source read-only SELECT returned exactly one revision:
`0037_customer_processing_charge`. Local command from backend:

```powershell
./.venv/Scripts/python.exe -m alembic heads
```

Output: `0037_customer_processing_charge (head)`. Matching commit and object counts
support backup alignment but do not establish exact semantic schema equality.
Destination `alembic current`, stamping, row verification and schema-drift comparison
have not run. Do not stamp until full schema equality is proven. Do not replay all
migrations on restored objects.

## Reference data and project configuration

- Baseline defines six safe language values: English, Malayalam, Hindi, Tamil,
  Arabic, Kannada (`en`, `ml`, `hi`, `ta`, `ar`, `kn`). Restore these from repository
  values, not source business data.
- Revision 0031 defines six global subscription plans, Growth and Premium for
  1/6/12 months. Reuse reviewed migration-defined values separately after schema
  restoration; do not run the entire historical migration chain to seed them.
- Service categories/subcategories need an approved reference-data decision;
  no source rows were read or copied. All user, salon, booking, payment, support,
  outbox and audit data remain excluded.
- Source Storage buckets: none. Media documentation uses Cloudflare R2; no R2
  operations were performed. No Storage files or metadata were copied.
- Source Realtime publication includes blocked_slots, bookings,
  booking_action_requests. Backup includes these publication additions and an
  ownership statement; review against destination publication state before restore.
- Auth Site URL, redirect allow list, providers, SMTP, templates, JWT/session settings,
  hooks, network/SSL settings, cron, Database Webhooks, Edge Functions and secret
  names remain unverified. Connector offers no Auth-settings update or bucket-create
  operation. Use supported management interfaces manually when approved.
- Google Cloud must ADD
  `https://wqjlgpnbiapcrlkxumcp.supabase.co/auth/v1/callback` while preserving Sydney's
  callback. Preserve discovered `salonapp://auth/callback` and
  `salonowner://auth-callback`; verify website callback routes before configuring.
- No fresh test account, SMTP test address, email, Auth flow, or upload was created.

## Security findings (source inspection only)

Source security advisors reported: 19 informational RLS-enabled tables without
policies; mutable search_path on is_subscription_promotion_active; btree_gist in
public; five anon-callable and seven authenticated-callable SECURITY DEFINER
functions; leaked password protection disabled. Review intentional internal
deny-by-default tables and public discovery helpers individually, without loosening
policies. Advisor output is not a substitute for ownership/negative tests.

Catalog queries confirm anon and authenticated both have TRUNCATE and TRIGGER
privileges on bookings and booking_services. Backup preserves those privileges
(and MAINTAIN grants). TRUNCATE is outside row-level policy protection. Broad
database-role grants are a security concern even when no public HTTP truncate
endpoint exists. Prepare a reviewed destination hardening migration; do not modify
Sydney. No attempted destructive privilege test was made.

Destination advisors, RLS negative tests, privileged function review, UPDATE policy
checks, views, Data API schema settings and bundle secret scans remain outstanding.

## Commands run / not run

Read-only connected operations: source get_project, catalog/extension/Alembic/
Storage/Realtime/Auth-trigger/grant SELECTs, source security advisors; destination
get_project (denied). GCP read-only SSH: hostname, docker ps, parsed docker inspect
with only redacted target/status output, HTTP health probes.

No restore command ran; sanitized restore output: not applicable.
No pytest, opt-in DB tests, Ruff, migration integration tests, Docker build, frontend
tests, Playwright, emulator tests, destination health tests or load tests ran. This
is an inspection-only stop before destination changes. Local docker info failed
because Docker config/engine access was denied in the sandbox; Docker executable
exists. psql was not found on PATH. Do not claim tool absence proves installation
absence elsewhere.

No Mumbai latency results exist. Production health failure prevents a useful
end-to-end success baseline here. No p50/p95/p99, concurrency, or region improvement
claim is made. Backend region recommendation is deferred until Mumbai is verified
and measurements from Windows and us-central1-a are available.

## Manual continuation and approval boundary

Per the request's mandatory rule 11, stop when connected tooling cannot perform
the required operation. Restore is additionally blocked by destination identity,
version/extension inventory, Auth-trigger gap, grant review, and incomplete semantic
schema comparison. Reconnect Supabase with access to destination before proceeding.
Do not bypass denied connector access with local credentials without approval.

After these gates pass, use PostgreSQL client compatible with the verified
destination server, session pooler port 5432, secure interactive password entry or
a protected pgpass file, and a separate reviewed restore copy. Never use 6543 for
restore. No executable-ready reviewed restore copy has been approved yet.
The exact PowerShell invocation for that future copy is:

```powershell
# Set PGHOST to the destination Session pooler hostname copied from Dashboard.
# First verify Dashboard project ref, destination inventory and server version.
if (-not $env:PGHOST) { throw 'Set the verified Mumbai Session pooler hostname first' }
$env:PGSSLMODE = 'verify-full'
psql --host=$env:PGHOST --port=5432 `
  --username=postgres.wqjlgpnbiapcrlkxumcp --dbname=postgres --password `
  --no-psqlrc --single-transaction --variable=ON_ERROR_STOP=1 `
  --file='D:/salon-secure-backups/supabase-schema-2026-10-15/schema.reviewed.sql'
if ($LASTEXITCODE -ne 0) { throw 'Restore failed; stop and review the transaction error' }
```

This command is NOT approved to run now. Configure trusted CA verification for
the session-pooler hostname; do not silently weaken TLS. The reviewed copy must
preserve extension semantics, resolve managed ownership/publication compatibility,
and include only approved changes. Omit original roles.sql. Capture sanitized
output and stop on any unexplained error. Verify all restored objects, recreate
the approved Auth signup trigger, seed repository reference values, then prove
semantic equality before stamping the exact revision.

## Cutover and rollback

Cutover remains unapproved. Required order: restore/config verification; destination
functional/security tests; measure latency; capture secure environment snapshots;
deploy isolated staging; test staging; obtain explicit production approval; update
production backend/workers; coordinate website then mobile release; monitor errors
and latency. Staging must keep Cashfree false and online payments disabled.

Preserve Sydney project and credentials unchanged. If a future approved cutover
fails, restore the saved Sydney environment on API/workers, restart only with
approval, and verify DB health and critical booking APIs. Coordinate client rollback
and investigate destination-only fresh accounts/bookings before routing those users
back: they will not exist in Sydney. Do not copy them back automatically. No rollback
is needed for this inspection because no environment or traffic was changed.

## Exact files inspected / changed

Changed: this report only. No application, migration, environment or backup edits.

Read: attachment Pasted text.txt; AGENTS.md; docs/README.md, project-overview.md,
tech-stack.md, folder-structure.md, database-plan.md, features.md, git-workflow.md,
frontend-integration.md; backend/docs/ARCHITECTURE.md, AUTHORIZATION.md,
BOOKING_FLOW.md, RUNBOOK.md, DOCKER_DEPLOYMENT.md; backend/docker-compose.yml;
backend/app/core/config.py, security.py; infrastructure/supabase/auth_admin.py,
auth_gateway.py; api/v1/routes/health.py; backend/migrations/README.md,
001_supabase_schema.sql, versions/0031_seed_subscription_plans.py; backend/.env
(redacted parsing only), .env.example, .env.gcp.example; both backup sets and secure
checksums.txt/backend-git-commit.txt. Search results additionally identified other
key consumers in Supabase storage and account-deletion worker.

Adjacent client reads/searches (no edits): customer-app/package.json, app.json,
.env, .env.example, src/constants/config.ts, services/supabase/auth.service.ts;
owner package.json, app.json, .env, src/api/supabase-client.ts,
supabase-auth.ts, src/lib/oauth-callback.ts; walking-customer-web/package.json,
.env.local, .env.example, proxy.ts, lib/server/env.ts, lib/server/supabase.ts.
Additional source searches located environment references without changing files.
