---
description: Quick mid-session save to this branch's progress file. Use before /compact or /clear.
allowed-tools: Read, Edit, Bash(git branch:*), Bash(git status:*)
---

Follow the `agent-memory` skill.

- Branch: !`git branch --show-current`
- Status: !`git status --short | head -20`

Update only `docs/agent-memory/progress/{branch-slug}.md`:

1. Done: add what was completed since the last save.
2. Next steps: rewrite as an ordered, concrete list with file paths.
3. Decisions: add any decision made, with the reason.

Do not append to SESSIONS.md. Do not touch `shared/`. Do not run tests. Reply with one line saying what was saved.
