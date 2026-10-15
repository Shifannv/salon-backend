---
description: Review the branch diff against main using the reviewer agents in parallel. Report only; fix nothing.
argument-hint: "[optional focus]"
allowed-tools: Read, Grep, Glob, Edit, Agent, Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git merge-base:*)
---

Focus (may be empty): $ARGUMENTS

- Branch: !`git branch --show-current`
- Changed files vs main: !`git diff --name-status main...HEAD`
- Uncommitted: !`git status --short | head -20`

## Steps

1. Determine the diff: `git diff main...HEAD` plus uncommitted changes.
2. In one message, launch in parallel: `code-reviewer`, `security-reviewer`, `performance-analyst`. Also launch `migration-reviewer` if anything under `backend/migrations/` changed. Give each the diff scope and the focus.
3. Merge their results into one report with three groups: **Blocker**, **Should fix**, **Nit**. Deduplicate; keep `file:line`. If a secret was found, show its location only.
4. Save the report under "Review findings" in `docs/agent-memory/progress/{branch-slug}.md`, each as `[open] severity, file:line, summary`. Edit only that section.
5. Print the report. Do not fix anything unless the user asks.
