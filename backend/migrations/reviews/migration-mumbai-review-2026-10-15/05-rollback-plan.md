# Rollback / recovery

Nothing executed: rollback currently unnecessary. Observed Mumbai already has the two
columns, restricted client ACLs, named server grants, function config and signup trigger.
All three drafts predict a no-op there; prove this again immediately before any later
execution. Disposable-database behavior/ACL tests remain outstanding.

Before any approved execution, independently verify Mumbai and capture exact columns,
relation/column/function ACLs with grantors/options, defaults, function owner/body/config,
and signup trigger definition/state. Keep source/bundle hashes. Abort on unreviewed drift;
never use today's snapshot to blindly undo later changes.

Each file owns one transaction with 5s lock_timeout and 60s statement_timeout. Use a
client that stops at the first error. On error before COMMIT, issue
90-rollback-open-transaction.sql on the SAME connection. Disconnect also rolls back an
open transaction. Never let an error-ignoring client continue subsequent statements.

| File | Observed-Mumbai effect | Post-commit recovery |
| --- | --- | --- |
| 01 schema | Expected no-op | Retain both columns. No DROP, clearing values or narrowing types. Even on a fresh reference where added, preserve them and prepare a reviewed forward fix. |
| 02 security | Expected no-op | Retain deny-by-default; never re-grant broad backup rights. Any compensating patch must name exact object/grantee rights from an immediately captured approved before-state and receive separate security approval. |
| 03 signup | Expected no-op | Keep existing trigger. No DROP/DISABLE. If creation was needed elsewhere, review a forward repair rather than automatically breaking profile creation after signups. |
| History plan | No operation | No reversal needed. Future stamp reversal is a separately approved exact metadata operation. |

The only executable recovery SQL supplied is ROLLBACK for an uncommitted transaction.
No safe generic post-commit DROP/regrant/destructive downgrade exists under the user's
constraints. If non-destructive recovery cannot be met, do not apply the migration.

Managed extension ACLs, defaults, roles/memberships must compare unchanged before/after.
Owner/backend/service-role access must survive, including sequence access if any appear
(currently none). Recovery remains Mumbai-only; no project reset, personal-data restore,
infrastructure action, production deployment or traffic switch.
