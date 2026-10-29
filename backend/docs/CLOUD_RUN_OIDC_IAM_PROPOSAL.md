# Approved GitHub Free OIDC configuration

The user approved the exact resources and scoped bindings below after revising
the trust condition for GitHub Free. Creation/readback status is recorded in the
audit report. No service-account JSON key is needed or permitted.

Verified target: project `saloon-505509`, number `283739091709`, region
`asia-south1`, service `salon-api-production`, Artifact Registry repository
`salon-production`. GitHub repository ID `1422493480`, owner ID `172572480`.

Create a dedicated account rather than expanding the existing `github-deploy`
account, which already has project-wide Artifact Registry writer access and an
older user-managed key. Preserve that account/key; retirement needs separate review.

| Proposed object | Identifier |
| --- | --- |
| Workload Identity pool | `salon-github` |
| OIDC provider | `salon-backend` |
| Deployment service account | `salon-github-deploy@saloon-505509.iam.gserviceaccount.com` |
| Provider resource | `projects/283739091709/locations/global/workloadIdentityPools/salon-github/providers/salon-backend` |

Requested IAM bindings only:

| Member | Role | Resource scope |
| --- | --- | --- |
| New deployment account | roles/artifactregistry.writer | Existing salon-production repository, asia-south1 |
| New deployment account | roles/run.developer | Existing salon-api-production service only |
| New deployment account | roles/iam.serviceAccountUser | salon-production-runtime@saloon-505509.iam.gserviceaccount.com only |
| Federated principalSet, repository_id 1422493480 | roles/iam.workloadIdentityUser | New deployment account only |

No Owner, Editor, Secret Manager accessor, service-account key, project-wide
Cloud Run write grant, or worker execution grant is proposed. Cloud Run Developer
can update service configuration/traffic; IAM does not constrain it to image-only
updates. Workflow dispatch/input guards and exact actor/environment trust provide
that restriction. Main is not protected; required reviewers/rulesets are not
relied upon. Anyone who can change main can change workflow code; the exact actor
must review the selected commit before manually dispatching it.

The provider issuer is `https://token.actions.githubusercontent.com`.
Map `google.subject=assertion.sub` and the following matching attribute claims:
`repository`, `repository_id`, `repository_owner_id`, `ref`, `actor_id`,
`workflow_ref`, `event_name`.

Provider CEL condition (all terms required):

```text
assertion.repository_id == '1422493480' &&
assertion.repository_owner_id == '172572480' &&
assertion.repository == 'Shifannv/salon-backend' &&
assertion.actor_id == '172572480' &&
assertion.ref == 'refs/heads/main' &&
assertion.sub == 'repo:Shifannv/salon-backend:environment:production' &&
assertion.event_name == 'workflow_dispatch' &&
assertion.workflow_ref == 'Shifannv/salon-backend/.github/workflows/cloud-run-candidate.yml@refs/heads/main'
```

Federated IAM member:
`principalSet://iam.googleapis.com/projects/283739091709/locations/global/workloadIdentityPools/salon-github/attribute.repository_id/1422493480`

After approval, create the three proposed objects, apply only the four bindings,
read back the trust policy and grants, then set the two GitHub variables
`GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_DEPLOY_SERVICE_ACCOUNT`. If an API must be
enabled or permissions differ from this scope, report before expanding the plan.
Workflow gates also require approve_deployment=true, typed confirmation exactly
DEPLOY api.salones.in, supplied SHA equal to github.sha and latest remote main,
and CI/image verification in the same run. The user explicitly forbids workflow
dispatch, candidate creation and traffic changes during this configuration phase.
Future traffic approval must be the exact message PROMOTE CLOUD RUN CANDIDATE.

References: [Google federation setup](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines),
[Cloud Run deployment roles](https://docs.cloud.google.com/run/docs/reference/iam/roles),
[auth action security](https://github.com/google-github-actions/auth).
