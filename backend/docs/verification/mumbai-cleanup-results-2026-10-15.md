# Authorized local cleanup - 2026-10-15

Cleanup is complete and uncommitted. No database operation, schema/migration edit,
Git history rewrite, Sydney/production/GCP/Cloud Run/DNS change was part of cleanup.
The separately authorized synthetic Mumbai acceptance run is documented in
[final acceptance](mumbai-final-acceptance-2026-10-15.md).

## Backup preservation

- External copy: `D:/salon-secure-backups/supabase-schema-2026-10-15`.
- Initial copy contained two files; both matched. Twelve missing files were copied.
- All 14 tracked files match SHA-256 between local, external and restored scratch copies.
- Both embedded SHA256SUMS and verification.json schema hashes also match.
- The external directory now has SHA256SUMS.all covering all 14 files. It is outside
  the checkout on the same drive; this does not establish off-site disaster recovery.
- Added `supabase-schema-backup/` to `.gitignore`.
- Ran `git rm --cached` with the 14 explicit filenames only. Git no longer tracks
  those files, while all 14 working-tree files remain byte-identical.
- Older commits still contain the backups. No history was rewritten.

## Runner relocation

Seven active/shared modules are in `backend/scripts/migrations/`:
`review_bundle`, `review_validate`, `revision_runtime_review`, `sql_preflight`,
`execution_preflight`, `staging`, `reference` (all retain their
`migration_mumbai_*_20261015.py` names).

Six historical modules are in `backend/scripts/migrations/evidence/`:
`booking`, `completion_business`, `completion_runner`, `runtime`,
`completion_audit`, `forward_validation`.

The tracked moves used `git mv`. Imports now use the package paths, including lazy
cross-folder imports; active ROOT definitions use `parents[3]`. Run from the repo
root with `python -m backend.scripts.migrations.<module>` or
`python -m backend.scripts.migrations.evidence.<module>`.
See [tool instructions](../../scripts/migrations/README.md). README and live references
were updated; sealed evidence retains its historical paths. No DB-touching runner ran.

## Verification and exact image removal

- Compile: pass for migration tools and the new acceptance helpers.
- Migration path tests: 17 passed. Every runner imports with network connections and
  credential-file reads prohibited; roots/distribution are checked. Offline generators
  write only to scratch and reproduce the sealed bundle/revision report byte-for-byte.
- Backend suite: 922 passed, 62 skipped, one existing Starlette warning.
- Ruff: pass for app/tests/migrations, moved tools and staging/acceptance helpers.
- Changed-document local links: checked; no broken targets.
- Git diff under `backend/migrations/`: empty. Raw blob/worktree differences are
  existing CRLF/LF conversions; no content or seals were rewritten.
- Removed only `salon-api:migration-layout-check`, without force or prune. Docker
  reported untagging and deleting image ID
  `sha256:269f6e35d47c846028a646ca895ec8a8b6783a2b66b648882e68b8ef7f505375`.

Evidence is ignored under `backend/.artifacts/cleanup-2026-10-15/`:
backup-verification.json, restore-verification/, image-cleanup.json,
link-and-migration-checks.json and backend-tests.txt. Runners/index removals are staged
by the authorized git operations; subsequent source/docs edits and new tests/helpers
remain uncommitted. Existing unrelated work, including a concurrent settings validator
change, was preserved. Nothing was committed.
