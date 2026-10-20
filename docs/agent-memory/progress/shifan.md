# Progress: shifan

## Goal
Set up the Claude Code workspace (.claude/, CLAUDE.md) and the agent-memory system. This session also did the migration-folder restructure (see Done); the Mumbai reconciliation itself is tracked in progress/mumbai-forward-reconciliation.md.

Latest continuation (2026-10-19): took over the payment/subscription/booking backend plan from Codex (docs only so far), shipped local WebP image variants, and cleaned the Claude tooling. Two local commits (28bf921 image + U06/U07 docs, b0957a5 .claude cleanup) are unpushed pending owner approval. Prepared migrations 0038-0040 and `alembic stamp` remain held.

## Status
ready for PR (local commits unpushed; push needs owner approval)

## Done
- 2026-10-19: commit 28bf921 "Add resilient image variant uploads" (46 files): versioned WebP families (`webp-v2`) with signed manifests, deterministic immutable keys, upload admission middleware (order Timing, CORS, Admission), family-aware cleanup/erasure, read-only `result_url` on `/v1/media/results/{token}` (own signature domain), best-effort `Link` header. Contract and limits: backend/docs/IMAGE_VARIANTS.md; review trail: backend/docs/verification/image-variants-review-2026-10-19.md. Same commit also carries the U06/U07 payment documentation (spec C27/C28/4.6, APPROVAL_REGISTER U06+U07, 0042/0043/0047/09, PHASE1_DECISION_SHEET) because the docs commit was reported as empty; accepted, not rewritten.
- 2026-10-19: commit b0957a5 "Clean up Claude project tooling" (64 files): replica-* skills removed, 15 agents and 4 skills added, CLAUDE.md and start.md router made consistent; non-backend agents marked optional; `learned/` and `commands/rams.md` left unregistered and untracked.
- 2026-10-19: owner approvals recorded: U06 (cancellation bands 70/30 split, reschedule limit 2, owner cancellation, TA02 rejected, TA03-05/08 accepted, TA07 single super-admin aal2, TA10 design) and U07 (payout hold formulas). Details: shared/domain-rules.md.
- 2026-10-19: /wrap run: Ruff clean; full pytest 1126 passed, 82 skipped, 3 failed (the known Windows CRLF failures).
- 2026-10-17: Twenty unchanged-revision natural Cloud Run cold starts verified (10 health, 10 DB-first); p50/p95/p99 ms: health 8384.88/9429.90/9429.90, DB 7422.67/9818.18/9818.18. All 260 measured requests and final three health checks passed. Read-only ownership audit verifies running production-entry VM/DNS, separate Mumbai staging and cost/cleanup scope. See backend/docs/verification/cloud-run-startup-investigation-2026-10-16.md and infrastructure-ownership-cost-2026-10-16.md. Fresh-revision DB-first and exact platform/import split remain unavailable without prohibited configuration changes; no application, VM, cloud configuration, billing, Supabase or DNS mutation. Existing broader business/concurrency gates remain separate.
- 2026-10-16: explicit portable0037 policy and manual Mumbai validation prepared; final CI-equivalent run 1031 passed / 34 skipped, zero collection/setup errors; separate recovery suite 20 passed. See [CI verification](../../../backend/docs/verification/ci-migration-policy-2026-10-16.md).
- Fresh synthetic customer/owner run: all 11 browser assertions pass; 18 API checks pass, two broader gates blocked and runner exits nonzero. Cleanup verified. Real Mumbai DB latency measured; deployed API latency remains unmeasured.
- Approved local API fix applied: Mumbai Session Pooler 5432, verified TLS/read-only CA mount; stale duplicate host Uvicorn stopped. IPv4 health passes three times. Original image missing, so preserved running runtime in a private local recovery image. See [health evidence](../../../backend/docs/verification/local-mumbai-db-health-2026-10-16.md).
- 2026-10-16: reviewed committed snapshot validation and closed remaining QR durable-replay, duplicate-notification, erasure-worker reachability, cache context cleanup and timing gaps. Twenty dedicated disposable SQL/TCP/browser tests pass; see [recovery verification](../../../backend/docs/verification/mumbai-redis-recovery-2026-10-16.md).
- Final continuation checks: 948 passed / 82 skipped, zero failures; 20 opt-in recovery tests separately passed. Ruff and diff whitespace checks pass; one existing deprecation warning remains.
- 2026-10-16: Fixed CI/CD — 4 test failures + 46 setup errors caused by Mumbai migrations (0038–0040) having production-specific review guards that fail on a fresh CI postgres. Added `_TEST_HEAD = "0037_customer_processing_charge"` constant to integration tests; replaced all `alembic upgrade head` calls with `_TEST_HEAD`. Ruff clean, 921 passed / 62 skipped / 18 pre-existing errors. Committed as 9a1eccf.
- 2026-10-16: Fixed local backend startup crash (`No module named 'psycopg2'`). Added `database_url_uses_asyncpg` validator to `Settings` that rewrites `postgresql://` → `postgresql+asyncpg://`. Added regression test `test_database_url_scheme.py`.
- 2026-10-15: authorized local cleanup verified; 14 backups preserved/untracked, 13 runners relocated, exact test image removed; compile/Ruff/path/link checks pass.
- 2026-10-15: final synthetic Mumbai lifecycle, cancellation, no-show, Redis-off idempotency and 11 browser checks pass; cleanup verified. Multi-process cache coherence fails; migration readiness remains held.
- Created CLAUDE.md, .claude/settings.json, skills, commands, agents, docs/agent-memory.
- Moved the karpathy-guidelines skill to its loadable path (it was nested one level too deep).
- Kept the existing code-refactorer agent unchanged.
- 2026-10-15: migration folder restructure, committed by someone else as 827cd47 and 28eb213 (pushed). versions/ holds .py only, sql/ holds sidecars and the 001 baseline, reviews/ holds evidence, backend/docs/migrations/ holds docs. Revision IDs, down_revision and the single head 0040 unchanged; only the sidecar path token changed in 0001, 0035, 0037, 0038, 0039, 0040.
- Evidence re-sealed by backend/scripts/migrations/reseal_layout_evidence.py; SQL content hashes unchanged. Review bundle regenerated byte-identical.
- Test comparison HEAD vs changed tree: 862 vs 871 passed, same 16 setup errors (test_docker_image_ids, test_vm_release). No new failures. Ruff clean. Docker image build, alembic heads/history inside it match local.

## In progress
- Nothing active. Commits 28bf921 and b0957a5 are local only; `.claude/commands/rams.md` and `.claude/skills/learned/` are untracked on purpose. The Redis recovery work from 2026-10-16 was committed earlier.

## Next steps
1. Owner decides on pushing `shifan` (fast-forward from origin/shifan e914c52; CI runs automatically on any push). Do not push without approval.
2. Backend person reviews 28bf921; then watch the first hosted CI run (ubuntu, LF checkout) for the 3 known Windows failures and the integration job (backend/tests/integration/test_account_deletion_sql.py was touched, mock-only).
3. Before any deploy: resolve that `.github/workflows/backend.yml` deploys only with `migration_target=0040_fastapi_only_access` (held Mumbai migration); confirm R2_*, PUBLIC_API_BASE_URL and migration 0020 on the target; deploy API and media-cleanup worker from one release.
4. Staging proof of image variants needs a dedicated non-production R2 bucket, proof of the serving code, and scoped worker/fault access; never point the cleanup worker at a shared bucket.
5. Wiring a `media-cleanup` healthcheck in backend/docker-compose.yml needs a disposable Compose test first (first-sweep time vs `up --wait --wait-timeout 120`); heartbeat code in backend/app/infrastructure/media/health.py has no consumer yet.
6. Owner answers still open (backend/docs/migrations/payment-subscription-booking-designs/APPROVAL_REGISTER.md): Q25 flat fee in INR, TA06 alert targets, TA09 audit retention, Q29 checked-in remedy, dispute scope/release; Cashfree evidence P01-P06 needs an account.
7. Only after owner approval A01: draft Alembic revisions for the cancellation/payout designs (no revision written yet; IDs 0041-0048 are not final).
8. Optional: decide whether `.claude/skills/learned/` and `.claude/commands/rams.md` are kept, moved out or deleted.

## Decisions
- 2026-10-19: `result_url` is a separate read-only token (signature domain `image-result-v1:`) carrying the upload token's original expiry; derived from the validated path token, never from the request URL, and never allowed to turn a stored upload into an error. Why: reusing the PUT token made the "read" link an upload capability and a query string or expiry crossing produced a 422 after objects were stored.
- 2026-10-19: `media-cleanup` Compose healthcheck stays disabled (docker-compose.yml equals HEAD). Why: `scripts/gcp-vm-deploy.sh` runs `up --wait --wait-timeout 120` and the heartbeat is written only after a full sweep, so a slow or failing sweep would fail a good deploy.
- 2026-10-19: U06/U07 documentation shipped inside the image commit rather than rewriting local history; note it in the PR description.
- 2026-10-16: PostgreSQL snapshot validation closes the lost-invalidation window without a new schema. It costs a database query per eligible hit and conservatively misses after unrelated writes; retry state is process-local but crash safety does not depend on it. All legacy readers must be replaced together.
- 2026-10-15: per-branch progress files, because they mirror one-branch-one-PR and avoid teammate merge conflicts.
- 2026-10-15: old paths inside sealed evidence JSON are kept as `layout_restructure.superseded` records, not rewritten, because evidence must stay auditable.
- 2026-10-15: no psycopg2 dependency added; it is not declared and the repo driver is asyncpg.
- 2026-10-16: integration tests stop at `0037_customer_processing_charge` (not `head`) because 0038–0040 are prepared-only Mumbai migrations requiring Supabase-managed pre-conditions; tested separately when the gates pass.

## Files touched
- 2026-10-19: see `git show --stat 28bf921` (image + U06/U07 docs) and `git show --stat b0957a5` (.claude tooling + CLAUDE.md). This wrap only edits docs/agent-memory/** (uncommitted).
- Redis continuation: runtime cache, QR/app booking use cases, durable booking-operation scope, erasure-worker ping gate, dedicated recovery runner and SQL/browser/unit regressions; full list in the recovery verification report.
- CLAUDE.md, .claude/**, docs/agent-memory/**, .gitignore
- backend/migrations/{sql,reviews,versions}/**, backend/docs/migrations/**, backend/scripts/migrations/reseal_layout_evidence.py, backend/.dockerignore, backend/scripts/check-container.sh, affected tests and docs links
- backend/tests/integration/test_payment_ledger_sql.py (added _TEST_HEAD constant, changed _build default)
- backend/tests/integration/test_deployment_migration_chain.py (replaced all "head" upgrade calls with _TEST_HEAD)
- backend/tests/integration/test_subscription_billing_sql.py (replaced 2 explicit upgrade "head" calls)
- backend/app/core/config.py (database_url_uses_asyncpg validator)
- backend/tests/unit/test_database_url_scheme.py (new regression test)

## Blockers and open questions
- Current CI-equivalent collection/setup errors: zero. Historic 18 setup errors were temporary-file/archive/fake-release cases, not Docker-socket prerequisites; the earlier claim below was inaccurate. Exact historic trace unavailable.
- Hosted CI has not run on 28bf921/b0957a5 (unpushed). The 3 known local failures (tests/unit/test_fake_provider.py x2, tests/unit/test_migration_tool_paths.py::test_offline_bundle_matches_sealed_files) come from Windows CRLF worktree files and are expected to pass on Linux CI, unverified. Not fixed here.
- Image variants are unit-tested against a fake R2 only; no live R2, staging, Cloud Run or device check was done. Dedicated non-production R2 bucket does not exist or is unverified.
- Open owner approvals: see Next steps item 6.
- Live committed-session concurrency, provider settlement sandbox and deployed Mumbai API latency remain incomplete. Fresh application assertions passed, but the broader acceptance gate correctly exits nonzero.
- Local health is repaired. Historical request-linked underlying exception was not retained; matching old Docker startup/reproduction failed direct-host DNS. No assertion that Supabase itself was down.
- Prepared migrations 0038-0040 remain held and unapplied; no stamp, grants, sealed evidence edits or production/Sydney changes.

## Review findings
- [fixed] high, PUT could store objects then return 422 (query string / expiry crossing): routes/media.py and r2/storage.py; regression tests in tests/unit/test_image_families.py.
- [fixed] admission outside CORS/timing and non-standard error envelope (app/main.py, core/exceptions.py, media/admission.py).
- [open] low, non-blocking: shared per-IP rate bucket for result GETs and uploads (admission.py), 10 s body read timeout, hardcoded `/webp-v2/` family lock prefix (platform_repository.py), encoded-byte hashes depend on libwebp version.
- [open] low, backend/migrations/reviews/migration-inspection-2026-10-15.md:363, historical report still names backend/migrations/README.md; left as written.

## Session log
- 2026-10-15: workspace and memory setup
- 2026-10-15: migration folder cleanup, evidence re-seal, HEAD vs changed test comparison, backup and runner plans (not executed)
- 2026-10-15: session started
- 2026-10-15: executed authorized backup/index/runner/image cleanup; verified final Mumbai lifecycle, Redis-off replay and 11 browser checks; reproduced cross-process cache failure, cleaned synthetic records and held migration readiness.
- 2026-10-16: diagnosed and fixed CI failures (4 failures + 46 errors from Mumbai migration guards in tests); fixed local backend startup psycopg2 crash; verified ruff clean, 921 passed.
- 2026-10-16: completed local Redis recovery continuation; real two-process TCP faults, independent committed booking sessions and fixture Playwright refresh verified; migrations held and changes left uncommitted.

- 2026-10-16: completed explicit CI policy and clean local verification; fresh synthetic apps/cleanup and qualified Mumbai latency measured; approved local DB health fix verified, migrations held and all changes uncommitted.

- 2026-10-17: completed read-only Cloud Run natural baseline and infrastructure/cost audit; JSON/CSV preserved in ignored backend/.artifacts/cold-start-investigation; no benchmark process remains running and no cleanup commands executed.
- 2026-10-17: session started
- 2026-10-19: session started
- 2026-10-19: took over payment/subscription/booking backend plan from Codex handoff; Phase 1 decision sheet written (backend/docs/migrations/payment-subscription-booking-designs/PHASE1_DECISION_SHEET.md); awaiting owner answers; no code, migration or database change
- 2026-10-19: recorded U06 in APPROVAL_REGISTER.md; added C27/C28 and section 4.6 to the spec and U06 section to 0047; TA02 marked rejected; Markdown link/anchor/whitespace checks pass; Q19, TA07, settlement arithmetic and reschedule-count rule later added to U06; no code, SQL, migration, database or provider change
- 2026-10-19: implemented approved local WebP image families, deterministic variants with compatibility aliases, signed manifests, family-aware cleanup/erasure, bounded ingress/processing and cleanup heartbeat; 298 focused checks and full Ruff pass; broader unit run 1085 pass/3 untouched newline-sensitive failures; no database, live storage, frontend or deployment changes. Contract, files, limits and next approval: backend/docs/IMAGE_VARIANTS.md. Changes remain uncommitted pending backend review and separately authorized isolated staging verification.
- 2026-10-19: image review requests changes: admission sits outside CORS/timing and returns a nonstandard error envelope. Reproduced locally; no implementation fix authorized in review. Focused 298 pass and Ruff clean. Actual HEAD baseline reproduces the two payment JSON CRLF failures but passes sealed CSV test; current sealed CSV has CRLF raw-byte drift versus LF HEAD, originals untouched. Report: backend/docs/verification/image-variants-review-2026-10-19.md; ignored evidence records complete 108-path entry manifest. Staging not contacted because clean-review gate failed; documented Mumbai candidate has unverified current code/bucket isolation. Hold commit approval; correct admission, resolve checkout integrity separately, re-review before any scoped staging traffic. No database, live storage, frontend, migration, deployment, commit or push.
- 2026-10-19: fixed only admission regressions: main middleware order is timing then CORS then admission; early rejects reuse the AppError serializer and error metrics with stable status codes. New HTTP regressions proved six failures before the fix and pass afterwards; 31 admission tests and combined 211 focused media/telemetry/API tests pass, Ruff and whitespace checks pass. Existing production Server-Timing privacy policy retained. Code/test files changed this task: app/main.py, app/core/exceptions.py, app/infrastructure/media/admission.py and tests/unit/test_media_admission_http.py (all under backend). Fingerprints of 118 protected migration/sealed/R2/policy/cleanup files unchanged. Sealed CSV CRLF issue stays separate. Mumbai serving code, isolated nonproduction bucket and scoped worker/fault access still need verification before authorized staging; no database, live R2, Cloud Run, frontend, schema, deployment, commit or push. Synthetic response and local evidence: backend/.artifacts/image-admission-fix/.
- 2026-10-19: result_url read-only token fix, U06/U07 documentation alignment, independent re-reviews, commits 28bf921 and b0957a5, CI/CD workflow audit and deployment handoff report. No push, deploy, migration, R2, staging, Cloud Run, VM or Cashfree action. Wrap: Ruff clean; pytest 1126 passed / 82 skipped / 3 known failures.
