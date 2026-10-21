# Decisions

Format: date | decision | reason. Newest last.

- 2026-10-15 | Agent memory is per-branch progress files plus shared durable files | Mirrors one-branch-one-PR; no teammate merge conflicts.
- 2026-10-15 | Review agents are read-only | They must not quietly change code mid-review.
- 2026-10-15 | Existing `code-refactorer` agent kept as-is | Already tailored to this repo; setup must not overwrite files.
- 2026-10-19 | Image `result_url` is a separate read-only token, never the PUT URL | A shared token made the read link an upload capability and let a stored upload report 422.
- 2026-10-19 | `media-cleanup` Compose healthcheck stays disabled until tested | The deploy script's `up --wait --wait-timeout 120` would fail on a slow first sweep.
- 2026-10-19 | Emergency financial repair: one super-admin with `aal2` plus audit, no two-person approval | One operator team; owner decision U06/TA07.
- 2026-10-21 | Graph audit decision — defer cleanup and refactoring until post-deployment stabilization: keep `backend/app/application/ports/email_gateway.py` unchanged (future port, ResendEmailGateway not wired now); no Graphify-driven deletion, wiring, rename or refactor; `http_exception_handler` stays (decorator registration is runtime use); `PlatformRepository`/`OwnerUseCases` split deferred to a separately approved refactor; isolated-symbol/docs gaps (for example `COMPOSE_ENV_FILE`) need deployment-owner evidence before any compose, env or doc change; graph-inferred edges are not proof of coupling; no API, payment, notification, Redis or frontend contract is removed | Backend is being finalized for deployment and frontend wiring; graph signals are review hints, not authorization. Future agents: search memory first, do not re-ask or duplicate this entry; raise again only on runtime evidence, a failing test, a security issue or a confirmed API-breaking change.
