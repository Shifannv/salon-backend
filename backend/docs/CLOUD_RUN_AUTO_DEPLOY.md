# Automatic production releases after main CI

The owner requested automatic releases instead of confirming each ordinary API
deployment. This changes the release model for the new main-push workflow only.
The manual candidate workflow still stops before traffic assignment.

## Behavior

After activation, a push/merge to `main` by GitHub actor ID `172572480` runs
`.github/workflows/cloud-run-auto.yml`:

1. Run the reusable backend CI, including PostgreSQL tests and Docker smoke checks.
2. Verify exact latest-main checkout, repository, actor, production branch policy
   and target identifiers. Authenticate with existing OIDC/WIF, never a JSON key.
3. Derive the baseline from the currently serving immutable image's Git revision
   and repository labels. Require that revision to be an ancestor of selected main.
4. Refuse any migration-source difference. Build exact Git source, push a unique
   image, resolve its digest and create a zero-traffic candidate using the existing
   candidate checks. Preserve runtime variables/references, service account,
   scaling, ingress and both hostnames. No migrations or workers run.
5. Require Ready, all five candidate GET checks and the strict OpenAPI comparison.
   Recheck latest main, service version, candidate readiness/digest and previous
   traffic. Promote the same tested revision to 100%, without rebuilding it.
6. Check API/DB/Redis health on both `api.salones.in` and the retained
   `apiv1.mudassirmhd.in`. On the first failure, restore previous traffic and check
   health again. Leave both revisions and every existing tag in place.

Only the existing service's `traffic` field is patched through Cloud Run v2, with
the service etag for concurrent-edit protection. No runtime configuration is sent
in the PATCH. Reconciliation polls only the named service, avoiding any need for
location-wide operation-read permissions. The workflow shares `production-cloud-run` concurrency with manual
candidates and does not cancel an in-flight release.

`candidate-result.json` and the Actions summary record commit, digest, previous
and candidate revisions, rollback command, candidate/public checks and final status.
The receipt is ignored locally so it cannot dirty the source checkout. It is a
generated output, never an independently trusted promotion input. Promotion uses
the in-process result and revalidates live state.

Rollback is attempted on ordinary operation/health failures, including a lost
response after traffic was accepted. A concurrent external edit is not overwritten.
Runner cancellation, loss, API outage or conflicting edits can prevent automatic
rollback; the failed run retains the exact rollback command for the operator.

GitHub Free does not enforce private branch review. The owner must review code
before merging/pushing main: **an eligible main push becomes release authorization**
after activation. Other actors, feature branches and PR events cannot auto-deploy.
Do not grant other actors access by silently relaxing the trust condition.

## One-time prerequisites — activation is still pending

The current serving hybrid image lacks proven Git labels. Production schema and
OpenAPI also differ from recent main. Automatic bootstrap is deliberately refused.
See [schema reconciliation](CLOUD_RUN_SCHEMA_RECONCILIATION.md) and
[restored-copy evidence](SCHEMA_REHEARSAL_20261029.md). Newer main migrations must
be reviewed against their own frozen hashes; the earlier rehearsal does not approve
later SQL edits.

Before enabling automation:

1. Review/merge this PR with green checks. Keep `AUTO_DEPLOY_ENABLED` absent or
   `false` in GitHub environment `production` until all prerequisites are complete.
2. Separately approve the narrow WIF condition update below; apply/read back it.
3. Resolve schema adoption and client contract compatibility through separately
   reviewed target/hash-bound approval and a fresh verified backup. No automatic
   Alembic upgrade/stamp or migration allowance is introduced here.
4. Complete a separately reviewed initial release with a verified Git-labelled
   serving image. Do not invent a Git SHA for the legacy image or bypass the
   existing bootstrap/migration/contract gates to activate automation.
5. Set the nonsecret production environment variable `AUTO_DEPLOY_ENABLED=true`.
   The next eligible main push then runs the automatic release. For an immediate
   pause, set it to `false`; do not cancel an already-promoting job.

The existing six GCP production environment variables remain unchanged. No
application secret is copied to GitHub. No new cloud resource, IAM role/binding,
service-account key, DNS, TLS, load-balancer, scaling or billing change is needed.
The workflow uses GitHub Actions minutes; no plan upgrade is requested.

## Exact IAM trust proposal — not yet applied

Resource:
`projects/283739091709/locations/global/workloadIdentityPools/salon-github/providers/salon-backend`.

Keep issuer, mappings, numeric repository/owner IDs, exact actor, main ref and
production environment subject unchanged. Keep the existing manual workflow/event
pair, and additionally permit **only** push with the exact auto workflow path.
The proposed CEL is [github-auto-condition.cel](../deployments/github-auto-condition.cel).
The paired OR prevents an event/path cross-match. Existing four scoped IAM grants
and the deployment account remain unchanged.

After explicit approval of this trust update, from the reviewed repository root:

```bash
gcloud iam workload-identity-pools providers update-oidc salon-backend \
  --project=saloon-505509 --location=global --workload-identity-pool=salon-github \
  --attribute-condition="$(cat backend/deployments/github-auto-condition.cel)"

gcloud iam workload-identity-pools providers describe salon-backend \
  --project=saloon-505509 --location=global --workload-identity-pool=salon-github \
  --format='json(name,attributeCondition,attributeMapping,oidc.issuerUri)'
```

Compare the returned condition and mappings with the reviewed proposal. Only after
the other prerequisites and initial Git-proven release are complete:

```bash
gh variable set AUTO_DEPLOY_ENABLED --repo Shifannv/salon-backend \
  --env production --body true
```

These are operator commands, not steps executed by CI. No IAM update or production
release is performed just by opening or testing this PR.

References: [GitHub reusable workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows),
[Cloud Run traffic-only field mask](https://docs.cloud.google.com/run/docs/reference/rest/v2/projects.locations.services/patch),
[Cloud Run etag](https://docs.cloud.google.com/run/docs/reference/rest/v2/projects.locations.services).
