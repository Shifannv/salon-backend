# Mumbai refresh designs — preparation only

Later implementation of design 2 is recorded in [Mumbai local refresh results](mumbai-local-refresh-results-2026-10-15.md). This document preserves the design-stage reasoning; migration acceptance remains held under the limits in that report.

No design is implemented. No grants, policies, triggers, publications, frontend environments or migrations are applied. Both designs keep business reads and writes authorized by FastAPI. Supabase Auth SDK use remains; media stays on R2 and Supabase Storage remains unused.

## Design 1: minimal secure Realtime access with strict RLS

### Compatibility boundary for existing Postgres Changes

Application-row SELECT is a data-access capability even when the normal callback ignores the payload. RLS limits rows, not sensitive columns. A safe grant review must test direct REST/SQL reads as well as events; frontend filters and callback behavior cannot enforce confidentiality.

The smallest candidate inventory for retaining any existing channels is below. It is a conditional alternative requiring an explicit change to the FastAPI-only read contract, not an approved grant plan:

| Table | Candidate recipient scope | Prerequisites before any positive SELECT |
| --- | --- | --- |
| bookings | Customer's own rows; currently owned salon's rows for owner | Review every exposed column; replace/reconcile all applicable policies and resolve helper/staff dependencies without broad staff/profile reads |
| notifications | `user_id = auth.uid()` only | Review payload columns and all applicable policies; add publication membership only after review |
| blocked_slots | Owner's salon-wide rows or staff rows proven to belong to that owner's salon | Remove broad `blocked_read USING(true)` access; review ALL policies too; verify staff-only rows with NULL salon_id; customers use API availability |
| salons | At most owner-only rows for this invalidation use case | Avoid granting customer access to whole salon rows just to refresh opening state; customers poll API; review helper dependencies and publication |

Only authenticated SELECT on an explicitly reviewed column allowlist could be considered, with named schema/helper rights only where proven necessary. No anon/PUBLIC grants, writes, business RPC execution, future-object defaults or broad dependency grants. Confirm installed Realtime/SDK support for the exact column privileges, filters and payload before relying on column-level grants. If that combination fails, reject this variant rather than widening access. Review INSERT/UPDATE independently; do not rely on DELETE filtering/RLS for confidentiality or refresh recovery. Handle soft-deactivation and access-revoking updates by periodic API reconciliation because a row leaving readable scope may not deliver a usable event.

This variant cannot safely enable the unchanged customer availability channels: strict own-booking RLS intentionally hides competitors' bookings, while its salon-only block filter misses staff-only blocks. It also cannot survive 0040 unchanged: that revision revokes these application-table rights. Retaining any such grants would require a separately reviewed revision/security decision and new expected-head proof. No grant followed by blindly applying 0040 is a compatible rollout.

### Safe design under the current FastAPI-only contract

Use private Broadcast for cache invalidation rather than existing application-table Postgres Changes. This preserves zero client application-table grants. Retaining the current channels would require application SELECT grants and policy/dependency changes; that conflicts with the architecture decision and is not proposed for execution.

After a successful business transaction commits, FastAPI publishes a small invalidation hint to each currently authorized recipient's private topic `user:<verified UUID>:events`. Determine recipients server-side from current ownership/account status. Hint payload contains an allowlisted resource kind and protocol version only; exclude booking contents, names, contact details, free text, payment values and other users' identifiers. The receiving client refetches through FastAPI. A hint never grants data access.

Use an after-commit sender with failure monitoring for best-effort hints; durable delivery would need a separately reviewed outbox/worker change. Never publish before commit, or use SQL triggers that send uncommitted/rolled-back state. Worker-originated mutations must participate too. Private channels use strict topic ownership and extension=broadcast RLS on realtime.messages; reject anonymous access, client publishing and Presence. Review existing permissive policies so another policy cannot allow broader access. Supabase evaluates channel permissions at join, so do not assume continuous membership enforcement: publish only to currently authorized recipients, reauthenticate/rejoin on token changes, disconnect on logout and handle revocation explicitly. [Realtime authorization](https://supabase.com/docs/guides/realtime/authorization), [Broadcast](https://supabase.com/docs/guides/realtime/broadcast).

Candidate privilege inventory (design scope, not executable SQL):

| Object | Grantee | Privilege/action | Reason | Existing objects only | Future objects |
| --- | --- | --- | --- | --- | --- |
| realtime.messages | authenticated | Receive authorization via SELECT and a narrowly scoped Broadcast policy; first inspect current managed ACL | Receive own private invalidation topic only | Yes, this named managed table | None |
| realtime.topic() and auth.uid() | authenticated | Retain/verify existing EXECUTE; a missing right would require separate explicit review | Compare topic to verified subject | Named existing helper signatures only | None |
| public application tables | anon/authenticated/PUBLIC | No positive grants | FastAPI remains business interface | No change | None |
| application functions | anon/authenticated/PUBLIC | No positive EXECUTE grants | No client RPC for business operations | No change | None |
| realtime.messages | anon; client authenticated send operations | No new send/anonymous privileges or allow policies | Prevent topic spoofing and client-generated hints | Named object only | None |

No global function/default grants. No extra profile-lookup function is required for the basic subject-equals-topic rule; current recipient authorization stays in FastAPI. Before implementing, inspect effective managed schema USAGE, helper EXECUTE and table ACLs; grant only a demonstrably missing named right through separate review. Do not alter managed-table ownership, enable RLS again on realtime.messages, or create objects in the managed realtime schema. RLS is already enabled and policy management has special Supabase support. [Managed schema restrictions](https://supabase.com/docs/guides/realtime/authorization).

Switch frontend hooks to private Broadcast with status/error handlers, deduplicated invalidations and a foreground API polling safety net. Refresh immediately after a successful rejoin to recover missed hints. Continue polling availability: exposing other customers' booking events, or distributing unfiltered blocks to booking clients, is unnecessary. Poll public salon visibility/status too. A join failure must reduce freshness latency, never block business reads.

Tradeoff: faster authorized invalidation, but requires backend publish integration, frontend channel changes, managed-policy review and real staging WebSocket tests. Existing subscriptions cannot be enabled safely merely by applying grants. Rollback disables hint publishing/subscriptions while retaining API refresh; remove only new, named policies/rights after verifying managed dependencies. Never restore broad table grants.

## Design 2: FastAPI refresh and invalidation — recommended

Retain zero business-table grants and disable/remove Postgres Changes cache hooks in a separately approved frontend change. Reuse owner operational polling; extend customer and owner gaps instead of introducing a second data authorization path.

Proposed foreground-only refresh contract:

| Visible data | Proposed maximum normal polling interval | Additional refresh |
| --- | --- | --- |
| Customer appointment list and inbox; owner bookings, inbox and pending requests | 30s | Screen entry, reconnect, resume, local successful mutation |
| Customer/owner mounted availability | 10s | Staff/date/service change, relevant mutation, conflict response |
| Customer active booking details | Retain existing 10s | Relevant mutation; terminal state final refresh |
| Customer booking confirmation | Retain existing 3s bounded confirmation loop | Stop after confirmed terminal result/timeout |
| Salon status, owner access state and relevant collection summaries | 30s | Resume, reconnect and mutations affecting that state |
| Owner blocks/holidays | Reuse current 30s operational route polling | Block changes also invalidate availability |

Intervals are proposed acceptance targets, not measured guarantees under outage. Keep one deduplicated request per query key, authenticated user/salon-scoped caches, cancellation on logout/navigation, jitter and bounded retry/backoff for reads. Pause while hidden/background/offline. On resume/reconnect force active relevant queries fresh rather than relying on five-minute stale time. Refetch authorization-sensitive state before enabling privileged actions. Preserve backend conflict/ownership checks; never automatically replay booking/payment writes due to polling failures.

Wire mutation invalidation explicitly across bookings, availability, access state, requests, notifications and collection summaries as appropriate. Do not assume a successful bookings poll invalidates other caches. User/salon switch must clear or partition caches; in-flight old-session responses must not populate the new session. Expose a stale/offline indicator and manual refresh when requests fail. Use server error handling without leaking SQL details. Conditional requests can be considered later if endpoints implement them; they are not assumed today.

Privilege inventory: no new database, schema, table, function, sequence, publication or future-object privileges. Auth operations continue through Supabase Auth. Preserve R2 flows and existing authentication redirects. Supabase Storage stays unused. No production configuration changes are part of this design.

Tradeoff: predictable refresh without database event access; higher API read load and up to one interval of normal staleness. Measure endpoint concurrency/load before choosing final cadence. Rollback a frontend refresh change only to a verified refresh-capable build; reverting to the known stale behavior is not an acceptable prerequisite for 0040.

## Required Mumbai staging acceptance gate for either design

1. Bind exact customer/owner build commits and API base URLs to Mumbai. Inspect network destinations without logging tokens. Do not test unknown production API endpoints. Current Vercel homepage is insufficient proof.
2. Use two isolated customers and two owners/salons. Test account and tenant isolation through FastAPI; cross-account requests must remain denied. Direct application-table access must still return expected 42501.
3. Keep relevant screens mounted. From a second session create/cancel/reschedule/complete bookings; change salon-wide and staff-specific blocks; create notifications and action requests. Verify list, detail, availability, access state and collection summaries update within the selected contract without navigation.
4. Disable WebSockets and simulate CHANNEL_ERROR/TIMED_OUT/CLOSED. Verify polling succeeds, reconnect forces refresh and missed events are recovered. For design 2 prove the app works with all Realtime connections absent.
5. Background/resume, offline/reconnect, token refresh, logout/login and salon switch: no old-session data flashes, duplicate loops, stale privileged controls or write retries. Verify denied API responses remove inaccessible cached records.
6. Design 1 additionally tests own-topic allow, foreign-topic deny, anonymous deny, client-send deny, old-token/revocation handling, no row/personal payloads, rollback producing no published hint and correct after-commit delivery. Negative policy tests must account for all permissive policies.
7. Verify Auth login/refresh/callbacks and R2 media behavior independently. Supabase Storage remains unused. Verify booking conflicts and owner collection/worker behavior without calling real payment/email/push providers.

Recorded results show 22 mocked frontend tests passed; source hashes still match, but tests were not rerun in this documentation-only revalidation. They do not satisfy this gate. Live staging build/API binding and multi-session refresh tests remain unverified. Real cross-connection Postgres Changes delivery requires committed test mutations; an outer-transaction rollback alone cannot prove event delivery. Any such staging fixture lifecycle must use an isolated authorized target, synthetic records and verified cleanup. Current work creates no new persistent records.

For each staging case, record build commits, target/API identity, selected design and interval, actor aliases, mounted screen/query family, mutation commit time, API response time, visible update time, event/error status and pass/fail. Store no tokens or personal payloads. Acceptance latency is the chosen interval plus measured API/render time under healthy foreground conditions; record those times separately. Fault cases must show recovery after service returns and visible stale/error state during failure. A missing result is pending, not a pass.

| Release requirement | Current result |
| --- | --- |
| Customer and owner exact staging build/API binding | Pending |
| Mounted list/detail/availability/inbox/access/summary refresh across two sessions | Pending; known source gaps above |
| Two-customer/two-owner isolation, logout/switch and token lifecycle | Pending |
| WebSocket failure/offline/reconnect recovery | Pending |
| Design 1 private-topic authorization and after-commit delivery, if chosen | Pending |
| Reviewed expected-head/schema/ACL comparison | Pending independently of refresh |

**0040 remains on hold.** Both customer and owner must pass the selected design's staging cases before any proposal to apply it. Passing refresh does not authorize migration execution or stamping. Re-read live ACL/publication evidence at that point; publication membership or a SUBSCRIBED status alone is not proof of data delivery or compatible refresh.

Recommended implementation: design 2, FastAPI refresh/invalidation. Design 1 private Broadcast remains the secure Realtime alternative. Identify isolated Mumbai staging builds/API before running acceptance; neither design is implemented by this review. No commit, migration execution or Alembic stamp is authorized. On revalidation the six 0038–0040 files were already tracked in Git HEAD; they were left untouched, and no database application was attempted. See the audit for this correction to the older Git-uncommitted claim.
