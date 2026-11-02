# Traffic verification metadata correction — 2 November 2026

The owner-approved promotion of commit 0027a9b succeeded: Cloud Run routed 100% to
`salon-api-production-gh-0027a9be-41405234717-1`, and independent readiness, version,
health, database and Redis checks passed on both production API domains.
The existing verification wrapper nevertheless reported a configuration change
and refused its recovery path. The service's server-owned `lastModifier` changed
from the revision's deployment identity to the approved operator identity.

Cloud Run documents `lastModifier` as output-only, not application configuration:
[Service REST resource](https://docs.cloud.google.com/run/docs/reference/rest/v2/projects.locations.services).
It belongs with the comparator's existing exclusions for generation, update time,
reconciliation and traffic status. Excluding only this additional field avoids a
false alarm during polling, promotion verification and rollback. Runtime templates,
service accounts, environment/secret references, ingress, labels, scaling and every
other configuration field remain compared exactly. Etag concurrency checks and
traffic/tag identity checks are unchanged. No IAM/WIF or runtime change is needed.

Three regressions reproduced the old failure before the one-field correction:
configuration comparison across modifier changes, traffic reconciliation with a
changed modifier, and failed-health rollback after that modifier change. They must
pass afterward, while the existing true runtime-change rejection still passes.

Read-only production metadata also confirmed that the v2 API preserves separate
tagged-zero and untagged-100 traffic rows. Their existing identity comparison works;
no traffic normalization change is introduced.

This change does not run migrations or relax contract admission. The first release's
admin trial contract differences were separately accepted by the owner with explicit
`PROMOTE CLOUD RUN CANDIDATE` approval. Subsequent no-migration main merges compare
against that now-serving commit through the existing automatic release path.
