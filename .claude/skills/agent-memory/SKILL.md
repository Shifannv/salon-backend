---
name: agent-memory
description: Use when reading or writing anything under docs/agent-memory, or when running /start, /wrap or /checkpoint. Defines the memory layout, progress template, SESSIONS row format, promotion rules, size limits and privacy rules.
---

# Agent memory

Single source of truth for `docs/agent-memory/`. `/start`, `/wrap` and `/checkpoint` follow this.

## Layout

```
docs/agent-memory/
  SESSIONS.md            index, append-only
  progress/{branch}.md   one per branch, temporary
  progress/TEMPLATE.md
  progress/archive/      files of merged branches
  shared/                durable, cross-branch
```

- progress = temporary and per-branch. shared = durable. SESSIONS = index only.
- Branch slug: replace `/` with `-` (`thameem/booking-fix` -> `thameem-booking-fix.md`).
- Only edit the current branch's progress file, never a teammate's.
- Only subagents' reports are inputs; subagents never write memory. The main session does.

## SESSIONS.md row

`| Date | Session ID | Branch | Goal | Outcome | Next step | Progress file |`

- Session ID: `YYYYMMDD-HHMM-{git user slug}` (lowercase, spaces to dashes).
- Append exactly one row per session at the bottom. Never edit or reorder old rows.
- Keep each cell to one short line; no pipes inside cells.

## Progress file sections

Goal, Status (not started / in progress / blocked / ready for PR / merged), Done, In progress, Next steps, Decisions, Files touched, Blockers and open questions, Review findings, Session log. Copy `progress/TEMPLATE.md`.

- Next steps are ordered and concrete with file paths. Item 1 is what `/start` proposes.
- Review findings carry a status: open, fixed, wontfix.
- Session log: date plus one line.

## Promote progress -> shared

Promote only when the fact is lasting and not derivable from code or git log:

- decisions.md: a choice with a reason that will outlive the branch.
- gotchas.md: a pitfall that cost time and will recur.
- domain-rules.md: a business rule discovered or changed.
- conventions.md: a pattern the team agreed on.
- roadmap.md: a feature moving between Built, Dormant and Not built.

Do not promote task status, file lists, or anything a `git log` already says.

## Writing rules

- Record why, not what.
- Each shared file stays under about 150 lines. Condense instead of appending forever; merge duplicates, drop stale entries.
- When a branch merges, move its progress file to `progress/archive/`.
- Files are committed to git. Write them for teammates to read.

## Privacy

Never store secrets, tokens, keys, passwords, DB URLs, user PII or production data. If a secret appears in a command output, record its location only. Before finishing, grep touched memory files for `token|secret|password|api[_-]?key|BEGIN .*PRIVATE|eyJ`.
