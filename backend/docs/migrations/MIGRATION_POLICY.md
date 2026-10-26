# Explicit migration policy

The portable CI revision is **0037_customer_processing_charge**. The actual Alembic
repository head is **0048_support_billing_erasure**, prepared and not released.
The guarded Mumbai approval/manifest target remains **0040_fastapi_only_access**;
it does not authorize the later photo/description, business-category, attendance,
checkout-policy, booking-change or finance-outcome revisions.
These are different concepts. No revision, dependency, label or sealed evidence has
been changed to make CI pass. Revisions 0038-0048 remain unapplied by this work.

0047 adds narrowly guarded redaction for new immutable booking/finance audits.
0048 adds versioned, restricted support-case retention and exact subscription
benefit redaction without altering charges, purchase/period/expiry dates or provider
references. Both remain separate prepared forward revisions; neither changes the
portable or approved Mumbai execution boundaries below. The repository head must
never be interpreted as an approved production migration target.

0045 adds versioned atomic customer service/time changes and an owned-booking SQL
availability overload. 0046 adds terminal U08 obligations, provider-pending refund jobs,
manual finance controls and ledger-drift reconciliation queues. Both have explicit
forward-only downgrade refusal, local SQL/HTTP regression coverage and read-only review.
They do not activate U08, dispatch refunds, verify provider-held funds or authorize any
remote migration. The existing portable and Mumbai execution gates remain unchanged.

Fresh read-only Mumbai metadata on 23 October still shows zero Alembic history rows.
Do not use `upgrade head` or stamp a restored database to bypass reconciliation.
0041/0042 require compatible API/client readers before their destructive field cleanup;
0043 additionally needs coordinated rollout of its required no-show reason body.
The scoped 0043 SQL passed local disposable PostgreSQL guard/journey tests, including
repeat execution, exact ten-minute timing and erasure compatibility. Those tests apply
the reviewed sidecar explicitly to a portable fixture; they do not prove whole-chain
replay or extend the Alembic execution policy to any remote target.

0044 replaces only the existing immutable checkout-policy stamp, with no data rewrite
or new grants. The server setting `BOOKING_CHECKOUT_POLICY_VERSION` defaults to
`customer_processing_v1`; explicit selection of `u08-2026-10-23-v1` is for future
bookings only and requires the reviewed migration first. Application creation verifies
the stored version and rolls back with503 if the migration is missing. Keep the old
setting until coordinated approval; preparing this selector does not activate U08.
Once U08 bookings exist, rollback must retain the stored-policy online-payment guard
or keep collection disabled. An older API must not route those bookings through the
legacy automatic-split/commission flow merely because credentials are configured.

`app/core/migration_policy.py` defines the two targets. Alembic `env.py` validates
the exact process-supplied URL, raw destination, operation, starting revision and
current history. It rejects implicit `head`, query routing overrides, unknown policies,
unapproved prepared targets, stamp and `ensure_version` before mutation. Cached app
settings or an ordinary `.env` cannot authorize a different migration connection.

## Portable CI

Only disposable loopback PostgreSQL is allowed by `migration_policy=portable-ci`.
The guard checks loopback addressing and revision ancestry; loopback alone does not
prove disposal or rule out a tunnel. The operator must supply a verified disposable
server. The local runs in this change used identity-checked dedicated Docker containers.
Targets must be explicit members of 0001-0037's ancestry. Prepared starting revisions
are also refused, including downgrades and offline ranges. The test helper checks the
target before creating a disposable database. The generic portable Alembic path never
executes prepared SQL; explicitly scoped local sidecar tests are separate evidence.

The generic workflow names `PORTABLE_CI_TARGET=0037_customer_processing_charge`, uses
the declared asyncpg driver, isolates normal environment files and emits JUnit results.
`tests/conftest.py` isolates local `.env` files before importing application code.
No collection/setup error is accepted, xfailed or ignored. The helper's portable target
is a named policy constant, not a reinterpretation of Alembic `head`.

After explicit authorization for a disposable server, a portable invocation is:

```bash
alembic -x migration_policy=portable-ci upgrade 0037_customer_processing_charge
```

The process must supply `DATABASE_URL` explicitly. Tests construct their own unique
database, install minimal Auth prerequisites, exercise the historical chain and clean
up. Account-erasure suites needing a separately provisioned database remain opt-in;
their skips are reported rather than counted as passes.

## Mumbai validation and approval

`.github/workflows/mumbai-migration-validation.yml` has only `workflow_dispatch`.
It has no scratch PostgreSQL service and never runs automatically on PRs. It uses
the dedicated `mumbai-migration-validation` environment and its scoped database secret.
Configure required human reviewers and branch protection for that environment before
using it. This repository change does not configure GitHub environment protection rules.

Inputs must name the exact Mumbai project, approval reference, explicit approval
manifest and reviewed CA certificate. The validator first verifies target and evidence,
then uses a READ ONLY transaction. It executes no revision SQL and no stamp. Empty
Alembic history or missing managed prerequisites fails validation and keeps execution held.
Client TLS verification and `pg_stat_ssl` on the pooler/database hop are separate evidence.

An authorization manifest must contain:

- `project_ref`, `target_revision` (0040), `approval_id`, `approved_by`, `status=approved`;
- `source_sha256`: hashes keyed by all six 0038-0040 Python/SQL filenames;
- `review` and `preflight`: each with `path` relative to the manifest, `sha256`, and
  `status=passed`. Existing sealed evidence is read and hashed, never rewritten.

No approved manifest is manufactured by this change. Approval metadata is an explicit
review artifact, not a substitute for the protected-environment human approval.
An application or CI default cannot select it. Re-review when sources or evidence change.
The script invocation, supplied only after separate approval, is:

```bash
python -m scripts.validate_mumbai_migrations --confirm-project <Mumbai-project-ref> \
  --approval-id <review-reference> --approval-manifest <approved-manifest> \
  --ca-file <reviewed-ca-file>
```

Execution is a different action. It requires `-x migration_policy=mumbai`, exact project
confirmation, explicit prepared revision, approval ID and matching manifest. Only known
Mumbai direct/regional-pooler authorities with the project-scoped account are accepted.
Generic servers, Sydney, query-routing substitutions and prepared downgrades are refused.
Mumbai offline SQL rendering also requires an explicit reviewed starting revision;
it cannot emit the baseline just because 0040 was named as the destination.
An empty/restored history cannot be repaired by this guard and is not authorization to
replay 0001 onward. Resolve history separately; no stamp is permitted here.

## Deployment

Push/PR events test and build. Production deployment now requires an explicit manual
request, protected environment approval, reviewed target and approval reference.
There is no automatic `upgrade head` on a push. The release script requires explicit
`SALON_MIGRATION_POLICY`, `SALON_MIGRATION_REVISION` and `SALON_MIGRATION_APPROVAL_ID`
before loading an image. Mumbai additionally needs project confirmation and a manifest;
its directory is mounted read-only. URL/current-history checks happen inside Alembic.

The production workflow offers no portable-CI migration option: portable is exclusively
for disposable loopback databases. Current non-Mumbai production/Sydney deployments are
not authorized by this change and remain held pending a separately reviewed policy.
No production resource or workflow has been triggered, and no remote setting changed.
Do not weaken the target guard to make that deployment job run.

The backend image retains the true prepared Alembic head. Its smoke test verifies that
an implicit head request fails before connecting. The container startup does not migrate.
Deployment failure preserves existing services and the prior healthy release pointer.

Rollback this code only with an equally restrictive migration entry point; restoring
automatic `upgrade head` reintroduces the original risk. No schema rollback, evidence
rewrite, grant or stamp is part of policy rollback.
