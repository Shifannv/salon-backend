# GitHub Actions to the GCP VM

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
6. Check `https://apiv1.mudassirmhd.in/health` from the runner, through Nginx/TLS.

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
