---
description: Write a new raw-SQL Alembic revision and have it reviewed. Never applies it.
argument-hint: "{description of the schema change}"
allowed-tools: Read, Grep, Glob, Edit, Write, Skill, Agent, Bash(git status:*), Bash(git diff:*), Bash(python -m ruff:*), Bash(python -m pytest:*)
---

Change requested: $ARGUMENTS

Apply `karpathy-guidelines` and `alembic-migration`.

1. Find the current head (newest file in `backend/migrations/versions/`) and read two recent revisions for style.
2. State assumptions and the exact SQL intent. Confirm it cannot be done without a schema change.
3. Write the revision and its tests per the skill checklist.
4. Run the `migration-reviewer` agent on the new revision and address Blocker findings.
5. Run `python -m ruff check app tests migrations` and `python -m pytest -q` from `backend/`.
6. **Never apply the migration.** Print the command for the user to run against a local DB: `cd backend && alembic upgrade head`.
