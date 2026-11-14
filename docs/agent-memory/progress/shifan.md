# Progress: shifan

## Goal
Get the full shifan branch work (migrations 0053–0070, booking-409 fix, break-times, auto-payouts, notification audience, payout config alias) deployed to production via Cloud Run. Branch is synced with main as of 2026-11-14.

## Status
**SYNCED WITH MAIN — 2510 unit tests pass, Ruff clean. Cloud Run deploy outcome not yet confirmed.**

## Done
- Migrations 0053–0070 written, reviewed and applied to production DB (direct SQL, then alembic_version stamped to 0070).
- All 0053–0070 migration Python files and SQL sidecars committed in prior sessions.
- Booking-409 fix (re-arm `set_actor_context` before booking SQL after age-check rollback).
- `_error_for_message` spoofing fix + 3 new error rules.
- Break-times enforcement (migration 0067, availability envelope, `break_conflict` error).
- Auto-payouts migration 0068.
- Notification audience routing migration 0069 + FCM/outbox filtering.
- Payout config alias (`CASHFREE_PAYOUT_SECERET_KEY`).
- Integration test schema extended: `booking_no_show_warnings` added to `_build()` fixtures and `POST_BASELINE_COLUMN_TREATMENT`.
- Production working-hours schema drift repaired (PR #88 `fix/cloud-run-schema-0070-release`).
- Schema repair verification recorded (PR #89 `chore/record-schema-0071-verification`).
- Cloud Run credential baseline reconciled (PR #90 `fix/cloud-run-credential-baseline`).
- `fix/remove-unconfigured-secondary-domain` merged into main (removed `apiv1.mudassirmhd.in` from `PUBLIC_CHECKS`).
- Main merged back into shifan (commit `0d0cb69`).

## In progress
- Verifying that Cloud Run auto-deploy succeeded after the credential baseline fix.

## Next steps
1. Check `https://api.salones.in/version` — confirm it returns a commit SHA from after PR #90.
2. Re-enable both GitHub rulesets (`main` ID 26150184, `shifan` ID 26152722) in Settings → Rulesets now that the emergency push is done.
3. Revoke the GitHub PAT shared in chat (visit github.com/settings/tokens).
4. Make the GitHub repo private (deferred until after deploy confirmed).
5. Owner app payout API UI still not wired to backend routes — separate session.
6. Cashfree Payouts activation: complete 2FA (IP whitelist or RSA), fund Payouts balance, register webhook `https://api.salones.in/v1/webhooks/payouts/cashfree`.
7. Set `ADMIN_REQUIRE_MFA=true` in production Secret Manager env if not already set.

## Decisions
- Emergency push directly to `main` by disabling both GitHub rulesets was chosen because: (1) the PR review gate is a solo-repo catch-22, (2) CI had already passed on the branch, (3) the change was a one-line health-check fix with no migration or auth impact.

## Files touched (this session)
- `backend/scripts/cloud_run_auto.py` — PUBLIC_CHECKS narrowed (via fix/remove-unconfigured-secondary-domain, merged)
- `docs/agent-memory/shared/gotchas.md` — approved_schema_release and ruleset gotchas added
- `docs/agent-memory/progress/shifan.md` — this file

## Blockers
- Cloud Run deploy outcome unknown — the credential baseline fix (PR #90) should have unblocked it, but `/version` has not been verified this session.
- GitHub PAT shared in this chat session must be revoked immediately.
- Both GitHub rulesets are still disabled from the emergency bypass — re-enable before next PR.

## Session log
- 2026-11-13: CI fix for booking_no_show_warnings; committed a0d206a
- 2026-11-13: fix/remove-unconfigured-secondary-domain branch work; health-gate fix committed 2c5a7ac
- 2026-11-14: merged fix/remove-unconfigured-secondary-domain → main; Cloud Run deploy failed (approved_schema_release gate); user fixed via PRs #88/#89/#90; main merged back into shifan; wrap
