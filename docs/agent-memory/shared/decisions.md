# Decisions

Format: date | decision | reason. Newest last.

- 2026-10-15 | Agent memory is per-branch progress files plus shared durable files | Mirrors one-branch-one-PR; no teammate merge conflicts.
- 2026-10-15 | Review agents are read-only | They must not quietly change code mid-review.
- 2026-10-15 | Existing `code-refactorer` agent kept as-is | Already tailored to this repo; setup must not overwrite files.
