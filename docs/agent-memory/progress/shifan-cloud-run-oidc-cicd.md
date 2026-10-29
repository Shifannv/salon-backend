# Progress: shifan-cloud-run-oidc-cicd

## Goal
Make the personal repository canonical and prepare exact-actor OIDC Cloud Run candidates.

## Status
in progress

## Done
- origin now Shifannv/salon-backend; previous repository preserved as upstream.
- Both main trees match despite merge-history divergence; shifan already present.
- Prepared CI and zero-traffic CD with exact-source/digest/configuration guards.
- Corrected two disposable fixtures to include existing 0050; no remote SQL.
- Full local Free-plan suite 1730 passed/36 skipped; final23 guard checks pass; Ruff, pip, actionlint, shell, Compose,
  Docker build/nonroot/custom-port/worker imports pass.
- All six verified nonsecret production environment identifiers configured/read back;
  its branch policy is exactly main. Four matching repository target variables remain.
- User-approved pool/provider/deployment account and four scoped bindings created;
  actor-ID trust readback exact, no ref_protected or project-wide grants/keys.

## In progress
- PR #14 open; initial CI green; update free-plan guards and observe final CI.

## Next steps
1. Review PR checks; merge only after review and passing checks.
2. STS API activation needs separate authorization; it remains disabled.
3. Prove serving-image source baseline before any future candidate dispatch.
4. Current user instruction forbids dispatch/candidate/traffic changes; stop after configuration.
5. Future traffic requires the exact message PROMOTE CLOUD RUN CANDIDATE.

## Decisions
- 2026-10-29: Preserve divergent merge histories because file trees already agree.
- User explicitly chose GitHub Free/private; exact repo/owner/actor IDs, main ref,
  environment subject, workflow/event path and typed/SHA guards replace unavailable protections.
- Refuse unknown deployed provenance/migration differences rather than assume a SHA.

## Files touched
- .github/workflows/backend.yml and cloud-run-candidate.yml; ignore rules.
- backend/scripts/cloud_run_candidate.py; guard tests and two integration fixtures.
- backend/docs/CI_CD.md, RUNBOOK.md, DOCKER_DEPLOYMENT.md, IAM proposal and audit.

## Blockers and open questions
- No enforced main protection/reviewers on Free; do not request an upgrade or change visibility.
- STS API disabled; no exchange/dispatch permitted or performed.
- Serving image has no source labels; migration baseline cannot be proven.
- Existing API/worker release gates remain independent; no worker activation.

## Review findings
- [fixed] High: legacy VM deploy removed from active workflow; recovery scripts kept.
- [fixed] High: ignored working-tree content excluded by building a git archive.
- [fixed] High: runtime configuration/normal traffic compared privately after image update.
- [fixed] CI fixture drift: disposable schema now includes existing 0050, no skipped assertions.
- [open] Infrastructure/provenance gates prevent live end-to-end CD validation.

## Session log
- 2026-10-29: Canonical remotes, scoped CI/CD source and local validation prepared;
  production baseline subpct-20261028 remains untouched. User then approved exact
  actor-restricted IAM scope; three objects/four bindings and environment variables verified.
