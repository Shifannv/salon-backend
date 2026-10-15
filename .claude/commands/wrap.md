---
description: End a session. Verify, update this branch's progress file, promote lasting learnings, append one SESSIONS row.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git config user.name), Bash(python -m ruff:*), Bash(python -m pytest:*), Bash(date:*)
---

Follow the `agent-memory` skill exactly.

## Live context

- Branch: !`git branch --show-current`
- Status: !`git status --short | head -40`
- Diff stat: !`git diff --stat | tail -20`
- Recent commits: !`git log --oneline -5`
- Git user: !`git config user.name`

## Steps

1. From `backend/`, run `python -m ruff check app tests migrations` and `python -m pytest -q`. Report the results. If anything fails, record it under Blockers and do not fix it.
2. Update `docs/agent-memory/progress/{branch-slug}.md`: Done, In progress, Next steps (ordered, concrete, with file paths), Decisions, Files touched, Blockers, Status, and a Session log line. Edit only this branch's file.
3. Promote to `shared/` only lasting facts that cannot be derived from code or git log (decisions, gotchas, domain-rules, conventions, roadmap). Condense any shared file that exceeds about 150 lines.
4. Append exactly one row to `docs/agent-memory/SESSIONS.md` (Session ID `YYYYMMDD-HHMM-{git user slug}`). Never touch old rows.
5. Secret-scan every memory file you touched: grep for `token|secret|password|api[_-]?key|PRIVATE KEY|eyJ|postgres(ql)?://`. Remove anything real.
6. Print a summary: what was saved where, a warning if there are uncommitted changes, and a suggested commit message. Do not commit.
