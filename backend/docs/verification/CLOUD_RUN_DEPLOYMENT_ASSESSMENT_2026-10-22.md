# Cloud Run deployment, VM retirement and billing assessment

Assessment: 22 October 2026, approximately 16:18–16:27 IST.
Project: `saloon-505509`. Local source: `ee87dde` on `shifan`.
Initial mode: live read-only infrastructure inspection and low-volume HTTP GET smoke
checks. Section 8 records the subsequent authorized local integration tests.

**Latest follow-up:** section 10 records the connected-phone Google login recovery,
website Playwright results and the approved, deployed gallery API fix. Sections 11–12
track the description removal and two-slide changes. **Section 13 records the separately
approved zero-traffic candidate deployment on 23 October; normal production traffic
still uses the gallery hotfix.** Section 14 adds the app-completion and cost assessment;
**section 15 records the subsequently approved cleanup and current minimum 0 / maximum 1 setting.** The initial read-only scope below describes the first
assessment, not every subsequent activity.

## Decision

**The production API is already running on Cloud Run and its basic health checks pass.**
Moving the HTTP API off the old VM is not an outstanding first step. Retiring the VM,
confirming data continuity, completing background processing and releasing current
source still require work. **Do not stop/delete the VM or copy a database based on
this report alone.** This is a partial deployment assessment, not full business-flow
acceptance or a zero-data-loss guarantee.

During the initial assessment, no deployment, traffic/DNS change, billing change, database write/migration, provider
activation, VM restart/stop, guest SSH, secret-payload access or resource creation was
performed. The GET tests can cause normal service activity, cache reads/fills and
autoscaling charges. Only local assessment artifacts and this report were written.

## 1. Current verified routing and resources

```text
apiv1.mudassirmhd.in
  -> 34.117.51.175 (external managed HTTPS load balancer)
  -> salon-production-api-proxy
  -> salon-production-api-urlmap
  -> salon-production-api-backend
  -> salon-production-api-neg (serverless, asia-south1)
  -> salon-api-production (Cloud Run)
  -> salon-api-production-00004-nx7 (100% normal traffic)

Old VM, separately still running:
instance-20261009-141410, us-central1-a, 35.254.254.227
```

DNS, forwarding-rule, proxy, URL-map, backend and serverless NEG metadata establish
the routing chain. This supersedes the 16–17 October report's VM-based DNS observation.

| Resource | Live result |
| --- | --- |
| Production domain | HTTPS works through the load balancer |
| Production Cloud Run service | Ready; `asia-south1` |
| Traffic-serving revision | `salon-api-production-00004-nx7`, created 19 October |
| Production image | `salon-production/api@sha256:e3893bd089e542bd15bd90147c96e61443580928a60816c65b05a3df9520b9ea` in the project's Mumbai registry |
| Production scaling | Service minimum 1, maximum 3; serving revision maximum 3 |
| Serving revision resources | 1 vCPU, 512 MiB, gen2, concurrency 8 |
| Serving revision startup probe | HTTP `/health`, period 5 s, timeout 3 s, threshold 24 |
| Serving revision DB pool overrides | Pool size 3 + overflow 2 per process |
| Production configuration source | Secret Manager volume `salon-production-env`, version 1; payload not read |
| Candidate revision | `salon-api-production-optiona-10201220`, tagged `candidate2`, no normal traffic |
| Other candidate | `salon-api-production-tcp-gen1-10201107`, tagged `candidate`, no normal traffic |
| Staging service | `salon-api-mumbai-staging`, Ready, separate IAM-protected service |
| Old VM | RUNNING, e2-medium, 10 GiB attached boot disk; guest workloads not inspected |
| Notification worker pool | `salon-prod-notifications`, Ready, manually configured 1 instance |
| Worker module observed | `app.infrastructure.push.outbox_worker` |
| Cloud Run jobs in Mumbai | `salon-production-db-check`; its existence is not an outbox-draining schedule |
| Cloud Scheduler jobs in Mumbai | List returned empty |
| Project billing | Enabled; one accessible open billing account returned |

**Latest created revision is not the traffic-serving revision.** The service template
shows gen1/concurrency 20/pool 3+1 for a candidate, while live normal traffic still uses
gen2/concurrency 8/pool 3+2. Candidate settings must not be reported as already released.

The staging template explicitly sets `DB_SSL_STRICT=false`. Earlier strict-TLS staging
evidence therefore does not establish current staging TLS policy. Review this before
using staging configuration as a production template. Production's corresponding
secret-loaded value was not accessed and is unverified here.

## 2. Actual HTTP test results

23 initial GET requests: 22 returned 200, and the one anonymous staging request returned
the expected 403. Four additional production GET checks returned their expected codes.
Tokens stayed in process memory; no business response rows were exported.

| Target/check | HTTP/result | Observation |
| --- | --- | --- |
| Production domain `/health` | 200, status ok | About 296 ms |
| Production domain `/health/db` | 200, database reachable | About 265 ms |
| Production domain `/health/redis` | 200, Redis reachable | About 451 ms |
| Production domain `/health/ready` | 200, status ok | About 279 ms |
| Production `/v1/payments/config` | 200, enabled false | Online payment remains disabled |
| Production `/v1/subscriptions/config` | 200, enabled false | Subscription billing disabled; native purchase false |
| Production `/openapi.json` | 200, 138 operations | Source/deployed gap below |
| Direct production run.app | Health/DB/Redis/readiness/config/OpenAPI all 200 | Direct public health also 200 |
| Staging without IAM token | 403 | Expected platform access denial |
| Staging with Cloud IAM token | Health/DB/Redis/readiness/config/OpenAPI all 200 | First observed health about 6.7 s; one observation, not a proven cold-start percentile |
| Production `/v1/auth/me`, anonymous | 401 | Correct no-session boundary |
| Production `/v1/salons/me`, anonymous | 401 | Correct no-session boundary |
| Production `/v1/admin/salons`, anonymous | 401 | Correct no-session boundary |
| Production `/v1/salons?limit=1` | 200 | Public discovery accepts the request; business completeness not tested |

These are smoke checks, not load measurements or an uptime guarantee. Database health
proves reachability, not correct project identity, schema revision or row completeness.
Redis health does not prove cache isolation or notification delivery. IAM tokens used
to reach staging are not customer/owner Supabase JWTs.

### API release differences

Fresh isolated local OpenAPI: **141 default-mounted operations**.
Production OpenAPI: **138 operations**. Production has no extra operation absent locally.
The conditional provider webhook is excluded from both default counts.

Local-only operations:

```text
GET /v1/admin/deleted-salons
GET /v1/admin/deleted-salons/{salon_id}/statement
GET /v1/media/results/{token}
```

Staging exposes 139 operations. The previous API handoff snapshot is also older than
current local source. Frontend teams must use the deployed contract until a reviewed
release is actually promoted. Existing operation schema/behavior parity was not fully
diffed; matching route names alone would not prove it.

### Recent errors requiring follow-up

A metadata-only query of production ERROR logs for the preceding 24 hours returned
three HTTP 500 request entries on the serving revision:

| UTC timestamp | Path, query removed | Status |
| --- | --- | --- |
| 2026-10-22 09:57:57.783795 | `/v1/salons/0001/services` | 500 |
| 2026-10-22 09:58:16.929725 | `/v1/salons/1/services` | 500 |
| 2026-10-22 09:58:18.347603 | `/v1/salons/1/services` | 500 |

These paths contain malformed UUID-like identifiers. That is consistent with the
existing audit's invalid-ID handling finding, but root cause was not established by
this check. They are not evidence that valid salon requests fail. No extra invalid-ID
requests were sent to reproduce them; application log messages and payloads were not
read. The query was limited to 20 entries and this service; it is not an exhaustive
incident audit across workers, proxies or other regions.

## 3. What data must move?

Cloud Run runs the API container; it is not the replacement storage location for
Supabase business records or R2 images. Choose the scenario before copying anything:

| Scenario | Required action |
| --- | --- |
| Same Supabase/Auth project, same R2 storage | Keep existing data in place and configure approved runtime access; no database copy merely because compute moves |
| Different Supabase project/database | Separate data and identity migration: backups, schema/history reconciliation, IDs, Auth users, references, validation and cutover plan |
| VM-only files | Inventory and back up needed persistent files; relocate appropriately, never depend on a Cloud Run instance's local filesystem for durable data |
| VM-local Redis | Determine whether cache-only or durable queue/application data exists; reconnect/rebuild or migrate only the required data under a separate plan |
| Same GCP project, different billing account | Change who pays for the same resources after billing approval; this does not itself require copying Supabase records |
| New GCP project/account | Recreate/rebind runtime resources, identities, secret access, registry and routing; preserve external data services where intended |

**Not yet verified:** VM database/Auth/storage targets versus production Cloud Run
targets, row/record continuity, actual Alembic history, VM-only files/volumes, and
whether the VM runs remaining workers. Secret values and guest runtime configuration
were deliberately not inspected. Therefore no data-copy or VM-retirement decision
can yet be justified.

Google documents that project resources belong to a project while its linked Cloud
Billing account determines payment. Changing that link is distinct from migrating
resources/data. Review permissions and service-specific effects before changing it:
[Google Cloud billing changes](https://docs.cloud.google.com/billing/docs/how-to/modify-project).

## 4. Remaining deployment blockers and manual work

### A. Finish the VM dependency inventory before retirement

Use an existing trusted VM access path. Do not create new SSH keys/project metadata,
change firewall/IAM, or expose runtime environment values just to obtain an inventory.
If access needs provisioning, review that change separately.

The VM operator should report sanitized results for:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
docker volume ls --format 'table {{.Name}}\t{{.Driver}}'
systemctl list-timers --all --no-pager
df -h
```

Then inspect only identified application containers' mount metadata, worker commands,
health and deployment pointers. Do not paste `docker inspect` in full: it can include
secrets. Inventory app-specific cron/supervisor tasks and persistent directories with
sanitized output. This report's readiness decision depends on verifying actual
dependencies, not just Docker container names.

A trusted operator must compare the existing and new nonsecret target identities for
database/Auth/storage/Redis without copying secret payloads into reports. Confirm
backup/restore readiness, authoritative data location, schema/history and ownership.
If a database target changes, use a separate reviewed migration plan; never replay or
stamp migration history to force a green deployment.

### B. Establish all required background processing

The Mumbai inventory proves only the notification worker pool is present/Ready. It
does not establish actual push delivery. No Cloud Run worker replacement was identified
there for email outbox, payment reconcile/webhook retry, media cleanup or account erasure.
These may still run on the VM or elsewhere; their absence globally is not proven.

Before stopping the VM, map each enabled feature to a functioning worker, runtime
identity, secret access, retry policy, monitoring and tested delivery. Disabled payments
do not excuse missing account-erasure/support processing if those features are exposed.
Do not execute erasure/refunds against live accounts as a smoke test.

Use a reviewed worker design: existing infinite-loop workers cannot simply be scheduled
as finite jobs without adaptation. Google provides worker pools for continuous work;
service CPU/billing settings affect background execution. Evaluate cost and availability
before choosing replacements. See [worker pools](https://docs.cloud.google.com/run/docs/deploy-worker-pools)
and [Cloud Run billing settings](https://docs.cloud.google.com/run/docs/configuring/billing-settings).

### C. Review production release and capacity

Resolve the three missing local routes and any schema differences against frontend
requirements, then build/test an immutable reviewed image. The deployed and local
versions must not be treated as interchangeable.

The serving API's pool budget is up to `(3 + 2) * 3 = 15` connections for three
single-process instances, before workers, other clients or rollout overlap. Earlier
repository evidence records a 15-client pooler limit; that current provider limit was
not independently rechecked here. Confirm current limits and shared target identities
before increasing capacity or promoting a candidate. The candidate's 3+1 setting is
not active on normal traffic. Do not alter pool policy merely to bypass saturation.

The current repository migration policy holds prepared Mumbai 0038–0040 behind explicit
target/evidence/manifest approval and prohibits implicit `upgrade head`/stamp. Live
database history was not queried. Use the [migration policy](../migrations/MIGRATION_POLICY.md),
not older runbook snippets, before any schema-dependent release.

### D. Complete business acceptance before release sign-off

Use isolated staging/test accounts and salons to verify real Supabase sign-in, customer
booking/quote, owner approval/check-in/collection/completion, QR OTP, media processing,
notifications/support, and appropriate account-deletion processing. Confirm CORS,
redirects, QR origin and admin MFA against real clients. Use sandbox credentials for
payment-provider verification only if separately approved; payments remain disabled now.

No authenticated business writes, real OTP/email/push sends, erasure, payment/refund or
load tests were authorized/performed in this read-only assessment.

## 5. Billing: what is known and what needs approval

**Owner decision, 22 October 2026:** keep the existing `saloon-505509` project and
change billing only. New-project provisioning and data migration are outside this
selected billing scope. Keep the existing services, identities, routing and data
targets. The owner subsequently supplied a billing account nickname identifying the
same account already linked to this project. A fresh read-only billing check confirmed
that the supplied account is linked and `billingEnabled=true`. **No relink is needed
for the supplied account.** Payments account/profile identifiers are distinct from
the Cloud Billing account identifier; personal payment identifiers are not retained
in this report. No billing change has been made.

Billing is currently enabled for `saloon-505509`; one accessible account was returned
as open. The supplied billing account is the current account, so no different
destination was selected. This does not establish
current spend, remaining credits, budget alerts, invoices or whether a new account
exists outside the inspecting identity's permissions.

There are concurrent resources to review for ongoing charges: running VM and disk,
production minimum-one API instance, manually provisioned notification worker instance,
load balancer/public routing, registry/secrets/logging and separate external providers.
Free-tier eligibility and actual invoices were not verified. No monetary forecast or
hard spending cap is claimed.

Recommended sequence if only the payer changes: keep the existing project/data targets,
confirm the authorized destination account/payment status and required IAM permissions,
then review and approve the exact billing relink. Do not disable existing billing as
an intermediate migration step. Payment-method entry or sensitive reauthentication
may need the account owner in Google's console. Review budgets/reporting after a move.

If a new GCP project is required, first provide its ID, region, destination billing
scope and ownership/access constraints. Prepare exact resources, IAM, secret transfer,
cost implications, rollback and traffic plan before requesting approval to execute.

## 6. Approval gates: concrete next steps

| Step | What must be ready first | Action needing separate approval |
| --- | --- | --- |
| Existing VM inventory | Trusted guest access; sanitized commands in section 4A | New key/firewall/IAM setup only if needed; read-only inventory itself is already in this assessment's scope |
| Data-target reconciliation | Sanitized source/destination identities, backup evidence and schema/history | Any export/import, restore, schema change or identity migration; name exact targets |
| Worker completion | VM findings, chosen worker design, image, required settings, cost/schedule and acceptance checks | Create/update workers/jobs/schedules/secret bindings |
| Release current API | Reviewed commit/image, passing checks, schema compatibility and staging acceptance | Deploy revision and promote exact revision/traffic share |
| Existing candidate promotion | Current candidate acceptance plus connection-budget review | Route normal production traffic to the named candidate; no automatic promotion |
| Billing-only move | Exact existing project and authorized destination billing account; owner permissions | Relink billing; owner completes any payment/reauthentication steps |
| New-project move | Exact destination and complete resource/data/cost/rollback plan | Provision/migrate/rebind and switch routing |
| VM retirement | No remaining workers/files/clients; backup and rollback verification | Snapshot if needed, then stop VM first and observe; deletion only as a later explicit action |

These gates follow the user's assessment-first request and repository deployment/
migration rules. They are not additional approval prompts for the completed read-only
checks. A general deployment approval must not be treated as permission for billing
changes, data restore, DNS cutover, account erasure or VM deletion.

## 7. Evidence and limitations

- [Sanitized live assessment JSON](../../.artifacts/cloud-run-assessment-2026-10-22.json)
  contains request timings/results, live service/worker/VM metadata, deployed/local
  operation comparison and error metadata. It is local ignored evidence, not a
  committed secret/config export.
- Load-balancer chain and Mumbai Scheduler/billing account status were verified with
  separate projected `gcloud` read commands; results are recorded in this report.
- [Earlier startup candidate study](cloud-run-startup-profile-2026-10-20.md) explains
  the pending candidate settings. This report rechecks live routing rather than
  treating that historical study as proof of release.
- Guest VM state, secret payloads, provider dashboards, database records/history,
  full frontend behavior, sustained capacity, invoice costs and backup restore were
  not inspected/tested in the initial infrastructure pass. That pass did not run
  local Python tests/lint; the subsequent isolated runs are documented in section 8
  and do not by themselves prove deployed business behavior.

Final status: **HTTP deployment/readiness pass; complete operational migration and
VM retirement remain unverified; billing/data moves remain unexecuted.**

## 8. Frontend integration test follow-up — 22 October 2026

The owner subsequently requested actual integration checks and instructions for
using the working API. The results below distinguish live Cloud Run checks from
isolated local tests. No production deployment, live booking, OTP send, payment,
account deletion, database migration or frontend source edit was performed.

### Live production contract checks

Target: `https://apiv1.mudassirmhd.in`. **27 checks: 20 passed, 7 failed**, exit code 1.
Assertions checked status, basic declared required fields/types on JSON success
responses, and expected error contracts. This was not a full JSON Schema validation.

| Result | Evidence and frontend implication |
| --- | --- |
| Swagger/OpenAPI and four health checks pass | Documentation and serving process/dependencies are reachable |
| Payment/subscription configuration passes | Capability responses are readable; billing providers remain disabled |
| Catalog, home, search and nearby requests pass basic declared response checks | Every sampled result is an empty array; no visible bookable salon or category was available for the next live journey step |
| Six malformed-token checks pass | Customer, owner, admin, booking, profile and notification reads reject invalid bearer tokens with 401 and application error envelope |
| Six missing-token checks fail the current error-envelope contract | HTTP 401 is correct, but the deployed response lacks the current source's structured error.code/error.message form; this is not an authentication bypass |
| Unknown QR fails current error-code contract | HTTP 404 is correct, but deployed code is not_found rather than the current source contract's qr_not_found |
| Missing availability input and invalid pagination pass | Validation returns 422 with the custom error envelope |

No salon-detail/service/staff/valid-slot request could follow discovery because it
returned no salon. Empty discovery does **not** prove the database has no salon rows:
approval, publication, setup, trial/subscription and other eligibility filters may
exclude them. Determine the intended data target and eligibility with the operator;
do not import a database or approve a real salon just to fill a test screen.

The first checker run incorrectly required `error.details` on every error. Source
inspection confirmed it is optional, so the checker was corrected and rerun. The
final seven failures above remain genuine differences from current source contracts;
the initial run is retained separately and is not counted as thirteen product defects.

Evidence: [final live check results](../../.artifacts/live-frontend-api-checks-2026-10-22.json).
No customer records, real tokens or credentials were exported.

### Isolated backend verification

A new PostgreSQL 18 container was created on loopback port 55473, separate from the
already running local application stack. Test processes used a sanitized environment
and a nonexistent env-file path. Existing test fixtures created their own disposable
databases. Only the allowed portable schema path through 0037 was used; prepared
Mumbai 0038–0040 and all remote databases were untouched. The task-labelled container
was verified and removed after the tests; the existing application stack was preserved.

The default full run completed with **1,304 passed, 36 skipped, 0 failed**, exit code 0,
in 157.75 seconds. Ruff for `app tests migrations` passed, exit code 0. One existing
Starlette/AnyIO deprecation warning was emitted.

Real-database coverage within that run:

| Suite | Passed |
| --- | ---: |
| Booking contract: direct/QR creation, source restrictions, retries, tenant/key scope and overlapping slots | 8 |
| Checkout safety: limits, collection/completion, trial, no-show and related guards | 15 |
| Portable deployment migration chain | 1 |
| Payment ledger | 9 |
| Subscription billing SQL | 23 |

Provider adapters/gateways and hosted identity were faked where the tests require
them. These results do not establish live Supabase sign-in, SMS, Cashfree/Razorpay,
email, push, or browser/device behavior. A further four fake-provider integration
tests passed in that default run and must not be counted as real provider verification.

### Additional opt-in suites: not green

The 36 skips were examined rather than counted as passes. A separate attempt enabled
16 opt-in erasure, approval, media-locking, service-presentation and website migration
tests against a newly prepared disposable 0037 database. **2 passed, 14 failed**,
exit code 1. This attempt does not invalidate the recorded default-run counts, but
it prevents claiming that all available integration suites pass.

Observed setup/schema incompatibilities:

- Erasure fixture writes legacy `cancellation_reason_code`/`cancellation_reason_text`
  columns absent from this portable schema; its classification check also reports
  newer text/JSON columns missing from the treatment matrix. The fixture's historical
  schema assumptions do not align with the current portable target.
- Website migration fixture attempts to create `auth` where this prepared database
  already has that schema; that portion of the attempt used an incompatible setup.
- Approval fixture fails on a missing generated `approval_test_*` role.
- Service-presentation fixture raises `RuntimeError: coroutine raised StopIteration`.

These require fixture-specific preparation/review before meaningful acceptance runs.
No test assertions, application code or migration policy were weakened to obtain a
pass, and no forbidden migration was applied. Failure logs are retained for diagnosis;
these failures are not evidence that the same operations fail in production.
The 20 Redis recovery cases were not enabled in this follow-up.

Evidence: [default JUnit](../../.artifacts/journey-tests-2026-10-22/pytest.xml),
[default output](../../.artifacts/journey-tests-2026-10-22/pytest.log),
[Ruff](../../.artifacts/journey-tests-2026-10-22/ruff.log),
[opt-in JUnit](../../.artifacts/journey-tests-2026-10-22/optin-pytest.xml).

### Existing frontend tests and source compatibility

Existing frontend suites were invoked using synthetic test configuration with normal
env-file loading disabled; reports/caches were directed into the backend's ignored
artifacts. These are local mocked/component tests, not frontend-to-Cloud-Run journeys.
| Client suite | Result |
| --- | --- |
| Website | 413 passed, 0 failed; exit 0 |
| Customer app | 332 passed, 3 failed; exit 1 |
| Owner app | Full run timed out after 360 seconds; one component suite had reported PASS, but no complete result is claimed |

The customer failures reproduced in a focused rerun (1 passed, 3 failed), all in
`src/hooks/__tests__/useSalonOpenStatus.test.tsx`: unexpected early refetch, stale
09:00 hours where 10:00 was expected, and duplicate refetch. They are repeatable local
test failures; their cause and real-device impact need investigation before release.
The focused owner API-client logic rerun passed **17 tests**, exit 0. This narrows the
evidence to its client/auth-refresh handling; it does not resolve the incomplete full
run or prove the complete owner journey. No release build or device/browser acceptance
is established by any of these unit/component suites.

Evidence: [frontend suite summary](../../.artifacts/journey-tests-2026-10-22/frontend-results.json),
[website results](../../.artifacts/journey-tests-2026-10-22/website-tests.json),
[customer results](../../.artifacts/journey-tests-2026-10-22/customer-tests.json),
[customer failure reproduction](../../.artifacts/journey-tests-2026-10-22/customer-focused.json),
[owner API-client results](../../.artifacts/journey-tests-2026-10-22/owner-focused.json).

Focused source inspection also found older assumptions that developers must reconcile:

- `salon-owner-APP/src/api/contract.ts` declares only five booking states and
  `cash|online`; the newer backend contract includes checked-in/no-show and direct
  collection `cash|upi_direct`.
- The customer app's appointment status mapping in
  `customer-app/src/services/api/api.types.ts` handles the older five-state set.
- The website's disabled `lib/api/mockOnly.ts` comment says quote routes are absent,
  while production now exposes `/v1/bookings/quote`. That module explicitly says it
  is not imported by pages: its existence alone is not proof of a broken screen.

This is a focused compatibility review, not an exhaustive frontend audit. Passing
tests against older mocks does not establish compatibility with every newer API state.

### How frontend developers access the working API

1. Use `https://apiv1.mudassirmhd.in` as the API origin. Swagger `/docs` is the human
   explorer; `/openapi.json` is the machine-readable contract. Neither is the base
   URL for ordinary API calls, and downloading OpenAPI does not grant authentication.
2. Public example: `GET https://apiv1.mudassirmhd.in/v1/salons?surface=search`.
   This currently returns an empty list in the sample; it is a working HTTP request,
   not proof that a customer can complete a booking.
3. Sign in through the client's configured Supabase project, obtain a valid session,
   and send its access token to protected API paths. A Google Cloud IAM token is not
   a customer/owner session. Tokens must not go into URLs, source code or reports.
4. Configure the existing clients through their actual adapters:

   | Client | Verified source configuration behavior |
   | --- | --- |
   | Website | Server `API_BASE_URL=https://apiv1.mudassirmhd.in`; its adapter strips trailing /v1, and request paths supply /v1 |
   | Customer app | `EXPO_PUBLIC_API_URL=https://apiv1.mudassirmhd.in` (or its supported API_BASE_URL alias); adapter normalizes trailing /v1 and services supply /v1 |
   | Owner app | `EXPO_PUBLIC_API_URL=https://apiv1.mudassirmhd.in`; its adapter adds /v1, so repository requests use relative resource paths |

5. Keep the configured Supabase URL/public key and auth redirects aligned with the
   backend's intended identity project. Regenerate each client's types from the
   **deployed** OpenAPI, review differences and update parsers/UI/mocks; generating
   types alone does not wire screens or implement missing flows. Restart/rebuild
   clients as their framework requires after configuration changes.
6. Test the actual website origin's CORS/preflight behavior if calling FastAPI from
   a browser. The inspected website has a server/BFF path; preserve that session and
   relay design. Actual deployed frontend origins/settings were not supplied/tested.

### What still prevents complete journey sign-off

The request for dedicated staging customer/owner/admin accounts and a test salon is
pending. No such session was available to this test run. Real hosted login, owner
onboarding/review, create/approve/collect/complete, cross-account ownership, QR OTP,
media, notification/support delivery and account deletion therefore remain unverified
end to end. Do not use real users or service-role privileges to bypass that missing
test setup.

Next: provision/identify approved isolated fixtures and secure test-session access,
resolve the fixture and client-contract gaps, release the reviewed backend version
when separately approved, then execute customer/owner/admin journeys against that
specific release. Payments remain a separate disabled-provider/sandbox gate.

**Conclusion:** production public/readiness APIs are reachable, but the complete
frontend journeys are not yet accepted. Empty live discovery, contract differences,
opt-in fixture failures, three reproduced customer-app test failures, incomplete owner
suite and missing authenticated staging fixtures are recorded blockers.

## 9. Existing owner-account and Android prerequisites

After the owner confirmed that an owner-app test account exists, the project folders
were inspected for the established staging setup. Connected Supabase metadata identified
the Mumbai project `wqjlgpnbiapcrlkxumcp`. The following database checks used explicit
READ ONLY transactions through the connected Supabase tool; no credentials, contact
details or secret payloads were retrieved, and no rows were changed.

| Connected Mumbai project check | Result |
| --- | --- |
| Active owner profiles | 1 |
| Active owner's Auth identity | Exists, email verified, not currently banned |
| Salon linked to that active owner | None |
| Active customer profiles | 4 |
| Active super-admin profiles | 1 |
| Active, profile-complete, approved salons | 0 |
| Active salons otherwise observed | 3 pending/incomplete |
| Older synthetic owner test identities | 3 inactive/banned, with inactive hidden salons |
| Alembic version table | Exists, but no version rows returned |

The active owner was not marked synthetic by the inspected name/email patterns.
Do not assume it is the owner's intended test identity until its app session is
confirmed. No password/session was retrieved or generated, accounts were not reset
or unbanned, and no existing salon was approved or reactivated.

This independently establishes a missing bookable fixture in the connected Mumbai
database. It is consistent with the empty public API results, but does not independently
prove the production service's secret-loaded database target is identical. Empty migration
history is not permission to stamp or replay the baseline; preserve the target-specific
review gates before any database migration.

An older website staging runner was found under
`walking-customer-web/scripts/staging/run.py`. It creates identities/data and its cleanup
disables accounts and salons. It was **not executed** against the existing account.
Its historical credentials/fixture lifecycle must not be reused blindly for this test.

Native tests still needed: actual Google/provider sign-in and return to the app, owner
onboarding/edit persistence, pending/approved routing, customer-to-owner booking flow,
collection/completion refresh, camera/QR/media permissions, push/background/resume and
session recovery. Local unit/component tests do not establish these native behaviors.

ADB was available, but two device-list checks returned no connected Android device.
Next device preparation: USB connection with data transfer enabled, Developer options
and USB debugging enabled, and acceptance of the computer authorization prompt. Keep
the owner app installed and sign in using the existing test account on the device;
do not send its password/token in chat. Verify its backend/Auth target before any
mutation. An active owner login can exercise onboarding, but booking acceptance needs
a deliberately configured test salon and authorized admin review; an owner login alone
cannot approve a salon or substitute for a customer/admin test session.

No database deletion or additional local full-suite rerun is needed merely to connect
the phone. The unresolved results in section 8 remain open.

## 10. Connected Android and Playwright follow-up

### Results and limits

| Check | Verified result |
| --- | --- |
| Existing website Playwright suite, desktop and mobile | 80 passed, 10 failed, 2 skipped; 92 cases, exit 1 |
| Current website booking-entry navigation | 4 passed: discovery and scanner links on desktop/mobile, exit 0 |
| Customer app on connected Android | Playwright verified home, empty salon catalog and navigation to My Bookings |
| Owner Google login | Owner selected the existing test Google account; corrected test APK reached onboarding |
| Owner session after restart | Returned to Gallery, step 5 of 8; later the owner continued into service setup |
| Production protected requests in the same test window | Auth profile, owner salon, services and staff returned 200 on revision `salon-api-production-00004-nx7` |
| Production gallery attachment | `POST /v1/salons/me/images` returned 500; logs identify `SalonImageResponse` validation |
| Local gallery regression tests | Three cases failed before the fix and passed afterward: list, create and update with database UUID identifiers |
| Full backend suite after gallery fix | 1,307 passed, 36 skipped; exit 0; Ruff passed |

The website suite used its established **mock backend**, synthetic public configuration
and the real Next.js build. It does not prove live OTP, Google, payment or authenticated
booking completion. Ten failures expect the previous `/book` heading, link labels or
animation selectors. Current source uses “Find a salon” and “Scan to book”; both routes
passed the four additional checks. Existing assertions were not weakened or skipped.
The animation expectations still need reconciliation with the current design.

Native owner Playwright attempts targeted a fixed onboarding screen while the owner
was advancing through setup and timed out. They are **not counted as passing owner
automation**. The login finding rests on the owner's confirmation, actual Android UI
captures, cold restart and protected production HTTP results. Customer native checks
cover three screen assertions, not a completed booking. Earlier customer unit-test
failures and the incomplete owner unit-suite result remain as recorded in section 8.

### Owner login recovery

The originally installed APK bundled Auth host
`puuptxogwtylbutosqek.supabase.co`, which failed DNS resolution. The active Mumbai
project's public Auth settings returned 200 with Google enabled. A corrected bundle
uses `https://wqjlgpnbiapcrlkxumcp.supabase.co`, its enabled publishable key, the active
Google Web OAuth client from the owner's Firebase project configuration, and API origin
`https://apiv1.mudassirmhd.in`. No identity-provider secret or account password was read.

The original APK also lacked the NetInfo native module required by current source.
An initial bundle-only attempt exposed that incompatibility and was reverted. The
working test APK combines the corrected **normal app entry point** with an existing
compatible local native build containing NetInfo and Google Sign-In. It uses the same
signing certificate, was installed with replacement/data preservation and does not use
the local fixture entry point or an authentication bypass. The owner personally selected
the Google test account. Google login subsequently reached onboarding.

This is an installed **local verification APK**, not a store-ready release. A separate
complete release build failed compiling Reanimated because Windows reported that its
paging file was too small. No system memory/security settings were changed. Produce a
fresh release in a sufficiently provisioned build environment, using the corrected
public configuration; verify its native modules, signing and login before distribution.
Existing real environment files were not read or edited, so future builds must explicitly
receive the corrected configuration through the team's approved build settings.

### Gallery API fix deployed after explicit approval

`SalonImageResponse` declares string IDs, but repository rows contain UUID objects.
Pydantic v2 rejects those values when the owner image routes construct the response.
The local patch converts UUID values for `id` and `salon_id` at this HTTP boundary,
preserving the documented string contract and rejection of unrelated input types.
It changes no authorization, storage policy or database schema.

The three route regressions reproduced the failure before the patch. All 16 media
tests passed afterward; the full suite and Ruff then passed against a disposable
loopback-only PostgreSQL container. The run reported an AnyIO deprecation and a pytest
cache-write warning. Previous opt-in fixture failures were not rerun or declared fixed.

The user explicitly approved the scoped production gallery hotfix. The image was
built from the exact serving production digest with only the schema UUID conversion;
unreleased checkout features were excluded. Candidate health, database and Redis checks
returned 200 before promotion. Its 138-operation OpenAPI set and image response schema
matched production.

The new revision `salon-api-production-gallery-20261022` now receives 100% of normal
traffic. Published image digest:
`sha256:2bffc8fa1680ac59b580ef16c0399928966d5f6d0feb10e22f4b6fbd53b61f6f`.
Rollback revision `salon-api-production-00004-nx7` is retained. After promotion,
`https://apiv1.mudassirmhd.in/health`, `/health/db`, `/health/redis` and `/openapi.json`
returned 200; the deployed operation count remains 138.

The phone retry reached the pending super-admin review screen. Production logs on
the new revision show gallery attachments 201, service creation 201, staff creation
201, and `POST /v1/salons/me/complete-profile` 200 at 14:24:06 UTC (19:54 IST).
An owner profile edit subsequently returned 200. This establishes that the reported
Finish failure was resolved. It does not approve the salon or establish a completed
customer booking. No migration, billing change or VM retirement accompanied the hotfix.
Sanitized rollout/readiness/write evidence is in
`backend/.artifacts/gallery-hotfix-20261022/live-verification.json`.

The local owner UI also returns failed photo attachment to Gallery, keeps the pending
photo for retry, and fixes the stacked duration selector layout. Its 28 onboarding
component tests passed before the later changes in section 11. The full owner typecheck
already reported booking-schema test mismatches outside that onboarding diff.

### Next acceptance gates

1. Gallery hotfix and Finish retry are complete; obtain authorized super-admin review of the submitted test salon.
2. Produce and verify a fresh owner release build with the corrected public configuration.
3. Identify an isolated test salon and customer/admin sessions; complete onboarding and
   authorized admin review before customer booking/QR acceptance. Recheck current data:
   section 9's account/salon counts predate the owner's interactive setup.
4. Exercise customer booking, owner decisions/collection/completion, QR/OTP, media,
   push/background/resume and session recovery. Payments remain disabled and unaccepted.

Local evidence is under `backend/.artifacts/frontend-e2e-2026-10-22/`: website JSON/logs,
the current-navigation results, Android captures, the corrected test APK and
`gallery-regression/pytest.xml`. APKs/screenshots are private local test artifacts and
are not committed. Playwright was already installed in the website; its Android helper
and test-driver APKs were installed for the authorized phone checks.

## 11. Requested description removal and independent photo slots

### Confirmed scope

The owner corrected the earlier request: **keep salon categories, service categories,
subcategories and the shared catalog**. Remove only salon and service description
fields from their HTTP contracts, stored columns and rendered screens. Catalog/plan
descriptions and explanatory UI/error copy are separate fields and remain in scope
for their existing features.

Final photo limit is **one separate cover plus Slides 1 and 2**: three photos total,
with at most two non-cover slides. It is not two photos including the cover. Each
slot must retain its own image, and empty slides must not be filled by repeating the
cover. The owner authorized retaining the cover and the first distinct photos in
gallery order; following the clarified limit, keep the first two distinct slides.
Retire extra/duplicate gallery references through `is_active=false`; do not immediately
delete storage files. Existing verified media cleanup remains responsible for binaries.

### Prepared implementation; production unchanged by this follow-up

- Backend requests reject removed descriptions and responses omit them, including QR
  payloads and admin onboarding responses. Category contracts remain intact.
- Gallery responses keep the cover and at most two unique slide URLs, including
  protection when an older cached payload has extra rows. QR responses now include
  the same bounded `images` collection.
- Writes serialize on the salon row and validate role capacity and duplicate URLs.
  Repeating a successful attachment can return its existing row; the same URL cannot
  be attached into a different photo role. Expected database violations map to safe
  application errors. This checks reference URLs, not visual similarity of different
  files or byte-for-byte content uploaded under different URLs.
- Owner Settings/onboarding/service UI removes descriptions, preserves category
  controls and offers two slide destinations. Replacements use the existing image
  PATCH route, so a failed replacement leaves the saved image intact. Owner response
  parsers discard legacy descriptions instead of requiring the removed field.
- Customer and website screens stop rendering salon/service descriptions, even from
  old cached payloads. Photo views separate the cover from the two gallery slides.
  The website's existing OpenAPI snapshot/types are updated only for these changes;
  unrelated endpoint and payment contracts are preserved.
- New revision `0041_salon_photo_limits` drops only `salons.description` and
  `services.description`, retires excess/duplicate active photo references, creates
  an active URL uniqueness index and enforces the two-slide limit in a trigger.
  It preserves QR RPC signature/ACLs with a null legacy SQL output and leaves booking
  functions unchanged. HTTP responses omit that legacy description output.
- Account erasure continues clearing old description columns while they exist during
  rollout; it does not recreate removed columns or write new description content.

### Release and migration gates

**This follow-up is local and prepared for review, not a second approved production
release.** The prior approval authorized only the gallery UUID hotfix. The production
OpenAPI still describes that deployed release until a separately approved API rollout.

Deploy updated owner clients before removing response fields: older owner builds have
required-description parsers and would fail against the new response. Complete client
regressions and verify the phone build before approving the coordinated API release.

Do not run `alembic upgrade head` or stamp Mumbai. Existing Mumbai migration history
is empty, 0038–0040 remain held, and the migration policy deliberately refuses 0041.
Reconcile history with the existing target-specific review first. A reviewer must
approve exact 0041 source, affected-row counts, preservation order and a controlled
maintenance window. It holds table locks while dropping fields, retiring references
and creating the index; lock acquisition is limited to 5 seconds and each statement
to 15 seconds. Rehearse against representative data before production execution.
Description values cannot be recovered by downgrade; use the approved backup/recovery
process when planning that irreversible step. Gallery rows are soft-retired, not erased.

The trigger supports READ COMMITTED writes and rejects other transaction isolation
levels with a retryable serialization failure rather than relying on stale snapshots.
No production description data or photos have been removed in this follow-up, no
salon has been approved, and no production migration has been executed.

### Final verification for this follow-up

| Check | Result and scope |
| --- | --- |
| Complete backend suite after review fixes | **1,319 passed, 36 skipped**; disposable loopback PostgreSQL; no live database writes |
| Backend Ruff | Passed after correcting one import-order finding in the new SQL test |
| New PostgreSQL regression | Passed: description-column removal, owner-isolated legacy erasure before/after removal, retained categories, ordered photo retirement, unchanged storage references, QR ACL preservation, concurrent upload limit, reactivation rejection, cover replacement and isolation-level refusal |
| Complete-schema forward DDL check | Passed on the disposable migrated schema; booking/availability function definitions preserved; no production history stamped |
| Owner Settings/onboarding/services components | **60 passed**; includes hidden legacy descriptions, retained Category and two slide controls |
| Owner photo/editor/API logic | **51 passed** across the four targeted suites; the final affected hook/editor subset also passed, 15 tests |
| Customer photo and service-card regressions | **8 passed**; old cached descriptions do not render and the gallery excludes cover duplicates/third slides |
| Website unit suite | **415 passed** with two workers; an earlier parallel run had a discovery-screen timing failure, which was not suppressed or asserted away |
| Website Playwright, actual Next production build | **4 passed**: public salon details and QR photo contract, desktop and mobile; synthetic intercepted API responses, not live authenticated booking |
| Website/customer TypeScript | Passed |
| Changed owner screen lint and website lint | Passed |
| Owner full TypeScript | Still fails in the previously observed `src/lib/validation/booking.schema.test.ts` expectations; no remaining diagnostics from the description/photo changes |
| Updated Android owner build | Normal app entry exported successfully; signed verification APK installed with replacement/data preservation; existing session retained |
| Actual owner screen inspection | Business Details shows Category and no Description. Profile shows two distinct saved slides. Photo editor offers a separate cover and two slide destinations |
| Native Playwright limits | Three presence assertions passed on the profile (Slide 1, Slide 2, Category). Further editor/absence assertions timed out on native selectors. The complete native suite is **not** signed off; UI inspection and component regressions are separate evidence |

Code review found and corrected two scoped issues: ignored null image-PATCH values
are normalized before capacity validation, and the QR thumbnail query excludes
inactive images. Both cases pass the real PostgreSQL regression. Security review
reported no scoped security blocker; its request for a focused pre/post-removal
erasure regression was implemented and passed. Migration review found no remaining
source blocker for keeping 0041 prepared and unapplied; its production gates above
remain mandatory.

The installed owner APK remains a **verification build** using an existing compatible
native base. The earlier clean release build failed on Windows paging-file capacity;
this follow-up does not certify a fresh store release. Customer changes are verified
in source/tests; a rebuilt customer APK was not installed in this follow-up. Website
changes were built/tested locally and were not published to hosting.

Evidence: `backend/.artifacts/profile-photos-verification-20261022/pytest.xml`,
`ruff-final.log`, and `backend/.artifacts/frontend-e2e-2026-10-22/` test logs,
`salon-photo-playwright.json` and private native captures. Earlier failed attempts
remain recorded; they are not counted as passes. No credentials or private captures
are embedded in this document.

### Manual and release work still required

1. An authorized super admin must review the submitted test salon through the admin
   approval flow. No account role or approval was bypassed. Customer/owner booking,
   payment collection/completion and QR/OTP acceptance remain pending that fixture
   and appropriate customer/admin sessions.
2. Distribute compatible owner clients before removing description response fields.
   Prepare/review a scoped production API candidate against the serving release;
   do not deploy the entire local branch with unrelated unreleased features.
3. Reconcile Mumbai migration history, approve the exact destructive revision and
   rehearse its lock/retention plan before a human executes it. The repository's
   [migration skill](../../../.claude/skills/alembic-migration/SKILL.md) says
   **"Never auto-run"** and **"Never run against anything but a local/throwaway DB."**
   The existing gallery-hotfix approval does not authorize this new schema release.
4. Finish the native end-to-end and broader integration checks listed in sections
   8–10. Keep the old VM and background workers until their separate continuity and
   retirement gates are satisfied. Payments remain disabled and unaccepted.

## 12. Continuation on 23 October: scoped candidate prepared, production unchanged

The description/photo API release is now a concrete local image based on the
immutable serving release, rather than the whole development branch. It changes
only six application files: the platform/admin/walk-in schemas, shared photo policy,
platform repository and account-erasure compatibility adapter. It excludes unrelated
booking, search, payment, media-generation and closed-salon statement changes, and
contains no migration. It deliberately retains the serving release's other API
behavior and its **138 operations**; it is not a release of every local endpoint.

Review found a transition bug: legacy third slides were hidden from reads but could
prevent replacing visible slides. The fix permits existing-row edits that do not
increase existing photo counts or introduce another duplicate URL. New additions
still enforce one cover, two slides and three active photos total. Four regressions
were added, including a three-slide legacy gallery trying to add a fourth photo as
a new cover. The affected cases failed before the fix and passed afterward. Review
closed with no remaining source blocker for this local candidate.

| Check performed on this continuation | Result |
| --- | --- |
| Final complete current-backend suite, disposable PostgreSQL | **1,323 passed, 36 skipped**, one dependency deprecation warning |
| Backend Ruff and whitespace checks | Passed |
| Serving-based candidate feature tests | **13 passed** |
| Serving-based candidate PostgreSQL regression | **1 passed**, including prepared 0041 behavior on a throwaway database |
| Built candidate with serving image dependencies, networking disabled | Passed: 138 operations, description absent from 12 affected schemas, categories retained, bounded images, legacy replacement permitted and fourth addition rejected |
| Actual owner app through Playwright | **3 presence checks passed**: Category, separate cover and Slide 2 |
| Separate Android UI-tree inspection | Details retains Category and omits Description; Photos shows Slides 1 and 2 and no Slide 3 |
| Live API recheck | Process/database/Redis health and OpenAPI all HTTP 200; gallery-hotfix revision still receives 100% traffic |

Native omission checks used Android's UI tree separately: Playwright's missing-element
lookup raised a driver exception. The complete booking/onboarding native suite is
still not signed off. No photo was uploaded, business setting saved or booking created
during these phone checks.

Newer media-generation tests were also compared with the unchanged serving source.
The baseline had 8 failures/50 passes; the candidate had 7 failures/60 passes before
the final extra transition regression. The same seven newer media expectations fail
on both sources; the eighth baseline failure is the photo replay query-count change
covered by this candidate. These runs do not establish a fully passing media suite
for the serving release, and unrelated media code was not added to silence them.

The immutable base reference `sha256:2bffc8fa1680ac59b580ef16c0399928966d5f6d0feb10e22f4b6fbd53b61f6f`
is an OCI image index. Its Linux/amd64 image is
`sha256:4bdc712f225fa32e17ba9401da0ecd50a41d826acb96cb3d4f082d21e7feae11`,
which matches Cloud Run's reported serving digest. An initial guard stopped on this
distinction; registry descriptor verification resolved it without weakening the
identity check. These are two identifiers for the same verified release.

Local candidate: `salon-api-photo-candidate:20261023`, image ID
`sha256:ce4f8856a2677f8beca0730ab74184215b748916a7009ad314da17240ed2741a`.
The prepared Cloud Run revision is `salon-api-production-photos-20261023`, initially
tagged `photos-review` with zero normal traffic. Its rollback target is
`salon-api-production-gallery-20261022`. Runtime settings and secret references are
inherited; no billing, VM, DNS or database change is proposed by this API-only rollout.

Evidence remains under `backend/.artifacts/photo-release-20261023/`: source inventory,
six-file diffs/hashes, image smoke results, candidate feature/SQL tests, full-suite
JUnit/log, native assertions, rollout review and unapplied manifest. The candidate
has **not** been pushed or deployed. Compatible owner-client rollout must be confirmed
before removing response fields; a question about older installations is pending.
The prior approval covers only the gallery UUID hotfix, so this separate production
release still needs approval. Migration-history reconciliation and human review/
execution of 0041 remain separate gates; stored legacy descriptions and excess image
references have not been removed from production. Super-admin approval and live
customer booking/QR acceptance remain outstanding.

## 13. Approved zero-traffic candidate deployed and checked on 23 October

The owner confirmed that only the connected test-phone owner installation is in use
and explicitly approved **the zero-traffic candidate only**. This resolves the known
older-owner-client population question; it does not authorize traffic promotion or
the destructive database migration.

The exact reviewed six-file image was published and revision
`salon-api-production-photos-20261023` became Ready at approximately **00:23 IST on
23 October 2026**. Cloud Run reports Linux/amd64 image digest
`sha256:47a78b21c4d8098bbac5fcd23f13237058984dae40d4d5a6fa2dce3be535236d`,
contained in published OCI index
`sha256:ce4f8856a2677f8beca0730ab74184215b748916a7009ad314da17240ed2741a`.

- Candidate base: <https://photos-review---salon-api-production-jmqpp743pa-el.a.run.app>
- Candidate Swagger: <https://photos-review---salon-api-production-jmqpp743pa-el.a.run.app/docs>
- Candidate OpenAPI: <https://photos-review---salon-api-production-jmqpp743pa-el.a.run.app/openapi.json>
- Normal client API remains `https://apiv1.mudassirmhd.in` on
  `salon-api-production-gallery-20261022`, **100% normal traffic**.
- Candidate tag `photos-review` receives **0% normal traffic**; its tagged URL is
  directly reachable for approved checks. It uses inherited runtime connections and
  is not an isolated database environment.

All **10 live checks passed**: process/database/Redis health (HTTP 200), unchanged
138-operation set, description removal from 12 affected schemas, retained salon and
service category fields, four bounded photo arrays, unchanged gallery identifier
contract, unchanged normal-production description contract, and Swagger UI HTTP 200.

This establishes deployment readiness and the public contract of the candidate,
not authenticated business acceptance. No owner/customer booking, upload, admin
approval or payment mutation was performed in these checks. No migration, legacy
data retirement/deletion, billing change, DNS change, VM change or normal-traffic
switch occurred. Remaining gates are authenticated business-journey verification,
separate approval for any traffic promotion, and the existing history/review/manual
execution requirements for 0041. Customer APK and hosted website release limits
from section 11 still apply.

Evidence: `backend/.artifacts/photo-release-20261023/publication.json`,
`candidate-deploy.log`, `candidate-rollout.yaml` and
`live-candidate-verification.json`. Earlier prepared-only notes in section 12 describe
the state before this separately approved deployment.

## 14. App completion and cost/cleanup review, 23 October 2026

**Neither mobile app is fully complete or fully verified against every intended API.**
Source integration, focused tests, an installed verification build and a successful
backend deployment are different acceptance milestones. No completion percentage is
assigned because there is no agreed, fully executed feature acceptance checklist.

| Surface | Completed evidence | Still pending |
| --- | --- | --- |
| Owner app | Real Google login/session recovery; onboarding Finish succeeded against the hotfix; photo/description UI changes installed on the test phone; category retained; focused screen/photo tests passed | Super-admin salon review, full real booking/collection/completion journeys, complete native suite, clean release build; unavailable advanced API features below |
| Customer app | Real API adapters exist for discovery, availability, bookings and account features; description/photo fixes in source; focused regressions and TypeScript passed | Updated APK installation and real authenticated booking/cancellation/QR acceptance; online checkout unimplemented/disabled; unsupported payment-options and cancellation-quote calls remain |
| Website | Public/QR/admin integrations exist; photo/description source fixes; local production build, 415 unit tests and four photo browser checks passed | Publish updated site; complete owner web workspace/customer-account scope and full live journeys; browser photo checks used synthetic API responses |
| Backend/deployment | Main API healthy on Cloud Run; gallery hotfix handles normal traffic; reviewed photo/description candidate healthy at zero traffic; latest complete local suite 1323 passed/36 skipped | Candidate business acceptance and separately approved promotion; reviewed/manual destructive migration; worker continuity and VM retirement |

### Current API wiring gaps

A fresh comparison with both the main and candidate OpenAPI documents (138 operations
each) confirms these source-referenced route families are absent. This is a source/
contract comparison; no protected write was attempted.

- Customer: salon `payment-options` and booking `cancellation-quote`. The payment-options
  hook falls back on failure, but uses a different shape from the backend's existing
  salon capability fields. Its online checkout flag is explicitly false.
- Owner: `alert-settings`, `commission-rules`, `ledger/daily`, `slot-filler-rules`,
  notification delivery acknowledgement and `auth/session-started`. Several reads
  handle an unavailable backend; that fallback does not implement the feature.

These need a deliberate feature decision: wire supported equivalents, hide/defer
unbuilt features, or implement the intended backend contract. Publishing the scoped
photo candidate does not add those missing APIs or release every local backend feature.
Evidence: `backend/.artifacts/client-contract-gaps-20261023.json`; current source was
also inspected. The earlier usage matrix remains a dated static inventory.

### Fresh resource inventory and cost implications

Captured around **00:47 IST on 23 October**; project `saloon-505509`. This inspection
made no infrastructure, scaling, billing or deletion changes.

| Resource | Verified configuration | Cost implication / next action |
| --- | --- | --- |
| Production Cloud Run service | 50 saved revisions; service minimum 1 / maximum 3; request-based CPU; 1 vCPU/512 MiB | One warm API instance is deliberately kept provisioned; propose minimum 0 / maximum 1 for low-traffic testing |
| Staging Cloud Run service | 14 saved revisions; minimum 0; revision maximum 1, service maximum 3 | Can scale to zero; saved revisions are not 14 continuously running machines |
| Recent API instance metrics | Latest returned sample: serving gallery revision active 1/idle 0; candidate active 0/idle 0 | Sampling is not a billing ledger or a guarantee about future/current transient counts |
| Notification worker pool | `salon-prod-notifications`, manual instance count 1, 1 vCPU/512 MiB | Continuous worker allocation; stopping it pauses push processing unless replaced |
| Old VM | `instance-20261009-141410`, RUNNING `e2-medium` in `us-central1-a`; attached 10 GiB standard disk | Recurring compute/disk/network costs; guest dependencies and backups must be verified before retirement |
| Public API load balancer | Global external managed HTTPS forwarding rule and reserved IP in use | Supports the current API domain; deleting it breaks that route. Published forwarding-rule list rate is $0.025/hour, about $18.25 for 730 hours before credits/taxes/other networking charges |
| Artifact Registry | Three repositories, approximately 612 MiB total; no cleanup policies observed | Stored images cost separately; inspect references before pruning. Published allowance is 0.5 GiB-month per billing account |
| Cloud Run job / Scheduler | One database-check job; no Mumbai Scheduler jobs returned | A saved job definition is not evidence of a running execution; no job was started by this review |

There are **64 saved API revisions across two services**, not 64 proven running
instances. All listed revisions have revision minimum 0. Google states that revisions
receiving no requests consume no resources and are not billed, subject to minimum-
instance considerations. Pruning old revisions mainly removes clutter/rollback
history; it does not by itself remove VM, worker, load-balancer or image-storage costs.
See [revision billing](https://docs.cloud.google.com/run/docs/managing/revisions),
[Cloud Run pricing](https://cloud.google.com/run/pricing),
[load-balancer pricing](https://cloud.google.com/load-balancing/pricing) and
[registry pricing](https://cloud.google.com/artifact-registry/pricing).

### Free-trial limit and billing checks

Billing is enabled and linked. **Trial versus paid status, remaining credit, expiry
and actual invoice spend were not verified.** Reading budget metadata returned
HTTP 403; this does not prove that no budget exists. No permissions or APIs were
enabled to work around that restriction.

Google's trial is **$300 credit for 90 days** for eligible new users. It can end
earlier if credit is exhausted; it is not a promise of unlimited service for three
months. An unupgraded trial stops rather than charging after exhaustion/expiry;
paid-account behavior differs. The owner must confirm account type, remaining
credit and expiry in [Billing Overview](https://console.cloud.google.com/billing?project=saloon-505509).
Do not send payment-card information. See [official trial FAQ](https://cloud.google.com/signup-faqs).
Supabase, Upstash and other providers have separate plans/limits; Google credits do
not establish their free status.

Ordinary alert-only budgets do not stop spending. Current Google documentation also
offers **spend-cap budgets for eligible services including Cloud Run**, but enforcement
is delayed and does not cover every persistent resource/cost. They are not a guaranteed
zero-bill switch for this architecture. No budget or spend cap was created here.
See [alerts-only budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets) and
[spend-cap limitations](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).

### Concrete cleanup proposal and decisions needed

The exact local manifest is `backend/.artifacts/cloud-cost-cleanup-plan-20261023.json`.
It proposes **58 untagged, zero-traffic revision deletions**: 45 production experiment
revisions and 13 older staging revisions. Preserve all four currently tagged production
revisions, immediate pre-hotfix rollback `salon-api-production-00004-nx7`, and the
current staging revision: six definitions total. Refresh references immediately before
any deletion; abort if a candidate gained traffic, a tag or latest-ready status.
**None has been deleted yet.**

Separately propose service minimum **0**, maximum **1** for the production API, keeping
the current normal-traffic revision. This trades idle cost for cold starts and reduced
capacity; it is not a hard spending cap. Preserve the photo candidate at zero traffic.

Approval is requested for that exact revision-pruning/scaling scope. The project
[working standard](../../../.claude/skills/senior-backend-engineer/SKILL.md) says:
“Confirm before deleting, force-pushing, migrating or touching shared state.” Do not
include VM/disk deletion, worker shutdown, load-balancer removal, image deletion,
candidate promotion or a database migration in this approval. Those need dependency/
continuity work first, with their own concrete review.

No additional software installation is needed for the checks and first cleanup step:
gcloud, Docker, Playwright and Android tooling are already available. Manual items are
Billing Overview confirmation, authorized super-admin review/test sessions and the
later clean app release builds. The existing Windows clean-owner-build resource limit
remains documented; no OS setting was changed.

Evidence: `backend/.artifacts/cloud-cost-review-20261023.json`,
`cloud-cost-cleanup-plan-20261023.json` and `client-contract-gaps-20261023.json`.


## 15. Approved revision cleanup completed; API scales to zero

On 23 October 2026 the owner approved the exact section14 plan: delete the 58 listed
untagged, zero-traffic revisions and set production service minimum0/maximum1. The
execution refreshed all service references before starting and before each deletion;
no target had acquired traffic, a tag or latest-created/latest-ready status.

- **58 revisions deleted:** 45 production experiments and 13 obsolete staging revisions.
- **Six saved API revisions remain:** five production (all four tagged revisions plus
  immediate pre-hotfix rollback) and the current staging revision. These are saved
  definitions, not six continuously running instances.
- **Production service scaling is now minimum0 / maximum1.** Service-level flags changed
  this without deploying another revision. An idle API can scale down; subsequent
  requests can have cold-start delay. This is not a billing cap or an instant assertion
  that no runtime instance exists.
- Normal API traffic remains **100%** on `salon-api-production-gallery-20261022`.
  `salon-api-production-photos-20261023` and its `photos-review` tag remain at **0%**
  normal traffic. All tagged revisions and `salon-api-production-00004-nx7` were preserved.
- No VM/disk/worker/database/registry-image/load-balancer/DNS change, traffic promotion,
  migration or new installation occurred.

Fresh postchecks verified the exact retained revision sets, minimum0/maximum1,
unchanged traffic, and HTTP200 for process/database/Redis health and OpenAPI on both
the normal domain and the candidate. Both contracts still expose138 operations.
Older min1/max3 inventory and prepared-only notes above are historical snapshots.
Do not reapply pre-cleanup service manifests: regenerate from current metadata so a
future deployment preserves the newly approved scaling settings.

### Trial balance supplied by the owner

The owner reported **Free Trial**, **84 days remaining**, and **₹28,127 remaining out
of ₹28,797**, as viewed in Billing Overview on 23 October. The difference is ₹670 of
the reported credit balance; it is not evidence of a card charge or an independently
retrieved invoice. This is owner-confirmed console information, not an API-verified
billing balance. No billing upgrade, relink, budget or spend cap was made.

Credits and remaining days can expire separately; consuming the balance earlier can
end the trial before84 days. The running VM, continuous notification worker, current
load balancer, stored images and other providers' plans remain cost drivers. This
cleanup reduces idle API provisioning and revision clutter; it does not guarantee
three months of zero resource costs or unlimited use. The remaining dependency and
business-acceptance gates from sections13–14 still apply.

Evidence: `backend/.artifacts/cloud-cost-cleanup-execution-20261023.json` and
`cloud-cost-cleanup-verification-20261023.json`; the original exact approved manifest
is retained as `cloud-cost-cleanup-plan-20261023.json`.

## 16. Test salon approved; customer phone discovery verified (23 October)

Scope is now the existing owner and customer apps. The super-admin interface remains
under development and was not included in this acceptance check.

The owner explicitly requested approval of the salon confirmed on the connected
phone. A guarded trusted-maintenance update changed exactly one active, completed,
pending salon to approved at **22 October 2026 20:11:59 UTC**. No account role was
changed and no administrator identity was impersonated. `approved_by` remains NULL;
the normal approval use case and its push notification were bypassed. This verifies
the requested maintenance approval, **not** the super-admin API or UI workflow.
Existing row audit metadata does not identify the maintenance operator.

After refresh, the owner app showed the live workspace. Its existing staff member
had no service assignment. Assigning the existing service through the owner app
made it appear in the public services API. Other pending salons were untouched.

The updated customer verification APK was installed with the normal app entry point
and live API configuration, retaining app data. On the connected Android phone:

- The salon **Mentrex** appeared in the customer salon list with its uploaded cover.
- Its detail screen displayed **Buzz cut, INR 100, 60 minutes**, retained the category,
  and displayed a two-slide counter without the removed description content.
- Booking date selection loaded the assigned staff member and available times for
  **24 October 2026**. The database availability function independently returned ten
  slots for that date. An initial empty screen during loading was not treated as a
  confirmed scheduling failure.
- After the user selected the dedicated customer account and entered its contact
  details, a **Pay at salon** booking was submitted through the customer app. The
  database stored it as pending; the owner app received a new-booking notification
  and displayed it under the selected appointment date.
- Owner approval changed it to confirmed. The customer app received the confirmation
  and displayed **Booking Approved**, still **unpaid**.
- Customer cancellation through Manage Booking succeeded. The database confirmed
  cancelled/unpaid, and availability returned to ten slots.
- A replacement request exercised owner rejection. The customer app displayed
  **Booking rejected** with the entered test reason. Final database state: one
  cancelled and one rejected test booking, both unpaid; no test appointment remains
  active. QR check-in, collection and service completion are not claimed.

### Owner approval-control rendering fix

The live phone exposed an invisible Approve control: accessibility still identified
it and the API action worked, but its fill/layout were missing. The affected controls
used function-valued inline styles through the installed NativeWind interop runtime.
The scoped correction gives Approve and Decline static native styles while retaining
disabled opacity, accessible labels and existing callbacks. No authorization or
phone-verification rule was changed. The phone then visibly rendered the black
Approve button and outlined red Decline button, and rejection worked through it.

Changed source is in the separate owner repository:
`src/features/bookings/screens/BookingsScreen.tsx`. Its component suite passed
**22/22 tests**; the native bundle export, APK signing verification and installation
succeeded. The test launcher subsequently failed while printing a Unicode checkmark
under Windows CP1252; the saved Jest result itself reports all tests passed. The
mechanical UI detector returned no findings. Private native before/after evidence
is retained; source and phone checks, not the detector, establish the rendering fix.

This is a verification APK assembled from compatible existing native components,
not a clean release/store build. Neither app is yet certified fully complete.
The photo/description API candidate still has zero normal traffic; the reviewed
migration and production promotion have not been performed. Normal production still
returns legacy gallery references, whereas the candidate limits its response to a
separate cover and two slides. The new customer UI limits its displayed slides.

Private local evidence: `backend/.artifacts/customer-owner-live-20261023/`, including
`customer-salon-visible.png`, `customer-service-visible.png`,
`customer-slots-visible.png`, `customer-booking-approved.png`,
`customer-booking-cancelled.png`, `owner-approval-controls-fixed.png`,
`customer-booking-rejected.png`, `owner-actions-tests.log`, `customer-live.apk` and
`owner-corrected.apk`. Public API checks before the
staff assignment are separately retained and must not be mistaken for the later
successful service response.

### Cloud and billing screenshots: interpretation and manual action

The supplied overview lists **four resources**, not five running API instances:

| Resource | Meaning and current decision |
| --- | --- |
| `salon-api-production` | Required live API; preserve minimum 0 / maximum 1 settings. |
| `salon-prod-notifications` | Background notification worker; currently provisioned at one worker, so preserve until notification continuity is reviewed. |
| `salon-api-mumbai-staging` | Separate test API; keep during current verification. |
| `salon-production-db-check` | Diagnostic job definition; inspected executions were successful and finished, not running instances. Potential later cleanup after dependency review. |

The chart covers seven days and does not establish an instantaneous instance count.
The five retained production revisions in section 15 are saved versions. No further
resource deletion, worker shutdown, traffic change or billing change was made in
response to these screenshots.

Billing screenshots show **Free trial**, **84 days remaining**, and an expiry of
**15 January 2027**. Displayed credit differs slightly between the header and cards
(approximately INR 28.1K); these screenshots are not an independently retrieved live
balance. The displayed INR 0 total is after savings/credits and does not mean the
resources consume no credit.

**Manual action:** Billing Overview explicitly warns that an administrator must
**Verify account** to avoid losing access. Complete that verification in the Google
Cloud console; this is distinct from upgrading the trial. No upgrade was requested
or performed. No additional software installation is currently required for testing.

## 17. Staff simplification, category defect and skill routing (23 October)

The owner requested continued verification of both apps, removal of staff experience
entry, standard role labels and custom professional role names. The owner app now:

- Omits experience from onboarding, Add/Edit Staff, expanded staff details, search
  and staff save payloads. This request removed the UI option; no database column or
  previously stored experience value was deleted.
- Shares role choices between onboarding and staff management: Barber, Senior Barber,
  Junior Barber, Stylist, Senior Stylist, Junior Stylist, Master Barber, Colorist,
  Nail Technician, Beautician, Massage Therapist, Salon Manager and Receptionist.
- Accepts a custom role name through the existing `specialization` API field. This
  is a professional title and grants no account permissions. A custom test title was
  saved through the phone, confirmed in Postgres, then restored to the original title
  through the phone. Experience remained NULL for that test staff member.

The updated verification APK is installed. The staff form visibly omits experience;
the role picker and saved custom role were checked on the physical Android phone.
Onboarding and booking component suites passed **50/50**, targeted ESLint passed,
and the mechanical UI detector returned no findings. Full owner TypeScript remains
blocked by previously recorded `src/lib/validation/booking.schema.test.ts` contract
expectations; the current check reported no staff-change type error. These are not
clean release builds or proof that every app screen has passed.

### How customer home categories actually work

Hair Cutting calls `GET /v1/salons?category=Hair%20Cutting` (alongside other active
discovery parameters). The filter concerns the salon's service offerings. The
business-profile category badge is a separate label.

Live checking exposed a mismatch: the test service has displayed category
**Hair Cutting**, backed by a shared **General** category/subcategory. Production
filters only the shared category, so the salon appears under All Services but not
Hair Cutting. This is a confirmed defect, not a phone installation problem.

The local repository query now matches the same effective service category that
public service responses display (`coalesce(category_name, shared category name)`)
and requires an active service assignment to active staff in the same salon. Active
shared category/subcategory checks remain. No catalog records or salon labels were
rewritten. Five regressions failed before this correction and pass afterward,
covering normal/nearby discovery and missing/inactive staff assignments.

The full backend suite passed **1,270 tests / 94 skipped** in **48.74 seconds**;
Ruff passed. This invocation did not enable optional PostgreSQL integration suites;
it must not be equated with the earlier opt-in run. The category regressions execute
the repository query through the SQLite compatibility harness. The corrected
predicate was also checked read-only on Postgres against the test service; that is
not a deployed FastAPI verification.

**Historical status before approval (superseded by section 19):** this category correction had not been published to Cloud Run.
The existing zero-traffic photo candidate does not contain it. Normal traffic and
the previously held migration remain unchanged. A fresh reviewed candidate is
needed before release approval and a final live category/phone check.

### Persistent task-based skills

One shared routing guide, `docs/agent-skill-routing.md`, is referenced by the backend,
owner and customer repositories' AGENTS.md instructions. It selects installed skills
by the current task (API, Supabase/Postgres, native UI, app tests, booking, media,
deployment), including later user updates. No duplicate skill/plugin installation
or global account setting was introduced. Future chats must load those project
instructions; this is not evidence that a fresh Codex session has already tested
discovery. Owner legacy `ctx` is unavailable; the instructions use existing repository
memory as the fallback instead of requiring an unrelated installation.

Private evidence: `backend/.artifacts/customer-owner-live-20261023/`, including
`owner-staff-no-experience.png`, `owner-custom-role-saved.png`, `staff-tests.log`,
`staff-lint.log`, `staff-types.log`, `category-live-check.json` (records the failing
old production behavior), and `category-backend-{before,after,lint}.log`.

### QR download continuation

The owner QR modal rendered successfully. Downloading originally requested music/
audio access because it requested every media permission, and used the deprecated
SDK 57 `saveToLibraryAsync` export. The scoped app fix requests write-only photo
access and uses `MediaLibrary.Asset.create`. The revised dashboard regression checks
both. Dashboard/onboarding/booking suites passed **73/73**, targeted ESLint passed,
and the rebuilt APK was installed. The physical phone then displayed **QR code saved!**
without an audio permission prompt; evidence is `owner-qr-saved.png` in the same
private artifact directory. No new package or native permission was added.

The QR targets the web booking journey. The customer app's current navigation does
not implement a dedicated QR scanner screen; QR rendering/download is verified here,
not an entire native customer QR booking or web acceptance journey.

## 18. Category-only release candidate prepared; approval pending

This is the pre-approval snapshot. Section 19 records the subsequent approved release.

A separate **one-file** hotfix is built locally as
`salon-api-category-review:20261023`, based on the immutable working gallery release.
It changes only the category predicate and active staff-assignment check in
`infrastructure/db/repositories/platform_repository.py`. It does not combine the
held photo/description release, new endpoints or migrations.

- Local image manifest-list digest:
  `sha256:fc21dca55ae768b3c2d59bcf87f9a911daf3382966e7d2e0d8d0fb132bbdbbfc`.
- Patched repository SHA-256:
  `818da97f2d56e0d819a6366fe901b486dfee92b63891714178de4d5b5624da6f`.
- Tests imported the actual isolated candidate and passed **5/5**. Its OpenAPI and
  offline container smoke check expose **138 operations**. The container file hash
  matches the manifest. The corrected predicate also matches Hair Cutting, and not
  Beard Care/Facial, in a read-only PostgreSQL check against the test service.
- A fresh production read still shows **100% normal traffic** on
  `salon-api-production-gallery-20261022`. Maximum instances remains **1**; the
  service minimum annotation is omitted (default zero). Existing photo-review and
  other tags are unchanged.

The concrete proposed approval is: publish a category-only zero-traffic candidate,
verify health/database/OpenAPI and both matching/nonmatching category results, then
move normal traffic only if those checks pass. Roll back to the current gallery
revision on failure and preserve minimum 0 / maximum 1. No migration, data cleanup,
photo/description promotion, billing, VM or worker change is included.

**No publish, deployment or traffic change has occurred for this candidate.** The
owner has been asked for the scoped release approval, with a zero-traffic-only option.
The prior photo-candidate-only approval does not authorize this new release.

Review evidence is in `backend/.artifacts/category-release-20261023/`:
`manifest.json`, `candidate.diff`, `pytest.log`, the one-file overlay, Dockerfile and
`production-state-before-approval.json`. The image contains the backend only.

## 19. Approved category hotfix released and checked on the customer phone

After explicit approval for the category-only release, a zero-traffic candidate was
published and checked before promotion. Normal production traffic is now **100%**
on `salon-api-production-category-20261023`. Rollback revision
`salon-api-production-gallery-20261022` is preserved. Scaling remains **minimum 0 /
maximum 1**; no migration, billing, VM, worker or resource-deletion change occurred.

The immutable published image is
`asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:fc21dca55ae768b3c2d59bcf87f9a911daf3382966e7d2e0d8d0fb132bbdbbfc`.
It contains only the reviewed one-file overlay over the working gallery image.

**All 11 candidate checks and all 11 production checks passed:** API/database/Redis
health, unchanged full OpenAPI contract (138 operations), Swagger UI, matching Hair
Cutting discovery, nonmatching Beard Care/Facial/General discovery, public service
category consistency and nearby category discovery. The publication receipt is
`backend/.artifacts/category-release-20261023/publication.json`.

On the physical Android customer app, selecting Hair Cutting now shows **Mentrex**.
Selecting Beard Care shows the empty state, consistent with its offered service.
The filter was restored to Hair Cutting. Additional native checks added Mentrex to
Favorites, opened the saved salon list, then removed it and verified the empty state.
The test favorite was not left behind. Screenshots are in
`backend/.artifacts/customer-owner-live-20261023/`:
`customer-hair-category-live.png`, `customer-beard-category-live.png`,
`customer-favorite-added.png`, and `customer-favorite-removed.png`.

Current client verification includes the approved test salon, service/staff/slots,
customer booking request, owner confirmation, customer cancellation, owner rejection,
custom staff title save/restore and owner QR image download. Both test bookings remain
terminal and unpaid. Staff experience prompts are removed in the installed owner
verification build; staff titles use the existing specialization API field.

**Still pending:** full QR target/check-in, collection/completion, remaining screen
acceptance, unavailable API families recorded in section 14 and clean release builds.
Owner full TypeScript still has the previously recorded booking-schema test errors.
The photo/description candidate remains at zero normal traffic and revision 0041
has not been applied. Those changes are not part of this category release. No claim
of complete API wiring or full application acceptance is made. No additional package
installation or manual sign-in is needed for the checks completed in this section.

Frontend connection URLs remain:
- API base: `https://apiv1.mudassirmhd.in` (routes under `/v1`).
- Swagger: `https://apiv1.mudassirmhd.in/docs`.
- OpenAPI: `https://apiv1.mudassirmhd.in/openapi.json`.

## 20. Customer/owner cache and salon-screen blinking correction (23 October)

Scope: the customer and owner clients only. No API implementation, Cloud Run
configuration, Redis settings, database records or migration changed in this work.
The category production release in section 19 remains the deployed backend.

### Confirmed causes

- Customer `SalonDetailsScreen` returned its full-screen skeleton whenever the
  detail query was fetching, even with successful cached data. Default 30-second
  salon polling therefore unmounted the content/gallery repeatedly.
- Customer discovery hid its cached list during every background read. Foreground
  handling reset public queries, and mount/focus/reconnect options forced reads
  despite fresh data. Opening-hours badges also fetched a separate detail per card.
- Owner defaults marked all reads immediately stale. Stable staff/service/setup
  resources polled every 30 seconds, and route changes invalidated nearly every
  non-auth query. An unchanged booking poll invalidated five dependent resources.

### Applied client behavior

| Data or event | Current policy |
| --- | --- |
| Customer salon lists/details/services/staff | 60-second freshness; reuse on immediate navigation; stale mount/foreground/reconnect reads run in the background |
| Customer detail screen | Skeleton only for initial missing data; successful content stays mounted during background reads |
| Customer opening-hours badges | Observe the shared detail cache; no detail request per card; retain local minute clock |
| Customer cover/gallery | Installed `expo-image` component with explicit memory/disk cache and no image transition fade |
| Owner services/staff | 60-second freshness, existing account-scoped persistence, mutation invalidation; no periodic setup polling |
| Owner route/reconnect | Invalidate live operational resources, preserving fresh setup caches |
| Owner unchanged booking poll | Skip dependent invalidations when TanStack structural sharing reports unchanged data |
| Both clients' ordinary query defaults | 30-second freshness; stale-only mount/focus/reconnect behavior |
| Booking availability | Existing staleTime 0, 10-second foreground polling and server authority preserved |
| Owner booking feeds | Existing route-aware operational polling preserved |

Manual refresh and mutation invalidation remain available. A forbidden/not-found
salon detail still removes that salon from cached discovery and removes its service/
staff entries. Failed list reads still suppress the list. There is no permanent
offline approval, permission, price or availability guarantee. No new personal data
was added to disk persistence; customer salon visibility is still revalidated after
process restart rather than restored from an old disk snapshot. The existing owner
snapshot remains user/salon scoped and expires after 24 hours. No new image package
or native dependency was installed.

### Measured API and photo behavior

Three sequential requests per endpoint from this workstation, against the existing
public production API, returned 200:

| Endpoint | Observed range | Body size |
| --- | --- | --- |
| Salon list (`limit=10`) | 162-174 ms | 774 bytes |
| Test salon detail | 168-187 ms | 3,861 bytes |
| Test salon services | 174-181 ms | 364 bytes |
| Test salon staff | 173-191 ms | 112 bytes |
| Redis health | 146-180 ms | `status=ok`, `redis=reachable` on all three |

These are warm end-to-end workstation samples, not phone latency, load testing,
server-only timings, a cache-hit ratio or a p95/SLA. Redis reachability does not
prove every endpoint is served from Redis. The client fixes reduce calls before
they reach either Redis or Postgres.

Public image samples were JPEGs of 229,884-335,201 bytes (about 225-327 KiB), with
no Cache-Control header on those sampled responses. One initial default Python
request returned 403; the recorded run with an explicit verification User-Agent
succeeded. Existing owner upload processing already downsizes salon images to at
most a 1600-pixel edge and a 1 MiB byte budget. Photos were not re-uploaded, degraded
further or deleted. The held legacy gallery cleanup is separate from this fix.

GET requests consume bandwidth, processing and potentially logging; they do not
create another stored salon photo on each read. JSON metadata caching and native
image disk caching serve different purposes. Existing process/device cache limits
still apply; this work does not claim that all cache storage has a new hard byte cap.
Cloud Run minimum 0 remains unchanged, so an initial request after an idle period
can still incur a cold start. This work makes no promise of zero latency or cost.

### Verification and delivery

- Four new customer and two new owner regression checks failed before correction.
  The repeat-navigation test previously made two detail requests; it now makes one
  detail/service/staff request each across prefetch, first open and immediate reopen.
  The card badge regression now makes zero detail requests. An unchanged owner
  booking response previously caused five invalidations; it now causes zero.
- **35 customer tests passed** across eight suites, including rendered content
  during background reads, denial removal, manual refresh, disk privacy and booking
  freshness. **27 owner tests passed** across six suites, including lifecycle,
  polling, persistence, staff and mutation behavior.
- Targeted ESLint passed for both apps. Customer TypeScript passed. Owner TypeScript
  still reports only the previously recorded `booking.schema.test.ts` contract
  expectations; a clean owner typecheck/release gate is not claimed.
- Both normal app entries were rebuilt as local verification APKs with the existing
  native bases, signed, verified and installed with app data retained. These are
  verification builds, not clean native/store releases or production OTA publication.
- Physical phone checks exercised customer first/repeat salon navigation and a
  35-second dwell, plus owner dashboard/staff repeat navigation. Sampled screens
  retain populated content; the early customer repeat sample shows the normal native
  slide transition with populated content rather than a skeleton. The customer
  interaction was recorded. No frame-rate improvement percentage, full video-frame
  audit or all-screen acceptance claim is made.

Evidence: `backend/.artifacts/app-cache-20261023/`, including before/after test logs,
lint/typecheck logs, `public-api-measurements.json`, both APKs, customer navigation
screenshots/recording and owner dashboard/staff screenshots. Functional work still
pending in section 19 remains pending; this performance correction does not complete
QR/check-in, collection/completion, missing API families or the held photo migration.

Library references: [TanStack freshness/refetch defaults](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults)
and [Expo SDK 57 image caching](https://docs.expo.dev/versions/v57.0.0/sdk/image/).

## 21. Owner unread bookings, date/source indicators and live badge check

The owner requested that the dock badge decrease when bookings are read and increase
for new bookings, with clear markers identifying the appointment date and booking
source. The owner explicitly chose **read when the card appears**, rather than read
only after tapping a card. This work changes the owner client only and reuses existing
notification and booking APIs. No backend release or schema change is involved.

### Corrected behavior

- The dock counts **distinct booking IDs with server-unread notifications**. It no
  longer uses the maximum of pending approvals and notification count. Multiple
  notifications for one booking count once; pending approval remains a separate
  status/filter and does not make a seen booking unread again.
- The focused, foreground bookings page acknowledges only bookings displayed by its
  current date/source/status filters. Hidden bookings and general notifications
  remain unread. Late-loaded notifications are handled after loading; merely
  prefetching or mounting an inactive page does not acknowledge them.
- Each acknowledgement carries immutable notification IDs selected before the
  optimistic cache update. A later notification is not accidentally included.
  Failed batches roll back only their affected read flags, preserve later arrivals
  and reconcile with the server; they do not retry in a render loop.
- Newly displayed cards retain an accessible **dot + New** cue for the current
  visit, even after acknowledgement clears the unread count. The cue resets when
  the owner leaves the page. It is a visual indication of a newly seen update,
  separate from the server's now-read state.
- Cards explicitly show **Today**, **Tomorrow** or the appointment date, and
  **App**, **Manual walk-in** or **QR walk-in**. Appointment time/status markers
  wrap rather than depending on a single crowded row.
- A **New booking updates** shortcut shows each unread appointment's date, time
  and source. It selects that exact day/source and the pending filter when relevant.
  This makes future requests accessible even though the default view requests only
  today's bookings. Calendar controls indicate new dates; view/source controls show
  unread dots. Terminal updates point to History as appropriate.
- Date/source lookup fetches only distinct unread booking IDs through the existing
  owner-scoped repository, using a salon- and notification-batch-scoped query key,
  60-second freshness and no interval polling. A new notification batch gets current
  metadata even for the same booking. Loading/errors remain visible with retry.

### Verification and limits

Four badge regressions failed before correction. The final focused run passed
**39 tests across five suites**, covering distinct counts, selected reads, arrivals
during acknowledgement, failed acknowledgement, focus/background protection,
late-loading data, current-visit markers, date/source navigation, next-month QR,
today's manual walk-in and unread history. Targeted ESLint and whitespace checks
passed. The UI detector reported no findings. Owner TypeScript still has the existing
`booking.schema.test.ts` contract-expectation errors; a clean owner release gate is
not claimed. CodeGraph was attempted first, but its MCP connection was closed and
its CLI could not open the index; investigation continued through current source.

Physical phone evidence confirmed:

1. The old badge displayed three notifications for two bookings. The corrected
   build displayed **2** distinct unread bookings.
2. Displaying the two historical bookings cleared the dock badge; both showed
   the current-visit New marker.
3. One dedicated test customer request for **24 October 2026, 09:00 salon time**
   increased the live dock badge to **1**. No payment was recorded.
4. The extended page showed **Tomorrow · App · Sat, 24 Oct · 9:00 AM**, an App
   unread dot and a new-date indication while the request was outside today's list.
5. Selecting its date displayed the future appointment, cleared the dock badge,
   retained the New marker and left **Awaiting approval** unchanged. This establishes
   that reading and approval are separate operations.

No foreground push latency SLA or every-device/store-build claim is made. The live
test checked the existing server notification flow and phone views; source-specific
manual/QR and next-month cases were covered in component tests without creating
additional appointments.

**Continuation completed (23 October):** after exclusive phone control was restored,
the dedicated unpaid request was cancelled through the customer app. Its confirmation
states that the slot is available again. The final badge APK was installed successfully.
The cancellation created one unread owner update; opening its date displayed the
cancelled card with a New marker and cleared the badge. A force-stop/restart then
showed the owner Home screen with no booking badge. Reading did not approve or charge
the booking. Screenshots: `cleanup-confirmed.png`, `final-cancellation-read.png` and
`final-restart-read-persisted.png` in the evidence directory below.
Private state/evidence: `backend/.artifacts/booking-badge-20261023/`, including
`live-test-state.json`, test/lint/type logs, APK, `before-bookings.png`,
`after-home.png`, `after-history-read.png`, `new-booking-badge.png`,
`unread-date-source.png` and `future-booking-read.png`.

## 22. Business-profile replacement, validation and category continuation

Scope confirmed on 23 October: remove **only the salon business-profile category**
from clients/API/storage; retain shared service categories, subcategories and service
display labels. This supersedes the earlier instruction to retain that salon field.

### Reproduced cause and source correction

The public test salon returned eight legacy image records: one cover, five slides at
sort order zero and two at order two. The editor previously reassigned a replacement
to its visible slot number and appended it to the local list. Replacing Slide 2 therefore
moved it behind older order-zero records, outside the two visible slides. A successful
PATCH could save the photo while the screen displayed a different legacy record.

The owner editor now preserves a replacement's existing sort order and list position,
and rejects a response that does not match the requested URL/role/order. This requires
no production migration. Two focused regressions fail under the previous logic.
Native acceptance subsequently passed: the user selected a distinct Slide 2 photo,
the owner app saved it, and reopening showed that photo as Saved. The same slide
record retained its order. The updated customer app then displayed the new photo
in its salon carousel. Evidence: `backend/.artifacts/profile-media-20261023/`.

Subsequent local verification: **72 owner tests passed across five suites**, including
the photo editor, Settings, salon repository, profile completion and fallback checklist.
Both new photo regressions fail with the previous save logic. **35 customer tests passed
across eight suites**, and customer TypeScript passed. The updated owner JavaScript bundle
exported successfully; the profile verification APK was subsequently packaged and
installed on the test phone. The customer verification APK was also updated.

Owner profile saves require the existing name, owner name, valid contact and location,
plus a cover and at least one service-page photo. Slide 2 remains optional; maximum
two slides plus the separate cover. Removed descriptions/category are not required.
The API rejects explicitly supplied null/empty/whitespace salon name/address/city and
profile name while preserving omitted fields for partial updates. Input checks do not
prove a business is genuine; admin review remains a separate gate.

### Category removal and release boundary

Compatible owner source no longer sends/requires category; customer profile tags and
mapping no longer use it. Shared catalog filtering remains based on service categories.
Backend response/request models, setup checklist and SQL projections remove the field.
Prepared migration `0042_remove_business_category` follows held `0041`; it uses bounded
lock/statement waits and `DROP COLUMN … RESTRICT`, never CASCADE. It is irreversible
and does not remove service taxonomy or platform records.

The actual 0042 upgrade passed in a newly created disposable local PostgreSQL database:
dependent-view refusal/rollback, preservation of service category/subcategory values,
repeat execution and explicit irreversible downgrade. No remote migration was applied.
Review identified and corrected statement splitting for asyncpg and owner-client
compatibility. Updated apps/readers must be distributed before response removal and
the explicit database drop; the working production revision still selects category.
Do not run the drop against production while those readers remain active.

Final backend verification including the profile-name guard: **1,285 passed, 95 skipped**
in 127 seconds; Ruff passed with its unwritable cache disabled. Skips include opt-in
integration suites. One dependency deprecation warning remains.

### Newly confirmed booking/payment requirements

The user's detailed cancellation/refund and admin-approved settlement policy is recorded
as the latest U08 amendment in `payment-subscription-booking-spec.md`. It supersedes the
earlier exactly-four-hour boundary and unresolved flat deduction. These payment/booking
changes are **requirements, not a released capability**. Current live cancellation still
uses the older cutoff/action-request behavior, and online payments remain dormant.
No provider settlement, refund, billing or production release occurred in this continuation.

## 23. Resumed native notification verification

The user resumed after the requested 2:28 PM pause. Approval review became available,
and exclusive phone control was confirmed. Both profile verification APKs were installed.
The user selected the replacement photo; owner save/reopen and customer display passed.
Customer profile freshness remains the accepted 60-second cache plus reopening/manual refresh.

Owner **Alerts & activity** now uses customer-aligned image cards, separate content/dismiss
touch targets, readable body text and reduced-motion-aware entry/exit/layout animations.
The source passed **18 tests across four suites** and focused lint, including independent
dismissal and push routing. The full native release-mode verification APK subsequently
built successfully (including Android release lint) and installed over the existing app.
It is signed with the existing debug certificate for local verification, not store release.
After the user unlocked the phone, the new cards rendered with their matching image
icons and without the old overlapping tinted blocks. Opening details and independently
dismissing a dedicated test alert passed on the phone. A fresh foreground test message
also displayed its full in-app heads-up banner; this establishes presentation alongside
provider acceptance, without attributing the banner exclusively to FCM rather than inbox sync.
The native build encountered a stale Windows dependency-cache path exceeding 260 characters;
removing only its generated Ninja dependency file allowed that compilation step to pass.
Google Maven DNS then blocked an AndroidX artifact; Java HTTPS connectivity was checked
before retrying the cached build successfully. The low local Gradle heap/metaspace settings
also caused a memory-pressure warning. No Cloud Run capacity was changed for this build.

Live checks use only guarded system-notification fixtures for the existing owner/customer
test accounts, through the existing outbox and notification worker. They create no booking
or payment. Neither raw tokens nor provider credentials were read or published.

| Installed app/state | Physical evidence | Result |
| --- | --- | --- |
| Customer foreground | Exact test push in Android tray; tap opened Notifications | Passed |
| Customer background | Exact test push in Android tray; tap opened Notifications | Passed |
| Customer process terminated | PID absent before sending; exact push arrived; tap cold-launched Notifications | Passed |
| Owner background, earlier installed build | Exact test push in Android tray | Receipt passed; tap incorrectly opened Home |
| Owner foreground, earlier installed build | Inbox/bell updated; recording not inspected | Physical foreground FCM presentation not yet established |
| Owner foreground, final installed build | Exact test message displayed in heads-up banner; provider accepted | Presentation passed; banner may also be driven by inbox sync |
| Owner background, final installed build | Exact push in Android tray; tap opened Alerts & Activity | Passed; route correction verified |
| Owner swiped out of Recents, final installed build | Task removed; exact push arrived; tap reopened Alerts & Activity | Passed; cached process remained alive |

The owner tap fallback was corrected to Alerts for notices without a booking; booking
notices still route to Bookings. Its regression failed before the fix and passed after.
That correction is installed and the live background/swipe-away tap retests passed.
Customer registration was
also corrected to create the backend's `salon-alerts-v3` Android channel rather than only
`default`; **17 tests across three suites** and focused lint passed, and this fix is installed.

Provider acceptance is checked separately from physical receipt. The fixture named
`customer-closed-01` ran while a PID still existed and counts only as background evidence;
`customer-process-stopped-02` is the valid process-termination check. This does not test
Android force-stop, owner process termination, every device, audible sound or iOS delivery.
All **nine** guarded test notices were processed and accepted without a provider error.
The final owner Read all action cleared its three new test notices and the visible count
fell to zero. One older test alert was hidden from this device while verifying dismissal;
server notification records were retained. No test booking or payment was created.
The initially missed swipe-away tap is not a passing artifact: `owner-swiped-tap.png`
shows the customer app. A fresh notification UI hierarchy supplied exact bounds, and
`owner-swiped-tap-verified.png` plus foreground package confirmation establish the pass.
Evidence remains private
under `backend/.artifacts/{owner-alerts,customer-push}-20261023/`.

No new backend revision, remote migration, settlement/refund operation or cloud resource
change was made during this resumed verification. Broader booking/QR/completion acceptance
and the U08 payment implementation remain separate, unfinished work.
