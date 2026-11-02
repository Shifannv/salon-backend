# Approved GitHub artifact cleanup — 2 November 2026

GitHub CI validation reached artifact upload but failed because artifact storage
quota was full. The backend inventory contained 195 artifacts totaling
20,477,453,916 bytes. Fifty-seven were CI image archives uploaded by main,
feature, PR and duplicated reusable/standalone CI runs.

The owner explicitly approved preserving the latest tested main image locally,
then permanently deleting exactly those 57 GitHub image archives, while retaining
all 138 other artifacts and all production backups/cloud rollback images.
The owner separately approved a no-cloud/OIDC cleanup job with Actions-write
permission limited by code to its own consumed image archive.

Preserved image source: main `7185ec1ede40c94a39ae132808832dcb9755f108`,
successful CI run 41334283559, artifact 13094293298. Archive/provenance, source
labels, image identities and layers verified before deletion. Local copy:
`C:\D\salon\salon-backend\backend\.artifacts\latest-main-preserved-7185ec1`.
Image tar SHA-256:
`4973b6b5cf15304b852395b7f48e48d974827ceed182392c100c0b04edd7b47e`.

Result: **57 exact manifest IDs deleted; 20,350,251,974 bytes removed**.
GitHub readback confirmed 138 artifacts remain. No other artifact, workflow run,
source commit, branch, production backup, GCP image or revision was deleted.
Deleted GitHub artifact IDs cannot be restored; the latest tested copy remains
locally preserved and the production rollback images remain in GCP.

Exact manifest and per-ID deletion evidence are local-only under
`backend/.artifacts/ci-artifact-cleanup-20261102/`.
The follow-up storage prevention change is PR #46. Image archive upload remains
mandatory for deployment; diagnostic report uploads alone are best-effort.
GitHub documents that storage accounting can take 6–12 hours to update after
deletion: https://docs.github.com/en/billing/concepts/product-billing/github-actions.
No billing setting was changed.
