# Salon owner approval

Owners finish onboarding through `POST /v1/salons/me/complete-profile`. A new salon
stays `pending`; this returns 200 with the salon, so onboarding is saved successfully.
`GET /v1/salons/me` exposes `approval_status`, `approved_at`, `approved_by`, and
`rejection_reason`. The owner app should show the waiting/rejection screen until the
salon is active, profile-completed, and approved.

Setup editing (profile, images, services, staff, and settings) remains available for
onboarding and corrections. Bookings, payments, booking decisions/action requests,
closures, holidays, blocked time, and the business QR require approval. Unapproved
workspace requests return HTTP 403 with `error.code = awaiting_admin_approval`.
The backend gate applies even when a client skips the waiting screen.

The super admin page uses a verified Supabase JWT for a database profile whose role
is `super_admin`. The API provides:

- `GET /v1/admin/salons?approval_status=pending`: paginated review list with owner
  name/email, onboarding completion, and approval fields. Use `profile_completed`
  to distinguish submissions ready for review from unfinished registrations.
- `GET /v1/admin/salons/{salon_id}`: salon and owner details.
- `POST /v1/admin/salons/{salon_id}/approve`: approve an active, completed salon;
  repeated approval preserves the original approving actor/time.
- `POST /v1/admin/salons/{salon_id}/reject` with
  `{"rejection_reason":"Please correct the address"}`: reject without banning.
- Existing update/deactivate endpoints remain available; deactivation disables the
  salon and owner's account separately from rejection. `POST
  /v1/admin/salons/{salon_id}/reactivate` restores salon and owner access without
  changing approval, discovery, onboarding, or subscription state.

A rejected owner corrects setup and calls complete-profile again. This resets only
the rejected salon to pending and clears the reason. Calling complete-profile on an
already approved salon preserves its approval. Review and resubmission serialize on
the salon row. Pending entries in the admin list are the review signal; a new admin
push notification is not part of this change.

Migration `0015_salon_admin_approval` adds the enum, columns, index, RLS rules, and
database guards. Public discovery, QR lookup, availability, and booking creation
require approval, including calls to the database functions. Owners cannot modify
approval metadata to approve themselves. Existing active, completed salons are
backfilled as approved to preserve the attached plan's compatibility behavior;
`approved_by` remains null because no human reviewed this backfill.

## Verification and deployment

Run from `backend/`:

```powershell
./.venv/Scripts/python.exe -m scripts.check_salon_approval_schema
./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
./.venv/Scripts/python.exe -m ruff check app tests migrations --no-cache
$env:SALON_APPROVAL_DB_TESTS='1'
./.venv/Scripts/python.exe -m pytest tests/integration/test_salon_approval_migration.py -q
Remove-Item Env:SALON_APPROVAL_DB_TESTS
```

The opt-in database test creates a randomly named isolated schema in one transaction,
exercises upgrade, role-based reads, self-approval rejection, resubmission, booking,
downgrade, and re-upgrade, then rolls back everything. It does not change shared tables,
auth registration triggers, publications, or Alembic tracking. Its v3 fixture skips
`0005` because the current baseline already includes `staff.experience`; it does not
prove that the entire historical fresh-install chain is clean.

On 2026-10-08, read-only inspection of the configured database found `salons` and
revision `0014_repair_cancel_reason`, but no approval columns. The exact repair
migration was restored from commit `644b730` in `origin/main` history. Approval now
follows it as `0015_salon_admin_approval`, so the local graph recognizes the live
revision without changing its tracking or inventing a replacement.

After reviewing the approval migration, apply `alembic upgrade head` as an explicit
deploy step, then deploy the backend. Migrations never run on API startup.
The owner waiting screen and super admin page belong in their separate frontend repos.

## Owner push on decision

When an admin approves or rejects a salon, the owner receives a push (and an in-app
notification, `type = approval_status`, no booking). Delivery is best-effort: a push failure
never undoes the decision, and an owner with no active device token is skipped silently.
Repeating the same decision (same status, same rejection reason) does not push again.

- Approved: title "Your salon is verified 🎉"; data `{type: approval_status, status: approved}`.
- Rejected: title "Action needed on your salon"; data
  `{type: approval_status, status: rejected, reason: <reason, max 500 chars>}`.

The structured data is stored in `notifications.data` (migration `0023_notification_data`;
run `alembic upgrade head` before deploying this backend version).
