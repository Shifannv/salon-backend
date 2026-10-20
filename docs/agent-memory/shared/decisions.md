# Decisions

Format: date | decision | reason. Newest last.

- 2026-10-15 | Agent memory is per-branch progress files plus shared durable files | Mirrors one-branch-one-PR; no teammate merge conflicts.
- 2026-10-15 | Review agents are read-only | They must not quietly change code mid-review.
- 2026-10-15 | Existing `code-refactorer` agent kept as-is | Already tailored to this repo; setup must not overwrite files.
- 2026-10-19 | Image `result_url` is a separate read-only token, never the PUT URL | A shared token made the read link an upload capability and let a stored upload report 422.
- 2026-10-19 | `media-cleanup` Compose healthcheck stays disabled until tested | The deploy script's `up --wait --wait-timeout 120` would fail on a slow first sweep.
- 2026-10-19 | Emergency financial repair: one super-admin with `aal2` plus audit, no two-person approval | One operator team; owner decision U06/TA07.
