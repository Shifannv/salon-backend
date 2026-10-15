---
description: Run ruff and pytest and summarize failures only. Does not fix anything.
argument-hint: "[path]"
allowed-tools: Bash(python -m ruff:*), Bash(python -m pytest:*), Read
---

Scope (empty means everything): $ARGUMENTS

From `backend/`:

1. `python -m ruff check app tests migrations` (or just the given path).
2. `python -m pytest -q` (or just the given path).

Summarize: pass or fail per tool, then each failure as `file:line  short reason`. Report the skip count and say if integration tests were skipped (no `MIGRATION_TEST_DB`). Do not fix anything unless asked.
