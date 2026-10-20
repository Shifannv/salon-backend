# Server-side WebP image families

Implemented locally; not deployed or verified against real R2/CDN. No schema or
migration change. Frontends have not been changed. The API remains authoritative;
client-side compression is an optional bandwidth optimization.

## Policy

`webp-v2` is defined in `app/application/ports/image_processor.py`. All variants
come from one decoded, orientation-corrected, metadata-free pixel buffer. EXIF/GPS,
ICC/XMP and comments are discarded. Alpha is preserved. No upscaling and no stored
raw original. JPEG, PNG and WebP inputs only; animation, SVG (including disguised
SVG), malformed/truncated files, MIME mismatches and decompression bombs fail.

| Category | Variant | Maximum edge | Maximum bytes |
| --- | --- | ---: | ---: |
| Avatar | avatar | 512 | 512000 |
| Staff | card | 512 | 512000 |
| Staff | detail | 1024 | 1048576 |
| Gallery/service | thumbnail | 400 | 1048576 |
| Gallery/service | card | 800 | 1048576 |
| Gallery/service | detail | 1600 | 1048576 |

Dimensions may shrink further to satisfy the byte cap; encoding has five bounded
attempts. New family policies are versioned constants, not the legacy `IMAGE_*`
output settings. `IMAGE_MAX_PIXELS` still limits decoding. Source limits remain
5242880 bytes, at most 40000000 pixels and 16384 px per edge.

## Keys, proof and compatibility

Canonical variant keys are deterministic for the namespace and encoded outputs:

```text
avatars/{profile_id}/webp-v2/{family_hash}/avatar-{output_sha256}.webp
staff-photos/{salon_id}/{staff_id}/webp-v2/{family_hash}/{variant}-{output_sha256}.webp
salon-images/{salon_id}/webp-v2/{family_hash}/{variant}-{output_sha256}.webp
```

The family hash covers the namespace, version and ordered sanitized-output
manifest. Equal content in different accounts cannot collide. Keys are immutable;
conditional `IfNoneMatch=*` writes never replace existing bytes. Encoder changes
that change the bytes create new keys. Deliberate policy changes need a new version.

Existing clients receive `public_url` before supplying any bytes. Therefore signed
uploads also create a compatibility image at that issued random key, **after all
canonical variants succeed**. It contains the largest processed WebP, even if its
legacy suffix is `.jpg`/`.png`; its HTTP Content-Type is `image/webp`. It is never
the raw input. Separate grants can create separate compatibility copies, while
their canonical variant objects deduplicate. Customer multipart upload returns the
canonical avatar URL directly, without a compatibility copy.

Every new object has HMAC-signed `processed-image-v2` metadata: bucket, exact key,
namespace, family ID, policy version, variant, width, height, MIME, byte length,
SHA-256, ordered member manifest and alias flag. Signing uses the existing secret
configuration. Content-MD5 protects PUT body transport. Each PUT acknowledgement
and subsequent HEAD are checked; signed metadata and actual HEAD MIME/length must
match. Ambiguous responses/conditional conflicts require an exact matching HEAD.
Objects receive `Cache-Control: public, max-age=31536000, immutable`.

Existing keys and unchanged legacy database URLs are preserved. v1 processing
proofs remain readable/valid under their legacy policy; unmarked legacy objects
are not enrolled into automatic cleanup. Secret rotation invalidates older proofs
until a separately reviewed re-attestation strategy exists.

## Additive API contract

Grant POST paths and their existing fields stay unchanged. A new `result_url`
is a separate **read-only** URL on `/v1/media/results/{token}`. It is signed in
its own domain, so it cannot be used to upload, and the upload token cannot read
results. It expires with the grant. Clients can keep the original flow:

1. Request a grant with `filename` and `content_type`.
2. PUT the binary to `upload_url`, with that Content-Type. Success is still 204.
3. Save `public_url` through the existing profile/gallery/staff/service mutation.

New clients may GET `result_url` after PUT and before grant expiry (300 seconds).
Before the PUT completes the family does not exist, so the GET returns 422:

```json
{
  "public_url": "https://media.example/salon-images/example/issued-key.jpg",
  "family_id": "<sha256>",
  "policy_version": "webp-v2",
  "variants": {
    "card": {
      "variant": "card", "url": "https://media.example/<canonical-key>.webp",
      "width": 800, "height": 450, "mime": "image/webp",
      "size": 12345, "sha256": "<sha256>"
    }
  }
}
```

The example abbreviates the variants map; gallery responses contain all three.
GET verifies the capability and entire family, and returns no-store. Successful
PUT also returns no-store and `X-Image-Family-ID`, and on a best-effort basis a
`Link` to the read-only result URL (never to the upload URL). The header can be
absent when it cannot be derived, and a missing `Link` never means the upload failed.
The `result_url` field in the grant response body is authoritative; the PUT itself
returns 204 with no body.
`POST /v1/customer/profile/avatar` retains `avatar_url` and adds `family_id`,
`policy_version` and the variants map. Existing database read responses keep their
single URL fields; the variant manifest lives in signed R2 metadata.

All variants must be processed and verified before saving a database reference.
Publication locks family members and rechecks every HEAD under transaction locks.
Failed uploads/saves never delete an old reference or blindly delete shared new
objects. Repeating the same source and grant completes a partial upload safely;
different content cannot overwrite an issued compatibility URL. Expired grants
need replacement grants. There is no background reconstruction of missing variants
because the original source is deliberately not retained.

## Family retirement and account erasure

The existing `0020_media_reference_guards` must already be installed. The cleanup
worker refuses to scan without all seven guards. No new migration is introduced.

Every canonical family URL takes a shared family advisory lock before its URL
lock. Publication and cleanup use the same locks. Cleanup then inventories aliases
inside the exact account/salon/staff namespace and checks every alias/member URL
against the existing seven-table reference query. Any reference protects the whole
family, including references to a smaller variant. No URL is removed from the DB.
All present objects, including newly issued aliases, must exceed the cleanup grace.
Unreferenced partial families are swept after the grace; client retries can finish
them before then. Missing objects are idempotent, but storage/metadata/listing and
database failures fail closed and retry on later sweeps.

The no-migration alias inventory is deliberately conservative: 10000 objects per
namespace maximum, after which retirement fails closed and needs operator review.
It performs namespace LIST/HEAD operations and can be expensive for large salons.
All backend writers must run the family-aware release together; old writers do not
acquire family locks. Direct privileged DB/storage administrators remain trusted.

Account erasure applies the same family/reference protections, without age grace.
Its recorded anchor is deleted last so a partial deletion retains the manifest for
retry. Confirmed 404 is idempotent; transient HEAD errors are not treated as missing.
The existing user-confirmed erasure exception still permits legacy object deletion.
Shared families referenced by another record remain preserved.

Cleanup logs numeric candidate/retirement/failure counts and duration, plus safe
error classes. Its atomic heartbeat JSON records last completion/success and those
counts. `python -m app.infrastructure.media.health` fails for missing, stale or
failed sweeps. No Compose healthcheck is wired to it: `media-cleanup` keeps its
healthcheck disabled until the deploy-script interaction (`up --wait`) is verified in
a disposable Compose project. Cloud Run still requires a separately scheduled sweep;
running the API alone does not run cleanup.

## Admission and resource limits

ASGI admission runs before multipart parsing: binary bodies at most 5 MiB,
multipart envelopes at most 5 MiB + 64 KiB; grant JSON bodies at most 8 KiB. Metadata
GETs also share upload admission/rate limits and accept no body. Invalid
Content-Length, mismatched framing, unsupported upload MIME and malformed multipart
boundaries are rejected. A total 10-second body-read deadline, four in-flight
upload/grant requests and 30 attempts per client IP per minute per upload/grant
class limit ingress. The rate map is bounded to 1024 entries. Multipart parsing
accepts exactly one image file, no other fields; its temporary spooling is bounded
by the admitted request size and concurrency.

The shared decoder pool has two threads and at most four running/queued jobs.
Requests time out after 15 seconds, but a timed-out native decoder retains its
capacity slot until it really exits. Thread cancellation cannot terminate native
code. Hard decoder termination would require process isolation.

Admission/rate limits are per process. Deployments need trusted ingress limits
for aggregate multi-process traffic; behind a proxy the socket IP may represent
many clients. Forwarded headers are intentionally not trusted automatically.
Rejected admissions use 413/415/408/429/503 as appropriate; codec validation uses
422 and decoder saturation/timeout uses 503.

## Verification boundary

Tests use synthetic images and stateful mocked R2, including upload/HEAD failures,
immutable retries, partial cleanup and erasure. Mocked repository tests do not prove
real PostgreSQL transaction/concurrency behavior. Real R2 response compatibility,
CDN behavior, native-device WebP display, shared ingress policy and deployment
health remain separately approved staging checks. No live bucket, production,
Sydney Supabase, frontend code, DNS or production URLs are changed by this work.

Origin deletion does not purge an existing CDN/browser cache. The immutable cache
policy and any erasure-related CDN purge requirements need staging/operations
review before release. If an erasure anchor was externally deleted beforehand,
remaining unreferenced siblings are left to the ordinary family cleanup sweep.

## Local verification, 2026-10-19

- Focused media, processor, admission, cleanup, erasure, ownership, service/profile
  and HTTP contract selection: **298 passed**, one upstream TestClient warning.
- Full `ruff check --no-cache app tests migrations`: passed.
- Broader unit run: **1085 passed, 3 failed**. The failures are in untouched
  `test_fake_provider.py` (two JSON fixture CRLF comparisons) and
  `test_migration_tool_paths.py` (sealed `privilege-matrix.csv` newline/hash).
  Those files/fixtures were not changed for this task.
- Compose configuration with an empty temporary environment: passed. Both GCP VM
  script syntax checks passed. Docker daemon access was denied, so image build
  verification could not run.
- Real database concurrency, R2/CDN and device checks were not run. All image
  inputs were synthetic; R2 used a stateful in-memory boto fake. Concurrent
  replacement tests explicitly model transaction locks, rather than claiming real
  PostgreSQL locking evidence.

Implementation files are the image processor/storage ports; avatar, publication,
cleanup and erasure use cases; `infrastructure/media/{pillow_processor,admission,
cleanup_worker,health}.py`; `infrastructure/r2/{storage,families}.py`; the repository
family lock; media routes/schemas; grant response construction; and `main.py`.
Compose is unchanged. Tests include the new `test_image_variants_processor`,
`test_image_families`, `test_media_admission`, `test_media_cleanup_health`,
`test_media_additional_guards` modules and stateful `media_r2_fake`, with the existing
upload/publication/erasure tests updated for the additive contract.

Next approval: review the backend changes, then authorize isolated staging
PostgreSQL/R2/CDN and real-client compatibility checks. No deployment, migration,
frontend change, commit or push is authorized or performed here.
