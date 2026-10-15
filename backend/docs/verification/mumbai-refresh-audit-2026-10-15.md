# Mumbai customer and owner refresh audit

Implementation follow-up: [Mumbai local refresh results](mumbai-local-refresh-results-2026-10-15.md). The findings below describe the pre-implementation audit; use that report for current implementation and acceptance limits.

Status: review only; compatible API refresh behavior must be verified first. The latest user instruction holds 0038–0040 and specifically prohibits applying 0040 before customer and owner refresh passes staging tests. No frontend source, settings, grants, publication, or infrastructure changed during this audit.

Revalidation on 2026-10-15: the working tree started clean on branch `shifan`, and all six 0038–0040 Python/SQL migration files were already tracked in HEAD. Thus the earlier claim that these files are Git-uncommitted is stale. This audit makes no commits, rewrites no history and changes no migration files. Database non-application is supported by the recorded rollback/history evidence, not a fresh live database query in this revalidation.

## Evidence and source scope

Inspected customer checkout: `D:/salon/Salon-Customer-APP/customer-app`. The supplied `D:/salon/customer-app` does not exist. Owner: `D:/salon/salon-owner-APP`. Website/admin: `D:/salon/salon-QR-Walking-Web/walking-customer-web`.

File hashes are in `migration-mumbai-refresh-source-inventory-2026-10-15.json` in `backend/migrations/reviews/`. Branch/commit and deployed staging build identity were not verified; user-reported branch is `shifan`. The supplied GitHub OWNER/REPO URL is a placeholder. Findings describe local source, not proof of the Vercel deployment's API configuration.

All 16 inventoried customer/owner source hashes still match on revalidation. Subscription implementations, polling configuration and lifecycle hooks were reread. Frontend build identity and staging API binding remain unverified; the backend branch above does not establish either frontend branch.

Inspected business requests use FastAPI (website/admin through its API/BFF where applicable). Supabase SDK Auth remains separate. No application-table `.from()`/`.rpc()` business calls were found in the inspected source. Existing Postgres Changes subscriptions are direct application-table consumers even though callbacks only invalidate caches. R2 remains the media backend; Supabase Storage stays unused.

## Subscriptions and cache effects

Customer paths below are relative to its checkout; owner paths are relative to its checkout.

| App / source | Table and channel filter | Callback/cache effect | Failure fallback and gap |
| --- | --- | --- | --- |
| Customer `src/services/supabase/realtime.service.ts`, `AppointmentListScreen.tsx` | bookings, customer_id=self | Invalidate appointment list; screen coalesces updates | Focus invalidation exists; mounted list has no periodic refresh |
| Customer same service, booking detail query | bookings, id=booking | Refetch/invalidate own booking | Foreground detail polls every 10s while active or request pending; terminal details may stop |
| Customer same service, `SelectDateTimeScreen.tsx`, ModifyBookingStep | bookings, staff_id=selected staff | Invalidate/reload availability | No periodic availability refresh; cannot receive other customers' bookings under own-booking RLS |
| Customer same availability channel | blocked_slots, salon_id=selected salon | Same availability invalidation | Misses staff-specific blocks with NULL salon_id even if grants were added |
| Customer same service, `NotificationProvider.tsx` | notifications, user_id=self | Invalidate inbox/unread queries | Push can invalidate when available; not a guaranteed fallback, no periodic inbox query |
| Customer same service, `useSalonOpenStatus.ts` | salons, id=salon, UPDATE | Fetch current salon status | Minute clock recalculates cached opening hours; does not refresh server status |
| Owner `src/hooks/useRealtimeSync.ts` | bookings, salon_id=own salon | Bookings, access state, availability | Bookings API polling exists; polling bookings does not inherently invalidate the other query families |
| Owner same hook | notifications, user_id=self | Inbox, bookings, access state, pending action requests | Inbox and action-request API polling exists; access-state coupling still needs verification |
| Owner same hook | blocked_slots, no filter | Blocks and availability | Blocks/holidays polling exists on relevant routes; mounted availability itself has no interval |

Both subscription implementations omit asynchronous subscribe-status handling. Customer shares channels, debounces 150ms and catches synchronous construction failures; owner removes channels on cleanup. Neither explicitly handles CHANNEL_ERROR/TIMED_OUT/CLOSED by activating a verified fallback.

Correction to the initial dependency finding: owner refresh does not depend exclusively on Realtime. `src/lib/operational-polling.ts` defaults to 30s, configurable within 10–120s, pauses background polling, and requests mount/focus/reconnect refresh. Bookings, blocks/holidays, notifications and action requests use it. `useQueryLifecycle` is mounted by `app/_layout.tsx` and wires AppState/NetInfo. `useWalkin.ts` availability has no interval; cross-query invalidation still needs tests. Comments in useRealtimeSync saying “without polling” do not describe all current behavior.

Customer's query client defaults to five-minute stale time with mount/reconnect/focus refetch. Native focus wiring is mounted, but stale time and missing intervals prevent a guarantee of fresh data while a screen remains open. Confirmation polls every 3s; that does not cover list, availability, inbox or salon-state freshness.

Website `lib/qr/queries.ts` already polls availability (default 30s, configurable 10–300s), salon data (60s), and pending booking (15s), with lifecycle refresh. Admin `lib/api/admin.ts` uses `/api/admin/proxy/admin`. No Postgres Changes subscriptions were found in the inspected web source.

## Mumbai privileges, RLS and publication

Evidence: `backend/migrations/reviews/migration-mumbai-refresh-permissions-2026-10-15.json`. Effective SELECT is false for anon and authenticated on bookings, blocked_slots, notifications, salons and staff. Direct client SQLSTATE 42501 is expected; no grant is proposed to make direct-client tests pass.

These are recorded catalog findings. No live ACL, RLS, publication or Alembic query was rerun in this revalidation. Refresh this evidence against the isolated staging target before acceptance.

| Table | SELECT required by existing Postgres Changes design | Current relevant RLS | Publication |
| --- | --- | --- | --- |
| bookings | authenticated SELECT on subscribed fields; policy dependencies must also be callable/readable | Customer=self OR owns_salon OR superadmin; staff policy queries staff | Present |
| blocked_slots | authenticated SELECT; current broad policy must first be replaced if access architecture changes | blocked_read USING(true); owner-write is another permissive policy | Present |
| notifications | authenticated SELECT plus user-scoped policy | notifications_own user_id=auth.uid() | Absent |
| salons | SELECT for subscribed fields, with dependency review | Approved active complete salons OR owner OR superadmin | Absent |

Bookings policies call owns_salon/is_super_admin; staff policy reads staff, whose restrictive approval policy reads salons. Existing application helper EXECUTE is denied to clients. Granting only bookings SELECT is therefore not a complete safe design. Broad dependency grants would expose additional data and violate the FastAPI-only contract.

Channel filters are not authorization. Existing unfiltered owner blocks would expose all matching readable rows under USING(true) if SELECT were added. Customer availability also cannot depend on receiving another customer's booking row. Even corrected own-row RLS cannot solve that freshness requirement safely.

Postgres Changes checks SELECT/RLS; current docs also describe field projection, which would need installed SDK compatibility and payload tests before relying on it. DELETE events have special filtering/RLS limitations. These considerations reinforce using API refresh or private invalidation instead of granting access to business rows. [Supabase Postgres Changes](https://supabase.com/docs/guides/realtime/postgres-changes).

## Verification performed

Recorded Jest tests ran without cache or frontend dotenv loading. JSON outputs are in `backend/migrations/reviews/`:

| Output | Suites/tests | Result | Limit |
| --- | --- | --- | --- |
| migration-mumbai-customer-refresh-tests-2026-10-15.json | 2 / 5 | PASS | Mock shared-channel lifecycle/debounce and query behavior |
| migration-mumbai-owner-refresh-tests-2026-10-15.json | 3 / 16 | PASS | Mock polling, Realtime invalidation and booking hooks |
| migration-mumbai-owner-lifecycle-tests-2026-10-15.json | 1 / 1 | PASS | Mock native focus/reconnect wiring |

The recorded results show 22 tests passed. They were not rerun for this documentation-only revalidation. React test-renderer/act and Node warnings occurred; no failed assertions. These tests do not prove cross-device freshness, channel-error recovery, API deployment binding, real RLS event delivery or actual Mumbai device/browser behavior. No live staging refresh pass is claimed.

Next: review [the two designs and acceptance gate](mumbai-refresh-designs-2026-10-15.md). Keep migrations held until approved frontend compatibility work passes that gate.
