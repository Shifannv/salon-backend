# Backend CI and Cloud Run releases on GitHub Free

Canonical repository: https://github.com/Shifannv/salon-backend. Keep the previous
repository as `upstream`; do not rewrite either main history. Production uses
`saloon-505509 / asia-south1 / salon-api-production`. Both https://api.salones.in
and https://apiv1.mudassirmhd.in must continue working. Website API_BASE_URL stays
https://api.salones.in. DNS, TLS, load balancer, scaling and runtime secrets are
outside this change.

## CI

`.github/workflows/backend.yml` runs on pushes and pull requests, and is reusable
by CD; manual CI runs are also supported. Jobs `Lint and tests` and `Build and smoke test image` install declared
requirements, run pip check, Ruff, shell syntax and the full pytest suite with a
disposable PostgreSQL 18 service. It builds backend/Dockerfile using backend/ as
context, validates Compose, and verifies nonroot/custom-port health and worker
imports. Actions are pinned to full commit SHAs. No production credentials are
needed. Tests apply existing prepared SQL only to disposable localhost databases;
the remote migration policy remains unchanged.

The active workflow no longer contains a production VM deployment job or VM
artifact transfer. Historical scripts remain for recovery and must not be run as
normal production releases.

## Local checks required before AI commits and pushes

Every AI assistant must follow the mandatory verification gate in `AGENTS.md`.
From the repository root, with development requirements installed:

```bash
# Linux/macOS, Python 3.12 virtual environment
PYTHON=backend/.venv/bin/python bash backend/scripts/check-ci.sh

# Windows Git Bash, existing virtual environment
PYTHON=backend/.venv/Scripts/python.exe bash backend/scripts/check-ci.sh
```

The script requires Bash, Python 3.12+ (prefer 3.12 to match GitHub), Git and Docker
with Compose. It does not install dependencies. It runs pip check, the workflow's
Ruff command, shell syntax and diff checks, migration-policy tests, the full suite
against a newly created PostgreSQL 18 container, Compose validation, an amd64 image
build and `check-container.sh`. Any failed check stops the script with a nonzero
exit code. Its database uses a random loopback port and is removed with its
anonymous volume on exit. Existing databases and Compose services are not reused.
Application environment files are not loaded. The diagnostic image is retained
with source revision `unknown` because the build includes the working tree.

Rerun after the final code edit; report pass/skip counts and runtime differences.
This preflight cannot establish production schema compatibility or cloud IAM,
activation, quota and network health. After an authorized push, inspect CI for
the exact commit. Review and merge only after green checks. The existing main
workflow automatically releases eligible owner merges after its deployment gates;
new migration differences still need their separately reviewed release procedure.

## GitHub prerequisites

Settings → Environments → New environment → `production`:

1. Select custom deployment branches and add only branch `main`; no tag policies.
2. Add the nonsecret variables below at production environment scope.
3. Do not add GCP JSON keys or application credentials.

The owner explicitly chose GitHub Free and private visibility. Rulesets, branch
protection and required environment reviewers are not relied upon. The production
environment now exists with custom deployment branches. Do not change billing or
visibility, ask for an upgrade, or represent main as protected. Review PRs and CI
manually before merging; deployment remains limited to the exact owner actor.

| Variable | Verified value/status |
| --- | --- |
| GCP_PROJECT_ID | saloon-505509; configured |
| GCP_REGION | asia-south1; configured |
| GCP_CLOUD_RUN_SERVICE | salon-api-production; configured |
| GCP_ARTIFACT_REGISTRY_REPOSITORY | salon-production; configured |
| GCP_WORKLOAD_IDENTITY_PROVIDER | projects/283739091709/locations/global/workloadIdentityPools/salon-github/providers/salon-backend |
| GCP_DEPLOY_SERVICE_ACCOUNT | salon-github-deploy@saloon-505509.iam.gserviceaccount.com |

These identifiers are not secrets. Database URLs, Supabase/JWT/payment/Firebase
credentials remain in Cloud Run/Secret Manager, never GitHub. See the exact
[approved IAM configuration](CLOUD_RUN_OIDC_IAM_PROPOSAL.md). All six variables
are configured and read back in production; its sole allowed branch is main.
The four target identifiers also remain at repository scope with identical values.
No GCP JSON credential or application-runtime secret is stored in GitHub. The obsolete
`PRODUCTION_AUTO_DEPLOY_ENABLED` environment secret may remain, but no active workflow
reads it.

The approved pool, provider, deployment account and four resource-scoped bindings
were created/read back. The account has no user-managed keys or project-wide
grants. Security Token Service API (sts.googleapis.com) is enabled, verified by
read-only inspection on 29 October 2026 after its separately approved activation.
The existing provider permits the reviewed manual candidate path and the exact
`cloud-run-auto.yml` owner/main/push path, and its condition was read back after
configuration. The skipped automatic run did not reach federation; its first live
OIDC exchange remains an observed check for the gate-fix merge. No JSON service-account
key is used. Do not broaden repository, owner, actor, ref, environment, event or
workflow restrictions.

## Automatic releases

The [automatic release guide](CLOUD_RUN_AUTO_DEPLOY.md) describes CI, immutable-image
candidate verification, automatic traffic promotion and health-triggered rollback.
Only production environment variable `AUTO_DEPLOY_ENABLED`, exactly lowercase
`true`, activates release. The similarly named legacy repository variable and secret
are ignored. Feature pushes and pull requests run CI only. An eligible owner-merged
latest-main push must pass both CI jobs and every admission/provenance/migration/
health guard before OIDC authentication and release.

The first supervised Git-proven release completed on 1 November 2026 and established
a healthy labelled baseline plus retained rollback revision. No future migration is
automatically approved: any migration-source difference fails closed pending its own
review, backup and compatibility release.

On 2 November, migrations 0056–0057 and the tested fa82510 API were explicitly
approved and released to production. See [the execution evidence](verification/PRODUCTION_0056_0057_EXECUTION_RESULT_2026-11-02.md)
and [hash-bound schema receipt](../deployments/schema-0056-0057-20261102.json).
The serving image establishes fa82510 as the new proven migration baseline; no
release guard was removed. For later schema-changing PRs, plan the reviewed schema
and compatible API release before promising automatic deployment: green tests and
image builds alone do not prove that production has the required schema.

On 3 November, the approved 0058 schema and PR #52 compatibility rollout completed.
Automatic workflow [41450888389 attempt 2](https://github.com/Shifannv/salon-backend/actions/runs/41450888389/attempts/2)
passed end to end and promoted commit 253a591 to 100% production traffic. This
supersedes fa82510 as the proven serving baseline. See [0058 execution and release evidence](verification/PRODUCTION_0058_PR52_EXECUTION_RESULT_2026-11-03.md).

## Manual candidate workflow

The historical manual candidate workflow is retained as a disabled/read-only notice;
it is not an alternate normal deployment path. Automatic releases use the reviewed
main-push workflow above. A future one-off manual recovery requires its own explicit
review and approval before the disabled workflow may be changed.

The active automatic workflow uses production environment, concurrency group
`production-cloud-run` with `cancel-in-progress: false`, main-only environment policy,
clean exact checkout, exact target identifiers and zero unreviewed migration
differences. It authenticates through GitHub OIDC/WIF, never a service-account JSON
key. Permissions are `contents: read`, `id-token: write`, `actions: read` for the
exact CI artifact, and `pull-requests: read` for merged-commit admission. No Actions
write permission or production application secret is used.

Normal releases require a matching OCI source revision label. The historical hybrid
image had none and was handled only by the separately approved first-release process;
never assign it a guessed SHA. Current production now provides the proven labelled
baseline required by automatic releases. Any migration difference requires separate
reviewed backup/target/approval. No Alembic upgrade/stamp, schema write or production
data mutation is performed by the workflow.

The 0053–0055 compatibility release now has an exact-source/hash-bound receipt
for the separately completed production SQL execution. It permits only a
zero-traffic candidate, with explicit promotion approval still required. Every
other migration difference remains refused. Once promoted, ordinary releases
derive their baseline from that new image and run automatically after exact-main
CI. See [scope and tests](verification/CLOUD_RUN_SCHEMA_COMPATIBILITY_RELEASE_2026-11-02.md).

CI builds and smoke-tests the exact checked-out commit with OCI revision/source labels.
The release downloads that same run/attempt artifact, verifies its archive, config,
layers and labels, pushes it without rebuilding, resolves its immutable digest, and
rechecks latest main and unchanged service metadata before deployment. It creates a
zero-traffic candidate with a unique revision suffix and review tag. No environment,
secret, runtime service account, CPU/memory/concurrency/min/max/ingress setting is
replaced. Raw service output and environment values are not logged or uploaded.

Candidate read-only checks: Ready, /health, /health/db (SELECT 1), /health/redis
(PING), /docs, and a parsed /openapi.json with contract hash/path count. Compare
expected routes and existing production paths/operations/schema fields before
accepting the candidate; schema changes require separate contract review. This
structural comparison does not prove every application's behavior. No owner,
customer, checkout, booking, payment or deletion mutation runs. Any failed check
holds promotion. A retained zero-traffic revision/tag is not deleted automatically.

After candidate verification, the workflow rechecks the receipt, service resource
version/etag and settled previous traffic, then promotes the tested revision without
rebuilding. Both public hostnames must pass readiness, exact commit identity,
process/database/Redis checks. Any failure restores the complete previous traffic map
and keeps both revisions. The uploaded `candidate-result.json` records exact SHA,
immutable image, candidate/previous revisions, migration comparison, smoke results,
promotion result and rollback command.

## Worker coverage

CI verifies worker imports; candidate deployment covers the API process only.
The audit found worker pool `salon-prod-notifications` and job
`salon-production-db-check`, and no Mumbai Scheduler jobs. This establishes neither
worker health nor coverage for email, media cleanup, payment reconciliation or
account deletion. No worker is upgraded, executed or activated by this workflow.
Unrelated account-deletion release gates remain in effect.

## Historical VM recovery guide — inactive

The following older procedure is retained as historical recovery material. Its
workflow job/artifact path is removed from active CI. Do not dispatch it for normal
Cloud Run production or treat its migration instructions as approval.

The workflow in [backend.yml](../../.github/workflows/backend.yml) tests all branch pushes
and pull requests.
Pushes and PRs test and build; they no longer authorize migrations or deployment.
Deployment requires a manual request, reviewed explicit target/approval and protected
environment approval. Current production/Sydney execution is held by the target policy.
Migrations are never part of container startup. See [migration policy](migrations/MIGRATION_POLICY.md).

## What runs

1. Python 3.12 dependency validation, Ruff, shell syntax checks and pytest.
   A disposable PostgreSQL 18 service runs the real `0014`-to-0037 portable migration
   regression, including downgrade/re-upgrade. Other integration tests that require
   their own explicitly configured database remain skipped.
2. Build a Linux amd64 image from `backend/`, validate Compose using the committed
   GCP environment template, then check non-root execution, `/health` on port 8080,
   all worker imports and the packaged migration files. The smoke check uses
   `scripts/check-container.sh` and requires no production credentials.
3. Package that exact image, its verified image IDs, Compose file and deployment scripts as
   a seven-day Actions artifact. No registry is required; the VM must be amd64.
4. Transfer the artifact over SSH with strict host-key verification. Releases live
   under `~/salon-backend/releases/<commit>-<run>-<attempt>/`.
   The image IDs include the configuration digest used by classic Docker and the
   equivalent manifest digest used by Docker's containerd store. CI checks that
   the archive matches the tested image and that each manifest references its configuration.
5. After separate approval, load and verify the image; run `alembic current`, the explicitly reviewed policy/revision, and
   `current`; update the API, Redis and all workers using `gcp-vm-deploy.sh
   --local-image`. Verify API/database/Redis health, then mark the release current.
6. Check `https://api.salones.in/health` from the runner. Production currently uses
   Cloud Run behind the Google HTTPS load balancer; the legacy VM workflow below
   remains manually gated and must not be dispatched for this hostname migration.

The Compose project stays `backend`, preserving the existing Redis volume. Runtime
secrets stay in `~/salon-backend/backend/.env`; neither the artifact nor GitHub needs
the database URL or provider credentials. The working Git checkout is not updated.
Actions serializes deployments and rejects a release that is already behind `main`.
The VM also holds a `flock` lock throughout migration and startup. Intermediate
pending releases can be superseded by GitHub's concurrency queue.

## One-time VM setup

Use the existing SSH user that owns `~/salon-backend` and can run `docker info`
without sudo. Confirm Docker Compose, `flock` (Debian's `util-linux` package), Bash,
and sufficient disk space are available. The VM must accept SSH on TCP 22 from
the GitHub runner; GCP browser SSH access alone does not establish that access.
If your firewall permits only fixed sources, use a runner with a fixed egress IP.
This workflow does not modify GCP firewall rules.

Ensure the VM `.env` includes the production Supabase and R2 settings required by
the account-deletion worker; its heartbeat must become healthy. Keep Nginx pointing
to the existing API port. Reserve the VM's external address so DNS and SSH stay stable.

Generate a dedicated deployment key on your trusted local computer:

```bash
ssh-keygen -t ed25519 -C github-actions-salon -f salon-actions -N ""
```

Add the contents of `salon-actions.pub` to the VM user's `~/.ssh/authorized_keys`,
using `restrict ` before the public key to disable forwarding and PTY allocation.
Keep directory permissions at 700 and `authorized_keys` at 600. This key still
allows deployment commands and Docker access, so protect it as an administrative
credential. If GCP OS Login manages SSH access, provision this public key through
OS Login for the intended identity instead of relying on `authorized_keys`.

Get the host-key record from the **trusted GCP VM console** (substitute the current
external IP if it changes):

```bash
printf '35.254.254.227 '
sudo cat /etc/ssh/ssh_host_ed25519_key.pub
```

The resulting single line is the `VM_KNOWN_HOSTS` value. Do not fetch and blindly
trust a new host key during deployment.

## GitHub configuration

In this repository's **Settings → Environments**, create `production`. Allow only
`main` to deploy and require a reviewer. If the plan cannot enforce that rule, keep
deployment held. Mumbai read-only validation uses its own reviewed environment.
Add these secrets to that environment (or repository Actions secrets if environment
secrets are unavailable):

| Secret | Value |
| --- | --- |
| `VM_HOST` | `35.254.254.227` (confirm it is still your VM's reserved IP) |
| `VM_USER` | `hafizmuhammedk9080` (the existing deployment user) |
| `VM_SSH_KEY` | Entire private `salon-actions` key, including BEGIN/END lines |
| `VM_KNOWN_HOSTS` | Verified host-key line from the trusted VM console |

Never put these values in a tracked file or paste the private key into chat.
If the public API domain changes, update both the environment URL and HTTPS health
check in the workflow. No application credentials go into GitHub.

Set a branch ruleset on `main` requiring a PR and these checks:
`Lint and tests` and `Build and smoke test image`. Avoid concurrent manual VM
deployments while Actions is deploying. Once the secrets and SSH access are ready,
merge the workflow PR or run **Actions → Backend CI/CD → Run workflow → main**.

## Operate the deployed release

Use the release wrapper so later commands select the deployed image, Compose file,
project and runtime env file together:

```bash
cd ~/salon-backend/releases/current
bash scripts/gcp-vm-release-compose.sh ps
bash scripts/gcp-vm-release-compose.sh logs --tail 100 api
bash scripts/gcp-vm-release-compose.sh run --rm --no-deps api alembic current
```

Do not run `docker compose up` from the old Git checkout after enabling this workflow;
it may select an old image or service definition. Release scripts also accept
`SALON_DEPLOY_ROOT` for an alternate checkout root, but the workflow uses the path above.

## Failed deployment and rollback

A migration failure stops before service replacement. A startup or connectivity
failure fails the job; it may leave some services updated. The `current` pointer
records the last release that passed internal health checks, not necessarily the
containers currently running after a failed rollout. A failed public HTTPS check
can occur after `current` was updated; inspect Nginx, DNS and TLS as well.

Inspect the failed release directory with its own wrapper and `ps`/`logs`. Correct
the issue and deploy a new main commit, or rerun the latest main workflow. Do not
stamp past a failed migration. Releases require schema changes compatible with
the old containers while the explicit upgrade is running.

To restore a previous image, first review database compatibility. From the VM,
replace `PREVIOUS_RELEASE` below with a retained release directory name:

```bash
(
set -e
cd ~/salon-backend/releases/PREVIOUS_RELEASE
exec 9>../deploy.lock
flock -w 600 9
docker load --input image.tar.gz
bash scripts/gcp-vm-release-compose.sh --deploy
)
```

This restores services only; it does not downgrade the database or change `current`.
Verify health before updating the current symlink manually. No automatic database
rollback or image pruning runs. Monitor disk usage; remove only confirmed obsolete
release directories and images while retaining your rollback releases. GitHub's
seven-day artifact retention does not clean VM disk space.

References: [GitHub deployment environments](https://docs.github.com/en/actions/concepts/workflows-and-actions/deployment-environments)
and [deployment concurrency](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments).
