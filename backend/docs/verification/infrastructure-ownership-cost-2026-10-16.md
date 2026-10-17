# Infrastructure ownership and cost audit — 16–17 October 2026 (IST)

Read-only infrastructure inspection of `saloon-505509`, captured at approximately
00:16 IST on 17 October 2026 (refreshed after study completion). The natural
cold-start study completed twenty trials without changing Cloud Run configuration. No cleanup command below has been executed.

## What the current work is doing

The current work **tests the existing Mumbai staging Cloud Run service**. It does
not create services/repositories/secrets, deploy revisions, change billing, or replace the VM. Earlier
authorized work created the staging service, repository, dedicated runtime identity,
and four staging secrets. The current investigation reuses them.
Cold HTTP requests cause Cloud Run to start temporary runtime instances through
normal autoscaling; those instances are the subject of the timing test and can
incur request-based compute charges. No persistent infrastructure is provisioned
by the current investigation.

The active CLI identity is `7alonbooking@gmail.com`. This is the inspecting identity;
it is not a claim about legal ownership of the GCP or Upstash account.

## Verified inventory

| Resource | Verified state | Ownership / purpose |
| --- | --- | --- |
| Cloud Run `salon-api-mumbai-staging` | `asia-south1`; staging label; only service returned by project-wide list | Approved staging experiment |
| Serving revision | `salon-api-mumbai-staging-cold19-20261016`, 100% traffic | Existing revision reused unchanged |
| Runtime identity | `salon-api-mumbai-staging@saloon-505509.iam.gserviceaccount.com` | Dedicated staging service account |
| Staging Artifact Registry | `salon-mumbai-staging`, `asia-south1`, 124,760,032 bytes | Staging image storage |
| Other Artifact Registry | `salon-backend`, `australia-southeast1`, 125,074,144 bytes | Existing resource; consumer ownership unverified; preserve |
| Compute Engine VM | `instance-20261009-141410`, `us-central1-a`, `RUNNING`, `e2-medium` | Existing production entry point |
| VM boot disk | Same name, 10 GiB `pd-standard`, attached and READY | Existing VM resource; preserve |
| VM public IPv4 | `35.254.254.227` | Current production DNS target |
| VM identity | `283739091709-compute@developer.gserviceaccount.com` | Different from staging runtime identity |
| Reserved addresses / forwarding rules / Cloud DNS zones | Each project-wide list returned empty | The attached public IP still exists; an empty reserved-address list does not mean no IPv4 cost |
| Mumbai Cloud Run domain mappings | REST list HTTP 200, empty items | No custom-domain mapping on the inspected staging region |

Cloud Run remains min **0**, max **1**, **1 vCPU / 512 MiB**, concurrency **8**,
request-based CPU allocation, startup CPU boost disabled. The service invocation
policy explicitly grants `roles/run.invoker` to the tester account and does not
grant `allUsers` or `allAuthenticatedUsers`; inherited IAM was not exhaustively
audited. Its image is pinned to an immutable digest:

```text
asia-south1-docker.pkg.dev/saloon-505509/salon-mumbai-staging/api@sha256:38ff423fbde6697e71a720c6f0506b0c0ec99ef0a80d8e11006bea9c2ad6b2a2
```

The four Secret Manager secrets have label `environment=staging`, one enabled
version each, and user-managed replication in `asia-south1`:

- `salon-mumbai-staging-database-url`
- `salon-mumbai-staging-redis-url`
- `salon-mumbai-staging-supabase-anon-key`
- `salon-mumbai-staging-supabase-service-role-key`

Only names/version metadata were inspected. No secret payload was accessed for
this audit. Container scanning reports `SCANNING_DISABLED`; this audit did not
enable scanning or any API.

## VM and production path

`apiv1.mudassirmhd.in` currently resolves directly to **35.254.254.227**, matching
the running VM. `.github/workflows/backend.yml` identifies that same HTTPS domain
as the production environment and explicitly names its deployment job
`Deploy production VM`. `backend/docs/CI_CD.md` records the same VM IP.

```text
Observed production entry:
production API DNS → 35.254.254.227 → instance-20261009-141410 (us-central1-a)

Observed staging entry:
IAM-authorized tester → salon-api-mumbai-staging*.run.app → cold19 revision
  → configured Mumbai Supabase + existing TLS Upstash Redis
```

The VM's last start is **9 October 2026, 19:46:03 IST**. Compute instance audit
metadata for the inspected preceding 24 hours returned no instance operations.
No command in this investigation modified, restarted, stopped, SSHed into, or
redeployed the VM. Audit absence and the last-start timestamp do not prove that
another actor made no changes inside the guest over SSH.
`RUNNING` is the VM control-plane state; guest Docker/container health and the
complete production application flow were not inspected or asserted healthy.

Cloud Run has no observed production domain mapping or load-balancer forwarding
rule. Its 634 returned HTTP log entries in the inspected 24-hour window contain
only `/health`, `/health/db`, `/health/redis`, `/`, and `/favicon.ico`; no business
API path was observed. This supports the staging-only interpretation. It does
not prove every caller's intent or inspect external frontend configurations.

**Cloud Run has not been established as a replacement for the VM.** Production's
public entry is verified as the VM. The VM's reverse-proxy upstream and runtime
environment were intentionally not read, so an internal forwarding dependency
cannot be ruled out solely from DNS. No production request was sent for this audit.

## Upstash status and limits of verification

The existing database is user-identified as `salon-mumbai-staging`, Free,
Mumbai / `ap-south-1`, TLS enabled. Current Cloud Run startup logs show successful
Redis connections, including all twenty accepted natural trials. Final IAM checks of `/health`,
`/health/db` and `/health/redis` all returned 200 with status `ok`. Earlier scoped
validation covered TLS, authentication, PING, synthetic command compatibility,
expiry, idempotency and invalidation. This audit does not repeat writes.

No Upstash account-management credentials or provider plan/region metadata are
available to this audit. **Free plan and Mumbai region remain user-confirmed,
not independently reverified account metadata.** No upgrade or new Redis database
was requested by the current work. The deployed application uses a Secret Manager
reference; its credential is not printed or copied into this report.

## Cost risk and free allowances

These are USD list-price illustrations before taxes, currency conversion, credits,
discounts and account-wide usage. Actual billed spend and remaining allowances
were not retrieved. Free allowances are shared at billing-account scope and do
not guarantee a zero bill for this project.

| Item | Limit / risk |
| --- | --- |
| Cloud Run request billing | 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests monthly free; Mumbai Tier 1 active rate about $0.0909/hour at 1 vCPU + 0.5 GiB, before allowances |
| Staging test illustration | 20 starts × 15 billable seconds ≈ $0.0076 compute before allowances, plus requests/transfer/logging; actual billable startup/shutdown duration may differ |
| Continuous staging traffic | One fully active instance for 730 hours ≈ $66.36 compute before allowances; max 1 limits instances, not the total bill |
| Artifact Registry | 0.5 GiB-month free per account; observed two repositories total about 0.233 GiB; additional images, other projects and transfer can consume the allowance; excess storage about $0.10/GiB-month |
| Secret Manager | 6 active versions and 10,000 accesses monthly free per account; observed four single-region versions; excess $0.06/version-location-month and $0.03/10,000 accesses |
| Upstash Free | Published Free card/FAQ: 250 MB data, 500,000 commands/month, 10 GB bandwidth; account plan itself remains user-confirmed |
| Existing VM compute | `e2-medium` Iowa on demand ≈ $0.03350571/hour, or $24.46/730 hours; the free VM compute allowance targets `e2-micro`, not this machine type |
| Existing VM IPv4 | Attached standard-VM external IPv4 ≈ $0.005/hour after the one-hour account allowance: about $3.65/730 hours |
| Existing VM disk | 10 GiB standard disk ≈ $0.40/month before eligible disk allowances; disk eligibility/other account usage not determined |
| VM rough subtotal | About $28.51/month compute + IPv4 + disk before allowances, transfer, logging, discounts and taxes; staging deletion does not remove this VM cost |
| Cloud Build | No build is launched by this investigation; published 2,500 promotional free build-minutes/month apply to default-pool `e2-standard-2`, not every machine type |

Scale-to-zero removes the need for a permanently allocated staging instance, but
startup/serving/shutdown work and separate services can still be billed. Neither
deleting a Cloud Run service nor removing a payment method would clean up the
VM's running resources. No billing/payment action was attempted.
Supabase plan, credits, usage and database charges were not audited or modified;
they are separate from Cloud Run allowances and survive staging resource cleanup.

Sources checked for this audit:
[Cloud Run](https://cloud.google.com/run/pricing),
[Artifact Registry](https://cloud.google.com/artifact-registry/pricing),
[Secret Manager](https://cloud.google.com/secret-manager/pricing),
[Upstash](https://upstash.com/pricing/redis),
[VM compute](https://cloud.google.com/products/compute/pricing/general-purpose),
[IPv4](https://cloud.google.com/vpc/network-pricing#ipaddress),
[disk](https://cloud.google.com/products/block-storage),
[Cloud Build](https://cloud.google.com/build/pricing),
[free-tier eligibility](https://docs.cloud.google.com/free/docs/free-cloud-features).

## Cleanup plan — commands for later review, not executed

Wait until testing finishes and preserve the JSON/CSV evidence. Deleting the
following **Cloud Run service itself** removes staging revisions and its URL;
it does not delete a Compute VM, disk, database or DNS record. The inspected
production DNS entry continues to point at the VM. Confirm there is no uninspected
VM proxy dependency before executing cleanup.

```powershell
gcloud.cmd run services delete salon-api-mumbai-staging --project=saloon-505509 --region=asia-south1
```

The repository is separately billed storage. Only after verifying that no VM or
other release consumes this staging repository, its exact cleanup command is:

```powershell
gcloud.cmd artifacts repositories delete salon-mumbai-staging --project=saloon-505509 --location=asia-south1
```

The names/labels below identify staging credentials but do not prove exclusive
use by every possible consumer. Delete them only after checking dependencies;
this audit did not read VM runtime files or other projects. Removing GCP secret
objects does not delete Supabase or Upstash themselves.

```powershell
gcloud.cmd secrets delete salon-mumbai-staging-database-url --project=saloon-505509
gcloud.cmd secrets delete salon-mumbai-staging-redis-url --project=saloon-505509
gcloud.cmd secrets delete salon-mumbai-staging-supabase-anon-key --project=saloon-505509
gcloud.cmd secrets delete salon-mumbai-staging-supabase-service-role-key --project=saloon-505509
gcloud.cmd iam service-accounts delete salon-api-mumbai-staging@saloon-505509.iam.gserviceaccount.com --project=saloon-505509
```

Delete the dedicated runtime identity last, after confirming no remaining workload
uses it. Upstash deletion is optional and requires independent confirmation that
the manually created `salon-mumbai-staging` database has no VM/production consumers.
Its provider database ID was not obtained, so no guessed API deletion command is
provided. Use the Upstash console for the verified database only if separately
approved later.

**Preserve** the VM, its disk/IP/default service account, Sydney repository
`salon-backend`, all Supabase projects, production DNS and frontend configuration.
Never delete the GCP project or disable billing as a staging cleanup shortcut.

## Evidence

Sanitized metadata is saved locally at
`backend/.artifacts/cold-start-investigation/infrastructure-audit.json`.
The audit helper contains only read operations and strips query strings and Redis
connection messages before saving summaries. No secret payloads are recorded.
Cold-start distributions and phase evidence are maintained in
[the startup investigation](cloud-run-startup-investigation-2026-10-16.md).
