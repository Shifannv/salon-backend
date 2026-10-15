---
description: Begin a session. Load memory, report branch state and propose the first next step.
argument-hint: "[optional task]"
allowed-tools: Read, Write, Edit, Glob, Bash(git status:*), Bash(git branch:*), Bash(git log:*), Bash(git rev-parse:*), Bash(tail:*)
---

Follow the `agent-memory` skill. Task from the user (may be empty): $ARGUMENTS

## Live context

- Branch: !`git branch --show-current`
- Status: !`git status --short | head -30`
- Last 5 commits: !`git log --oneline -5`
- Last 8 sessions: !`tail -n 8 docs/agent-memory/SESSIONS.md`

## Steps

1. Read `.claude/skills/senior-backend-engineer/SKILL.md` first and follow it for the whole session. Then read `docs/agent-memory/shared/README.md`, then `architecture.md` and `gotchas.md`. Read other shared files only if the task needs them (domain-rules for booking/payment/auth, conventions for endpoints/tests, commands for running things).
2. Branch slug = branch name with `/` replaced by `-`. Look for `docs/agent-memory/progress/{slug}.md`.
   - If the branch is `main` (the base branch), say so and ask for the task and a branch name. Do not create a progress file.
   - If the file is missing, create it from `progress/TEMPLATE.md` with the branch name and the task as Goal.
   - If a progress file belongs to a branch already merged into `main`, suggest moving it to `progress/archive/`. Do not move it yourself.
3. Report in at most 10 lines: branch, status, what the last session achieved, next steps, blockers, uncommitted changes, and anything stale or contradictory (e.g. progress says done but git status disagrees).
4. If a task was given, treat it as the goal and update Goal in the progress file. Otherwise propose Next steps item 1 and wait for the user's go.
5. Add `- {date}: session started` to the progress file's Session log.

Do not start coding. Do not scan the whole repo.
