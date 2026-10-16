# Progress: thameem/cloud-run-startup-investigation

## Goal
Investigate startup phases, measure ten cold-first requests per endpoint for fresh revisions and natural shutdowns, and report safe options before any configuration change.

## Status
in progress — wrap recorded; natural sampling still running

## Done
- Read startup code and unchanged Cloud Run settings. Existing ten fresh process-health samples reverified on the server clock.
- Existing paired cloud logs: pre-lifespan median 6997.98 ms, lifespan 530.62 ms; DB warm-up upper span 127.21 ms, Redis 401.43 ms, probe delay 709.55 ms.
- Ten isolated local ordinary imports median 1081.57 ms; ten low-overhead local factory profiles identify registration and pool-construction costs without modifying application files.
- Recommendations reported in backend/docs/verification/cloud-run-startup-investigation-2026-10-16.md. No Cloud Run change made during investigation so far.
- Natural runner started on fixed serving revision cold19; incremental results in ignored backend/.artifacts/cold-start-investigation/natural-results.json. Do not duplicate it or send manual HTTP requests during idle intervals.

## In progress
- Natural study targets ten independently cold first requests for each of /health and /health/db. Require active and idle counts both zero plus instance termination evidence. Match request arrival and instance startup on the server clock.
- Tool execution session 25211 owns the resumed natural runner. Fourteen natural samples (7 per endpoint) were preserved after one control-plane read RuntimeError; Cloud Run/Monitoring read access was independently rechecked. Original session 33017 exited. Read JSON for current counts; completed samples are not a full distribution until each endpoint reaches ten.
- Read-only ownership/cost audit added in backend/docs/verification/infrastructure-ownership-cost-2026-10-16.md. Production DNS points to running VM 35.254.254.227 in us-central1-a; separate Mumbai staging Cloud Run remains IAM protected. No VM SSH or mutations. VM proxy internals and Upstash provider account metadata remain unverified.

## Next steps
1. Monitor natural-results.json; preserve all completed, rejected and pending observations. Do not trigger keep-alive requests or change the service during this phase.
2. Do NOT run fresh_db_study.py: latest user steering explicitly forbids configuration changes and says not to ask again. Fresh DB-first trials require new revisions/tags and remain unavailable under this restriction. Reuse only the existing verified ten fresh process-health samples.
3. Correlate phase/server metrics, update the investigation report with full distributions, then verify final settings and scoped access without revealing values.

## Decisions
- 2026-10-16: require explicit shutdown logs as well as monitoring zero counts; delayed/transient zero metric samples alone can misclassify a live instance.
- 2026-10-16: use trace-correlated server request intervals to classify cold starts rather than comparing unsynchronized workstation and server timestamps.
- 2026-10-16: no production/VM/Sydney/DNS/frontend/migration/payment action; no boost/CPU/memory/concurrency changes during baseline.
- 2026-10-16: latest user steering: no configuration changes; continue staging natural measurement without asking again. Send updates only at 25%, 50%, 75%, 100% (5/10/15/20 accepted natural cold samples) or immediate failure, inability to reach zero, unexpected cost, unhealthy service or production/VM risk.

## Files touched
- backend/docs/verification/cloud-run-startup-investigation-2026-10-16.md
- docs/agent-memory/progress/thameem-cloud-run-startup-investigation.md
- .mcp.json (new — Supabase MCP server)
- .agents/skills/supabase/, .agents/skills/supabase-postgres-best-practices/ (new — agent skills)
- .claude/skills/supabase, .claude/skills/supabase-postgres-best-practices (new symlinks)
- skills-lock.json (new — from npx skills add)
- Ignored scripts/evidence in backend/.artifacts/cold-start-investigation/.

## Blockers and open questions
- Natural shutdown cycles take real idle time; no shortcut, forced termination or revision deployment counts as a natural restart.
- Pure platform versus Python import duration is not separately observable in the deployed image. Recommendations identify additional low-overhead markers needed for that split.
- Existing source checkout was clean on shifan; prior deployment reports were absent, while ignored evidence remained. Those removed files were not restored.
- **BLOCKER**: `test_mumbai_validation_workflow_is_manual_and_has_no_scratch_service` fails — `environment: mumbai-migration-validation` line was removed from `.github/workflows/mumbai-migration-validation.yml` in the uncommitted diff. This line is required by the test policy and must be restored before committing.
- 23 test errors (docker image IDs, migration tool paths, vm_release) are pre-existing sealed-evidence-absent errors, unchanged from prior sessions.

## Review findings
- [fixed] Natural cold classification uses server-clock request timing; zero-count gate now also checks known instance shutdown completion.
- [wontfix] Heavy function profiling inflated local time; excluded from conclusions and replaced with ordinary imports plus low-overhead local wrappers.

## Session log
- 2026-10-16: investigation started; startup spans analyzed and natural unchanged-revision sampling running; recommendations reported before any Cloud Run change.
- 2026-10-16: Supabase MCP server added (.mcp.json, project wqjlgpnbiapcrlkxumcp); agent skills installed; ruff clean; 959 passed, 1 failed (test_mumbai_validation_workflow_is_manual_and_has_no_scratch_service — environment: line removed from CI workflow in uncommitted diff), 23 errors (sealed evidence absent locally, pre-existing).
