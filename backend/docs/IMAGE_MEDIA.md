# Validated images and safe retirement

New uploads now use [versioned WebP families](IMAGE_VARIANTS.md). That document is
the current variant, metadata, API, admission and cleanup contract. The single-image
encoding policy below describes the retained v1/legacy processing behavior.

Client processing reduces network use; the backend remains the publication boundary.
Customer multipart avatars and signed owner/profile/gallery/staff uploads use Pillow
before R2. Owner services reuse gallery uploads. QR images are server-generated HTTP
responses and do not create R2 objects. Customer style archives are device-local.

The upload-url response fields and public URL paths are unchanged. Signed URLs point
to `/v1/media/uploads/{token}` on `PUBLIC_API_BASE_URL`, never a direct R2 PUT. Grants
expire in 300 seconds. An identical retry can succeed after a lost response; conditional
creation prevents different content from replacing the first object.

## Processing and publication

JPEG, PNG and WebP inputs: at most 5242880 bytes, 40000000 pixels and 16384 px per edge.
Animated/malformed files and MIME mismatches return 422. HEIC/HEIF is rejected; native
clients may convert it with their existing decoder, otherwise show an error.

Defaults, configurable with `IMAGE_*` settings:

| Media | Maximum edge | Maximum stored bytes |
| --- | ---: | ---: |
| Avatar | 512 | 512000 |
| Staff | 1024 | 1048576 |
| Gallery and service | 1600 | 1048576 |

Aspect ratio and transparency are preserved, no upscaling occurs, EXIF orientation is
corrected and metadata removed. JPEG/WebP quality starts at 84; five attempts at most
lower quality and dimensions. PNG remains lossless with bounded resizing. Failure to
meet the cap rejects the upload and never stores the original as a fallback.

A bounded process-local cache retains only SHA-256 hashes of this server's encoded
outputs, keyed by MIME, policy and decoder pixel limit. Only an exact byte match under
the same policy skips another decode/encode. Client flags cannot enable the shortcut.
Restarts, another API worker, stricter policies or eviction cause normal processing.
Images are never cached in Redis.

New objects carry an HMAC processing proof in R2 metadata binding bucket, key, MIME,
size, stored dimensions/pixel count and SHA-256. New profile, gallery, staff, service and admin catalog
references require a HEAD check of this proof and the authorized namespace. This trusts
server-only R2 credentials; a privileged credential holder can change storage. It does
not fetch external URLs. Existing unchanged legacy references remain readable; different
external/unmarked URLs are rejected. Bundled avatar identifiers remain supported.
Catalog admins may reuse validated gallery objects platform-wide; there is no separate
catalog upload endpoint. Create new staff without a photo, then upload and PATCH; staff
creation may also use an owned validated gallery object if its actual dimensions and
bytes satisfy the stricter staff policy.

Saving a URL takes a PostgreSQL transaction advisory lock through the repository commit.
Unchanged legacy URLs are compared with the current record under the lock, not a stale
authentication snapshot, so concurrent replacement cannot resurrect a retired object.
Repeated gallery attachment of the same URL returns its active existing row; change
captions/order through PATCH. Reviewed migration `0020_media_reference_guards` installs
invoker triggers on all seven media tables, so direct SQL and Supabase Data API writes
also take the URL lock. Direct `anon`/`authenticated` role writes cannot assign new hosted
URLs; they must use the backend API. Unchanged references, clearing and bundled avatars
remain supported. Server-only database/auth/service roles remain trusted administrators.

## Scheduled cleanup

Compose runs `media-cleanup` from the API image using
`python -m app.infrastructure.media.cleanup_worker`. GCP VM deployment pulls and starts
it. The worker refuses to scan/delete until all seven database guards are enabled.
It scans the three managed prefixes hourly with a default 24-hour minimum
object age. Configure `MEDIA_CLEANUP_INTERVAL_SECONDS` (minimum 60) and
`MEDIA_CLEANUP_GRACE_SECONDS` (minimum 3600). Cloud Run needs a separately scheduled sweep;
an API-only deployment does not run cleanup. Never expire public prefixes via lifecycle.

For each aged candidate, the worker takes the same URL lock, verifies its proof and
checks committed references in profiles, staff, active salon images, services, catalog
categories/subcategories and salon QR URLs. Other inactive records also protect shared
objects. RLS is set to `off` for this check: this does not bypass policies, but causes
a restricted role to fail rather than return a partial view. The worker needs a database
role able to read all these references, plus R2 List/Get/Put/Delete permissions.

Only objects enrolled by this release are deleted. Legacy/unmarked objects, failed HEAD
checks, policy-incompatible proofs and failed reference checks are preserved. Deletion
failures leave candidates for the next sweep. Replacements never eagerly delete old
objects; failed or ambiguous commits never trigger blind deletion. This covers replaced
avatars/staff/service photos, deleted gallery photos, abandoned PUTs and failed saves.
Expired grants without a successful PUT create no object to clean up.

Legacy accumulated media needs a separately reviewed inventory/migration before cleanup.
R2 secret rotation makes older proofs unverifiable until reviewed re-attestation; existing
references remain readable and those objects are not deleted. IMAGE_* changes require
coordinating frontend defaults and handling older proof policy values.

No new dependency is required. Review and explicitly apply migration
`0020_media_reference_guards` before deploying/enabling cleanup; it changes no media URLs
or stored records and leaves the raw baseline unchanged. Its downgrade removes only the
guards/function. The worker fails closed if they are absent or disabled. Deploy the API
and worker together, configure
externally reachable `PUBLIC_API_BASE_URL` and environment-driven CORS, then verify camera,
gallery, retry, replacement, shared references and cleanup on isolated staging resources.
Local mocks do not establish real R2/Postgres or device behavior. Production was not touched.
