# Current subscription catalog approval — 1 November 2026

The owner explicitly confirmed these existing production catalog prices after
reviewing the Gate A diagnostic snapshot. This supersedes the previous price
expectations recorded on 31 October 2026.

| Plan code | Approved INR |
| --- | ---: |
| growth_1m | 449 |
| growth_6m | 2419 |
| growth_12m | 4299 |
| premium_6m | 3499 |
| premium_12m | 6199 |

Approval context: after the exact five prices were presented, the owner replied,
“yes i confirm it the prices”. No other plan, including premium_1m, is changed
or newly attested by this record.

The reconciliation harness now checks these exact approved values. Incorrect
prices and missing plans still fail. No production price UPDATE, migration
replay, Alembic stamp, deployment or traffic change is authorized or performed
by this price confirmation. The historical 0049 SQL and earlier evidence remain
unchanged. Gate A must still complete against a fresh encrypted backup and an
isolated restore before production migration approval.
