# Mumbai refresh designs — preparation only

No design is implemented. No grants, policies, triggers, publications, frontend environments or migrations are applied. Both designs keep business reads and writes authorized by FastAPI. Supabase Auth SDK use remains; media stays on R2 and Supabase Storage remains unused.

## Design 1: minimal secure Realtime access with strict RLS

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

Existing 22 mocked frontend tests pass but do not satisfy this gate. Live staging build/API binding and multi-session refresh tests remain blocked. Real cross-connection Postgres Changes delivery requires committed test mutations; an outer-transaction rollback alone cannot prove event delivery. Any such staging fixture lifecycle must be separately scoped with synthetic records and verified cleanup. Current work creates no new persistent records.

Required next approval: select a design (recommend design 2), authorize the corresponding frontend/backend implementation scope and identify isolated Mumbai staging builds/API for acceptance testing. This is separate from migration execution approval. All 0038–0040 remain uncommitted and unapplied, and no Alembic stamp is authorized.
