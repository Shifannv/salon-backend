# Proposed production SQL execution — 0053 through 0055

Prepared for separate owner approval; not executed.
Subsequent status: explicitly approved and executed successfully; see
[execution result](PRODUCTION_0053_0055_EXECUTION_RESULT_2026-11-01.md).
Target: Supabase project wqjlgpnbiapcrlkxumcp, the shared production database.
Gate A evidence: [completed isolated rehearsal](GATE_A_0053_0055_2026-11-01.md).

1. Recheck source and the three exact committed SQL hashes from Gate A. Stop if
   any source differs. Check current Alembic history is the observed 0052 entry,
   all prerequisite objects exist, and none of the eight proposed tables exists.
   Already-existing or partially applied objects require investigation, not replay.
2. Take a fresh encrypted complete exportable database backup outside the checkout;
   verify decryption, timestamp, hash and isolated recovery. Obtain permission to
   retain that encrypted backup for the release recovery window. Do not treat the
   deleted Gate A backup as an available recovery point.
3. Apply only 0053_salon_payout_requests.sql, then 0054_staff_earnings.sql, then
   0055_feature_access.sql, individually with psql --single-transaction and
   -v ON_ERROR_STOP=1. Preserve their lock and statement timeouts. 0054's unique
   index creation can block writes on staff/services; schedule the approved
   short release window and stop on contention instead of extending timeouts.
4. After each transaction, verify object definitions, guards, RLS, effective
   client denial and the migration's expected seeds. Do not replay successful
   transactions after a later failure. Review a forward repair if necessary.
5. Preserve current application traffic throughout schema execution. No API,
   booking, payment, customer or account-deletion mutation smoke requests.
6. This SQL-only scope leaves Alembic history unchanged, exactly as rehearsed.
   Do not stamp or manually update alembic_version, run upgrade head, or claim
   the recorded history advanced. Any history adoption requires a separate review.
7. Produce a hash-bound schema compatibility receipt. API rollout is a separate
   step: exact latest-main CI image, immutable digest, zero-traffic candidate,
   readiness/version/contract verification, then the established promotion
   approval. Keep migration-difference refusal intact until that scoped release
   is reviewed; do not bypass it by disabling checks.

Failure handling: a failed transaction rolls itself back. Previously committed
additive migrations remain; retain the old healthy API and stop. Never drop
populated finance tables or run destructive downgrades. Restoring production
requires a separate incident decision and write-freeze to prevent losing writes.
Retain the existing Cloud Run rollback revision; do not alter DNS, runtime
secrets, IAM/WIF, deployment flags or workers as part of this SQL approval.
