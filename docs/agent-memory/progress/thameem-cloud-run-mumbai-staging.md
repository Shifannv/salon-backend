# Progress: thameem/cloud-run-mumbai-staging

## Goal
Deploy the approved Mumbai staging API and measure IAM-authenticated cold starts without production changes.

## Status
ready for PR

## Done
- Created approved staging image repository, dedicated runtime identity, four scoped secrets and IAM-only Cloud Run service in asia-south1.
- Verified existing Redis TLS and adapter commands using cleaned synthetic keys; Free/Mumbai metadata is user-confirmed because account API metadata was unavailable.
- Mumbai target/key claims and strict-TLS read-only probe passed; no migrations or business writes.
- Final revision cold19 receives all staging traffic; min 0/max 1, CPU 1/memory 512 MiB, concurrency 8, request billing and boost disabled all verified.
- Ten audited request-initiated cold instances: p50 8386.97 ms, p95/p99 13815.61 ms. Nine prestarted trials excluded; all 342 measured health responses and 285 warm responses succeeded.
- Removed nine temporary measurement tags; final health/DB/Redis 200, anonymous 403, scoped secret access verified.
- Twelve health/cache tests pass; Ruff passes; no full integration/migration suite run under the no-migrations instruction.

## In progress
- None; evidence and report are uncommitted.

## Next steps
1. Review backend/docs/verification/cloud-run-mumbai-staging-2026-10-16.md and ignored backend/.artifacts/cloud-run-staging/cold-start-audit.json.
2. If needed, separately measure natural idle-to-zero and later reactivation of the same revision; keep min instances zero.
3. Business-flow acceptance and production actions require separate scope; this deployment only verifies health and startup.

## Decisions
- 2026-10-16: use tagged no-default-traffic revisions for cold measurement because ordinary rollouts prestarted instances despite deployment-time prewarming being disabled; require instance/request correlation before accepting samples.
- 2026-10-16: package a pinned public database CA in the staging-only image and pin secret versions; credentials never enter image layers or command arguments.

## Files touched
- backend/docs/verification/cloud-run-mumbai-staging-2026-10-16.md
- docs/agent-memory/progress/thameem-cloud-run-mumbai-staging.md
- docs/agent-memory/SESSIONS.md
- Ignored validation/deployment/measurement evidence in backend/.artifacts/cloud-run-staging/.

## Blockers and open questions
- No deployment blocker remains. Independent Redis plan/region metadata is unavailable; provider account details were user-confirmed.
- Natural idle-to-zero duration, business workflows and production SLOs remain unmeasured.

## Review findings
- [fixed] Prestarted rollout observations excluded from cold percentiles using actual revision and instance-start evidence.
- [fixed] Initial public certificate byte mismatch was only newline formatting; identical DER confirmed before rebuilding.

## Session log
- 2026-10-16: deployed and verified Mumbai staging, completed ten audited cold starts, removed measurement tags and preserved all prohibited targets.
