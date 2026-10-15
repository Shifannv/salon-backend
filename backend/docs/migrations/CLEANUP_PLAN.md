# Migration cleanup plan (prepared, NOT executed)

Nothing here has been run. Each section needs explicit approval. No database,
Supabase, Sydney, GCP, Docker runtime or Cloud Run access is involved.

## 1. `supabase-schema-backup/` in Git

Audit (counts only, no content printed):

| Item | Result |
| --- | --- |
| Tracked files | 14 at HEAD `28eb213`: the original 4 (`schema.sql` 269 KB, `roles.sql` 370 B, `history_schema.sql` 0 B, `history_data.sql` 41 B) plus 10 in two `mumbai-pre-0038-0040-*` folders (about 1.8 MB: schema, rollback preflight, CA cert, checksums, verification.json). The 10 were untracked when audited and were committed afterwards. |
| Untracked files | 0 |
| Total size | 2,058,878 bytes (all tracked) |
| Remote | HEAD is in `origin/main` and `origin/shifan`, so these files are already pushed |
| Credential patterns (passwords, JWTs, private keys, connection strings, API keys) | none found |
| Email addresses / `COPY` / `INSERT` data blocks | none found |
| Content | schema only (`CREATE TABLE` 44 and 83 per file); CA files are public certificates |

Risk: no secrets or user data found, but backups do not belong in Git. They are already
on the remote, so `git rm --cached` only stops future tracking; it does not remove them
from history.

Prepared steps (run only after approval):

1. Copy to a secure external location outside the repo (for example an access-controlled
   bucket or encrypted drive). Verify with `sha256sum -c` against each `SHA256SUMS`
   and against `verification.json` before touching Git.
2. `.gitignore` rule to add: `supabase-schema-backup/`
3. Untrack but keep local files: `git rm -r --cached supabase-schema-backup/`
   (`--cached` leaves the working-tree files in place; confirm with `ls` afterwards).
4. Restore verification: copy back from the external location to a scratch folder,
   re-run `sha256sum -c`, and compare `schema.sql` hashes to the values recorded in
   `backend/migrations/reviews/migration-mumbai-forward-baseline-2026-10-15.json`.
5. Old commits (including the pushed ones) still contain all 14 files. They hold no
   secrets or user data, so history rewriting is not recommended; it would also need a
   force-push to shared branches.

## 2. Root `migration_mumbai_*.py` runners (13)

Target: active tools to `backend/scripts/migrations/`, evidence stays in
`backend/migrations/reviews/`. Move with `git mv` (tracked) or `mv` (untracked), no copies.

| Runner | Role | Touches DB or network | Move |
| --- | --- | --- | --- |
| `review_bundle` | Active: regenerates the review bundle | No | `scripts/migrations/` |
| `review_validate` | Active: validates the bundle | No | `scripts/migrations/` |
| `revision_runtime_review` | Active: per-revision local review | No | `scripts/migrations/` |
| `sql_preflight` | Active: BEGIN/ROLLBACK preflight (psql) | Yes (Mumbai only) | `scripts/migrations/`, keep gated |
| `execution_preflight` | Active: schema-only backup (pg_dump) | Yes (Mumbai only) | `scripts/migrations/`, keep gated |
| `staging` | Shared helpers (config, host) | Reads `backend/.env` | `scripts/migrations/` (import root) |
| `reference` | Shared helpers (catalog) | Yes | `scripts/migrations/` |
| `booking`, `completion_business`, `completion_runner` | Evidence: synthetic business tests | Via helpers | `scripts/migrations/evidence/` |
| `runtime`, `completion_audit`, `forward_validation` | Evidence: historical runs that produced the JSON | Yes | `scripts/migrations/evidence/` |

None are obsolete outright; the last six reproduce recorded evidence and should be
kept for audit. All use `ROOT = Path(__file__).resolve().parent`. After the move:

- change `ROOT` to `parents[3]` in each script (already done in the pattern used by
  `reseal_layout_evidence.py`), or import a shared `ROOT` from `staging`;
- rewrite sibling imports to the new package path (add `__init__.py` or keep one folder
  and `sys.path` unchanged);
- re-run `python -m py_compile` on every file, then the offline ones
  (`review_bundle`, `review_validate`, `revision_runtime_review`) and diff output
  against `backend/migrations/reviews/`. Never run the DB-touching ones during the move.
- Do not add the new folder to the Docker image: `scripts/` is already in `.dockerignore`.

## 3. Evidence note

Old paths inside `reviews/` are historical. `reseal_layout_evidence.py` keeps the old
path and hash under `layout_restructure.superseded` in the two sealed JSON files. The
narrative `migration-inspection-2026-10-15.md` still names `backend/migrations/README.md`
as a file it read at the time; left as written.
