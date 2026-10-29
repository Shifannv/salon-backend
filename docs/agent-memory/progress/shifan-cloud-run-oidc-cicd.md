# Progress: shifan-cloud-run-oidc-cicd

## Goal
Make the personal repository canonical and prepare protected OIDC Cloud Run candidates.

## Status
in progress

## Done
- origin now Shifannv/salon-backend; previous repository preserved as upstream.
- Both main trees match despite merge-history divergence; shifan already present.
- Prepared CI and zero-traffic CD with exact-source/digest/configuration guards.
- Corrected two disposable fixtures to include existing 0050; no remote SQL.
- Full local suite 1727 passed/36 skipped; Ruff, pip, actionlint, shell, Compose,
  Docker build/nonroot/custom-port/worker imports pass.
- Four verified nonsecret repository target identifiers configured.

## In progress
- Push reviewed CI/CD branch and open PR; observe GitHub CI.

## Next steps
1. Review PR checks; merge only after review and passing checks.
2. Resolve GitHub protection availability; configure required main checks and
   production reviewer/main-only environment per backend/docs/CI_CD.md.
3. Obtain explicit approval for backend/docs/CLOUD_RUN_OIDC_IAM_PROPOSAL.md.
4. Prove serving-image source baseline before any candidate dispatch.
5. After protected latest-main candidate passes, request explicit traffic approval.

## Decisions
- 2026-10-29: Preserve divergent merge histories because file trees already agree.
- Do not replace private protections with weaker gates or change billing/visibility.
- Refuse unknown deployed provenance/migration differences rather than assume a SHA.

## Files touched
- .github/workflows/backend.yml and cloud-run-candidate.yml; ignore rules.
- backend/scripts/cloud_run_candidate.py; guard tests and two integration fixtures.
- backend/docs/CI_CD.md, RUNBOOK.md, DOCKER_DEPLOYMENT.md, IAM proposal and audit.

## Blockers and open questions
- GitHub private branch protection requires a supported plan; required environment
  reviewers also require a plan supporting them. No production environment exists.
- No WIF pool/provider or dedicated approved deploy identity yet.
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
  production baseline subpct-20261028 remains untouched.
