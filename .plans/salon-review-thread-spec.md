# Super-admin to owner review thread (spec; design, not built)

| | |
|---|---|
| **Date** | 2026-10-22 |
| **Status** | Design only. No code, no migration file. |
| **Source** | Interview with the product owner, 2026-10-22 |
| **Builds on** | [SALON_APPROVAL.md](../backend/docs/SALON_APPROVAL.md) |

## Problem

An owner who finishes onboarding waits for the super-admin. Today the super-admin can only approve, or reject with **one** `rejection_reason` (`backend/app/application/use_cases/admin.py:202-218`). There is no way to say "fix your photos and your working hours" without rejecting the salon, and no history of what was asked.

## Decisions (from the interview)

| Question | Decision |
|---|---|
| Can the owner reply? | **No.** Read-only. The owner fixes the onboarding and resubmits. |
| Does a message point at a field? | **Yes, optionally**, with one of the six existing setup-checklist keys: `profile_basics`, `working_hours`, `photos`, `services`, `staff`, `payout` (`backend/app/api/v1/schemas/platform.py:963`). |
| Does the approval status change? | **No.** The salon stays `pending` while requests are open. No new status, no enum change. `rejected` keeps its meaning (a final no). |
| How is a request closed? | Only the super-admin marks it resolved. **Approving the salon closes every open request.** |
| Sent how? | One **review** holds many requests, sent together, so the owner gets one notification, not one per request. |
| Edit or delete? | **Append-only.** Text never changes. A mistake is withdrawn, and the withdrawn request stays on record. |
| Reject? | Still fills `rejection_reason` exactly as today (current clients keep working). It also records a "rejected" entry in the thread and closes open requests. |
| Notification? | In-app plus push, email, and polling by the waitlist screen. |
| After approval? | The owner no longer sees the history. It is kept for the super-admin. |

## Review of the decisions

- **No `changes_requested` status** is the right call: every client would otherwise have to learn a new value, and the enum change needs a migration. The owner app and website can show "action needed" from `open_review_count > 0`.
- **Hiding history after approval** means an owner cannot look back at what was asked. That is acceptable, but the super-admin's audit copy is then the only record. When the owner deletes their account the thread is erased with the salon data (see Erasure).
- **Email** depends on an email provider that is not wired yet (`docs/agent-memory/shared/decisions.md`, 2026-10-21). The row is queued now and delivered when the provider exists. Until then the push and in-app notice carry the message.
- **Operating cost.** Each review is manual super-admin work. With no reply channel, an owner who is confused has to contact support (`/v1/support/tickets`). That is acceptable at launch volume. Re-evaluate if reviews take more than one round on average.
- **Skill coverage.** `CLAUDE.md` asks for the founder skills on a new feature. The `founder-board` and `founder-ops` agents were not run for this spec (the earlier specialist agents hit a usage limit); the assessment above is the author's. Run `founder-board` before building.

## Data model (proposal)

Two backend-only tables: RLS on, `anon` and `authenticated` revoked, `service_role` granted, like the payment tables.

**`salon_review_rounds`** (one per review sent)

| Column | Notes |
|---|---|
| `id uuid primary key` | |
| `salon_id uuid not null` | references `salons(id)` |
| `kind text not null` | `changes_requested` or `rejected` |
| `created_by uuid` | the super-admin; set null if that account is erased |
| `created_at timestamptz not null default now()` | |

**`salon_review_items`** (one per request)

| Column | Notes |
|---|---|
| `id uuid primary key` | |
| `round_id uuid not null` | references the round |
| `salon_id uuid not null` | denormalised for the owner query and erasure |
| `section text` | null, or one of the six checklist keys (a check constraint) |
| `body text not null` | 1 to 1000 characters |
| `status text not null default 'open'` | `open`, `resolved` or `withdrawn` |
| `resolved_by uuid`, `resolved_at timestamptz` | |
| `resolution text` | `manual`, `approved` or `rejected` |

A trigger rejects any change to `body`, `section`, `round_id` and `salon_id`, and allows `status` to move only from `open` to `resolved` or `withdrawn`.

Index: `(salon_id, status)`. The owner list and the open count both filter on it.

## API (explicit `response_model`, status codes and `UUID` IDs)

**Super-admin** (`require_role(super_admin)` with `aal2`)

| Route | Behaviour |
|---|---|
| `POST /v1/admin/salons/{salon_id}/reviews` (201) | Body: `items: [{section?, body}]` (1 to 20). `Idempotency-Key` required. Only while the salon is `pending`, else 409. Creates the round and items, one notification, one email-outbox row. |
| `GET /v1/admin/salons/{salon_id}/reviews` | The whole thread, newest first, including resolved and withdrawn items. |
| `POST /v1/admin/review-items/{item_id}/resolve` | `open` to `resolved`, resolution `manual`. Repeat is a no-op. |
| `POST /v1/admin/review-items/{item_id}/withdraw` | `open` to `withdrawn`. |

**Owner**

| Route | Behaviour |
|---|---|
| `GET /v1/salons/me/reviews` | The owner's own salon only. Open and resolved items while the salon is not approved. **An empty list once approved**, so clients need no special case. |
| `GET /v1/salons/me` (additive) | New field `open_review_count: int`, so the waitlist screen can poll one cheap route. |

**Existing routes that change**

- `POST /v1/admin/salons/{id}/approve` closes open items (`resolution = 'approved'`).
- `POST /v1/admin/salons/{id}/reject` records a `rejected` round and closes open items (`resolution = 'rejected'`). `rejection_reason` behaves as today.

## Authorization

- Owner: reads only the salon where `owner_id` is the actor; a staff or customer gets 403, and a salon that is not theirs returns 404 (no existence leak).
- Super-admin: the role comes from `profiles`, never from the token, and `aal2` is required.
- All checks live in the use case, not the router or repository (`AGENTS.md` rule 13).

## Notifications

Reuse the existing notification type `approval_status`, with `data = {status: "changes_requested", round_id, open_count}`. Push goes through the existing outbox (`PlatformRepository._insert_notification_outbox`). The email row goes into `email_events` with event key `salon_review:{round_id}`, which makes it exactly-once. Do not repeat a notice for an idempotent retry.

## Live status

Polling first: the waitlist screen polls `GET /v1/salons/me` and compares `open_review_count` and `approval_status`. Realtime on these tables is **not** proposed: `backend/docs/verification/mumbai-refresh-designs-2026-10-15.md` records that row-level security limits rows, not columns.

## Erasure

- Both tables join `SALON_CASCADE_TABLES` (`backend/app/infrastructure/db/repositories/account_deletion_repository.py:28`), so owner deletion removes the thread.
- `created_by` and `resolved_by` are nulled when a super-admin account is erased (`erase_profile_references`).
- Classify `body` in `COLUMN_TREATMENT` (`backend/tests/integration/test_account_deletion_sql.py`); the guard test fails until someone does.

## Migration outline (not a migration file)

One revision after `0040_fastapi_only_access`, owned by the migration owner, with the release policy and deploy workflow updated for the new head. Same ordering constraint as [ACCOUNT_DELETION_FINANCIAL_PURGE_DESIGN.md](../backend/docs/ACCOUNT_DELETION_FINANCIAL_PURGE_DESIGN.md); the two could share one revision.

## Tests required

- Role matrix: owner reads only their own salon; staff and customer are denied; a super-admin without `aal2` is denied.
- Create review: validation (section key, body length, 1 to 20 items), 409 when the salon is not `pending`, idempotent retry, one notification per round.
- Append-only: the body cannot change; `status` moves only `open` to `resolved` or `withdrawn`.
- Approve closes open items; reject closes them and still fills `rejection_reason`.
- After approval the owner list is empty.
- Erasure removes the thread.
- `open_review_count` on `GET /v1/salons/me` is correct and additive (existing fields unchanged).

## Client impact (for the update lists)

- **Owner app and website owner workspace:** show the thread on the waitlist screen from `GET /v1/salons/me/reviews`; link each item to its checklist row by `section`; poll for changes.
- **Website super-admin:** a review screen: add requests with an optional section, send, resolve, withdraw.
- Nothing in existing responses changes except one added field.

## Open questions for the product owner

1. Maximum length of a request (1000 characters proposed).
2. Should a withdrawn request notify the owner? (Proposed: no.)
3. Should the super-admin see how long a salon has been waiting? (Cheap to add; not in this spec.)
