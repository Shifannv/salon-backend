# Schema review required before latest-main release

Preparation only: no production SQL execution is approved by the bootstrap fix.
Target: existing Mumbai project wqjlgpnbiapcrlkxumcp, shared by staging/production.

## Read-only evidence, 29 October 2026

- salon_plan_prices exists and has valid_until (0049/0050 effects).
- booking_customer_changes, booking_financial_outcomes, booking_finance_commands,
  booking_policy_refund_jobs and support_erasure_events are absent.
- salon_expenses, salon_cash_adjustments and salon_day_closes are absent.
- salons.category, salons.description and services.description still exist.

The serving image packages migration sources through 0040; current main includes
0041–0051. Some were applied separately, so do not blindly replay them. Column
presence, packaged files and CI are not complete schema-compatibility proof.
Do not stamp or upgrade Alembic history to infer adoption.

## Separate procedure needed

1. Freeze latest main and exact proposed migration hashes.
2. Obtain/verify a fresh complete shared-database recovery point; record UTC/IST
   time and rehearse decryption/restore outside the repo. Hosted backup/PITR is
   not assumed. Current no-secret-payload rules remain; separately approve any
   credential handling needed for backup or execution.
3. On a disposable restored copy, compare live columns, functions, triggers,
   ownership/grants and tables with exact 0041–0051 effects. Classify already
   applied, partial, absent and intentionally deferred items.
4. Review code paths needing each missing effect. Do not activate unrelated U08,
   payments, deletion or audit-retention behavior merely to reach a migration head.
5. Explicitly review 0041/0042 data retention: they drop description/category
   columns that currently exist. These are not purely additive changes.
6. Produce/rehearse the exact ordered SQL plan and hashes, verify counts,
   financial invariants and client-role denial, then obtain target-specific
   execution approval. Existing 0049/0050 must not be rerun blindly.
7. Apply only approved SQL with explicit transaction/error/lock/statement guards
   where valid. No head upgrade, stamp, startup migration or blanket batch.
8. Verify schema and approve a digest/hash-bound compatibility attestation for
   release. Bootstrap currently has no migration-delta bypass.
9. Review/merge release changes, validate a zero-traffic candidate from latest
   main, and handle traffic only under the user's release approval.

## Finance 0051 review input

At reviewed base 5903d47ff8c46348b02464d853cfc78d13c8ddf0:
`backend/migrations/sql/0051_owner_finance_cashbook.sql` has 25 marked statements.
SHA-256 of committed LF bytes:
`c1103a7cf55238a99d394a90b1b9de637b002ffaaff9d69ed4bd52e45677c860`.

It creates three append-only finance tables, indexes, RLS/grants and triggers.
It is forward-only because future finance records cannot be discarded by
downgrade. This hash/count is review evidence, not execution approval. Applying
only 0051 cannot establish compatibility with all remaining source differences.

## Local rehearsal follow-up

See [29 October restored-copy rehearsal](SCHEMA_REHEARSAL_20261029.md) for the later
848ac73 source, proposed 43-statement finance correction, recovery verification and
measured retention effects. The historical 5903d47 hash above is not the current
0051 execution input. No production SQL or release was performed.
