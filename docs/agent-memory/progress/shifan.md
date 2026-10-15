# Progress: shifan

## Goal
Set up the Claude Code workspace (.claude/, CLAUDE.md) and the agent-memory system.

## Status
ready for PR

## Done
- Created CLAUDE.md, .claude/settings.json, skills, commands, agents, docs/agent-memory.
- Moved the karpathy-guidelines skill to its loadable path (it was nested one level too deep).
- Kept the existing code-refactorer agent unchanged.

## In progress
- 

## Next steps
1. Confirm the assumptions in the setup report (base branch `main`, test command), then commit this setup on its own branch (not `shifan`, which also carries other work).
2. Decide what to do with the untracked root-level `migration-*` scratch files (unrelated to this change).

## Decisions
- 2026-10-15: per-branch progress files, because they mirror one-branch-one-PR and avoid teammate merge conflicts.

## Files touched
- CLAUDE.md, .claude/**, docs/agent-memory/**, .gitignore

## Blockers and open questions
- 

## Review findings
- 

## Session log
- 2026-10-15: workspace and memory setup
