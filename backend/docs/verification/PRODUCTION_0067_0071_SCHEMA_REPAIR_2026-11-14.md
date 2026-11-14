# Production schema repair evidence: 0067-0071

The owner explicitly authorized a production schema repair and the subsequent
Cloud Run release in this session.

## Scope

Production project `wqjlgpnbiapcrlkxumcp` was inspected before the repair. Its
catalog showed the objects introduced by migrations 0068-0070, while the
`public.staff_break_overlaps(uuid, timestamptz, timestamptz)` helper was absent
and `public.visit_break_conflict` had an older definition that did not invoke
that helper. The repair is limited to migration 0071's forward-only
`CREATE OR REPLACE FUNCTION` statements. It creates no tables, changes no data,
and does not alter migration history.

## Executed repair and verification

- The exact 0071 SQL from the immutable CI image for merged commit
  `f7bedcfc8572fbeb0ce4885633b1e0267b62216c` was executed by Cloud Run Job
  `salon-schema-repair-0071`, execution `salon-schema-repair-0071-zls2f`.
- The job used the existing production runtime service account and mounted
  runtime environment configuration. No credential values were printed or
  recorded in this repository.
- A first verification execution was rejected because the inline command lost
  quotation marks before Python ran; it made no database change.
- The job command was then replaced with a base64-encoded verification program.
  Execution `salon-schema-repair-0071-6fbn4` completed successfully. That
  program exits non-zero unless both functions exist and the current
  `visit_break_conflict` source invokes `staff_break_overlaps`; successful
  completion therefore establishes the required catalog state.

## Release boundary

This evidence authorizes only the hash-bound migration set 0067-0071 against
the established healthy baseline commit
`52197d54be9313ef6e1bdb5fdc6ca0792a5dd5a8`, revision
`salon-api-production-credential-v4-20261113`, and immutable image
`asia-south1-docker.pkg.dev/saloon-505509/salon-production/api@sha256:8ee466a3808d8077d332a8188d13f3e080ae69970334793938199b26d17d6418`.

This baseline superseded the earlier `age-guardian-0065` revision when the
production credential bundle was rotated. Read-only inspection on November 14
confirmed the same exact API source commit on the public `/version` endpoint.

It is not a general migration bypass. The normal GitHub Actions workflow must
still build and test the exact receipt commit, validate image provenance and
schema hashes, create a candidate, pass public health and contract checks, and
then promote traffic. No direct traffic change was made while recording this
evidence.
