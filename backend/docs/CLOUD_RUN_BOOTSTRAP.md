# Legacy Cloud Run baseline bootstrap

This verifies the existing hybrid image without claiming it equals a Git commit.
It does not approve deployment, migrations, runtime changes or traffic promotion.

## Verified baseline

Target: saloon-505509 / asia-south1 / salon-api-production.
Serving revision: salon-api-production-subpct-20261028.

- Registry index: `sha256:ee92c2f588acbab37e905162cc8346d5eeea387046521db4c2c52eb717858f69`.
- Linux/amd64 image: `sha256:76ce6bec396732f0ac82957248547eead50f662bbc35fce3a42cbdfdb728a9d7`.
- Base image: `sha256:dfb24746323e9d4cfa2a4fd9cff7d0fee1d7a02ee5d0893a8a436f9f3cfbcef1`.
- Overlay reference: d93ba0a13f60f0574d8cc2878e3bebd149d70905. This is a partial
  source reference, never a full-image Git source claim.

The registry index contains the serving platform digest. All 406 inspected file
hashes under app/, migrations/, requirements.txt and alembic.ini match the
committed attestation, including compiled files. Base-versus-serving comparison
found exactly the nine application changes recorded in the original manifest;
all nine final overlay hashes match actual image bytes. Inspection used stopped
containers and never ran the application or read environment files/mounted secrets.

`backend/deployments/bootstrap-subpct-20261028.json` contains identifiers/hashes
and limited read-only schema observations. The immutable digest binds the entire
image; the inventory describes selected paths, not all OS/package files.
Original evidence: salon-owner-APP/.tmp/subscription-release-20261028/. No frontend
source or credentials were copied into this repository.

## Workflow selection after review

All existing actor, main/SHA, event, deployment confirmation, environment, CI,
concurrency, zero-traffic and configuration guards remain. Normal labeled-image
releases still use baseline_commit.

For this exact old image only, select bootstrap_baseline=true, leave baseline_commit
empty and type bootstrap_confirmation exactly:
`BOOTSTRAP salon-api-production-subpct-20261028`.

The verifier requires the exact target/revision/platform digest, registry-index
membership and all 406 hashes. Different revisions/images, missing/extra files
or changed hashes stop release. Only verifier-owned stopped inspection containers
are removed; images, revisions and rollback resources remain.

After a labeled release serves production, this bootstrap becomes ineligible.
A rollback to the exact old baseline again requires explicit bootstrap selection;
no persistent consumed marker is invented.

## Migration gate

Compare packaged migration source to selected Git. LF/CRLF differences alone
are tolerated; SQL/Python changes are not. Historical review material is not in
images, so its changes are checked separately against the recorded overlay Git
reference. No migration allow-list or automatic SQL execution is introduced.

Current main differs in SQL/version files 0041–0051. This does not mean all are
unapplied: 0049 was separately applied and 0050's offer-expiry column exists.
The preflight reports outstanding paths and stops before publication/deployment.
See [schema review](CLOUD_RUN_SCHEMA_RECONCILIATION.md); latest main is not
deployment-ready merely because its baseline provenance can now be verified.

## Other fixes

Resolve an index to exactly one linux/amd64 image, verify its source labels,
deploy that immutable platform digest and record both identifiers. Cloud Run's
platform digest must not be compared directly to its parent index digest.

Fake-provider signed JSON fixtures are pinned to LF in .gitattributes. Fresh
Windows checkout reproduced two exact-byte test failures from CRLF. Committed
fixture contents/assertions are unchanged; only the checkout rule is fixed.
