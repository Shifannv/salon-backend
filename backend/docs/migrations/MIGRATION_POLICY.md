# Explicit migration policy

The portable CI revision is **0037_customer_processing_charge**. The actual Alembic
repository head remains **0040_fastapi_only_access**, prepared for Mumbai only.
These are different concepts. No revision, dependency, label or sealed evidence has
been changed to make CI pass. Revisions 0038-0040 remain unapplied by this work.

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
target before creating a disposable database. No prepared SQL executes on scratch.

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
