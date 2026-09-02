Let me start by reading the project documentation and understanding the current state of the codebase before planning the R2 integration.

Viewed README.md:1-65
Viewed ARCHITECTURE.md:1-115
Listed directory app
Viewed tech-stack.md:1-95
Listed directory infrastructure
Listed directory application
Listed directory r2
Listed directory ports
Listed directory use_cases
Viewed storage.py:1-147
Viewed storage_gateway.py:1-40
Listed directory routes
Viewed config.py:1-82
Viewed owner.py:1-605
Viewed deps.py:1-95
Viewed platform.py:1-100
Viewed platform.py:100-220
Listed directory schemas
Searched for "ImageUpload"
Searched for "SalonImage"
Viewed platform.py:85-220
Viewed platform.py:535-573

Now let me look at the infrastructure DB repository to see how image operations are handled, and check the requirements files to see if boto3 is already listed:

Searched for "salon_image"
Viewed requirements.txt:1-24
Viewed platform_repository.py:330-400
Viewed platform_repository.py:520-610

Now let me check the existing tests for R2 and the .env.example:

Searched for "r2"
Viewed .env.example:1-36
Listed directory tests
Viewed exceptions.py:1-136
Listed directory unit
Viewed platform.py:1-50
Viewed test_owner_use_cases.py:1-286

Now I have a thorough understanding of the codebase. Let me also check the `customer.py` route to see if there's any image upload for staff/profiles, and the `pyproject.toml`:

Searched for "upload"
Viewed pyproject.toml:1-73

Now I have a comprehensive picture of the current state. Let me also check the `conftest.py` to understand the test infrastructure, then create the implementation plan:

Viewed conftest.py:1-150
Viewed .env.gcp.example:1-31

Now I have a complete picture. Let me assess what "update the full Cloudflare R2 functionality" means in this context. The current state:

**What already exists (working):**
- `R2StorageGateway` with presigned PUT URL generation and public URL construction
- `StorageGateway` abstract port
- Config settings for R2
- `get_image_upload_url` use case for owner salon images
- Owner routes: `POST /me/images/upload-url`, `GET/POST/PATCH /me/images`
- `boto3` dependency in place

**What's missing or needs improvement:**
1. **No staff photo upload support** — staff have a `photo_url` field but no presigned URL endpoint
2. **No profile/avatar upload support** — profiles have `avatar_url` but no presigned URL endpoint  
3. **Content-type validation** — no validation of allowed MIME types in the request
4. **No delete support** — delete image route returns 501 with no R2 object deletion
5. **Object key path design** — different resource types need separate path prefixes
6. **No unit tests for R2 gateway** — R2StorageGateway has no tests
7. **The `ImageUploadUrlRequest` content_type has no validation** — accepts any MIME string
8. **R2 gateway creates a new boto3 client on every presign call** — could be improved

Let me check what the staff entity and schema look like to fully understand what's needed:

Viewed staff.py:1-66
Searched for "photo_url\|avatar_url\|image_url"
Searched for "photo_url|avatar_url|image_url"

Now I have everything I need to create the implementation plan. Let me create it:

Created implementation_plan.md

Here's the full picture of what I found and what needs to be done.

## Current State

The R2 integration is **partially built** — it only covers salon gallery images (`POST /owner/me/images/upload-url`). It's missing coverage for two other image types that the schema already supports.

## Plan Summary

The plan adds these improvements across 7 areas:

| # | What | Why |
|---|---|---|
| 1 | **Content-type validation** | `content_type` currently accepts any string — needs an allow-list |
| 2 | **Staff photo upload URL** | `POST /owner/me/staff/{staff_id}/photo-upload-url` — staff have `photo_url` in DB but no upload endpoint |
| 3 | **Avatar upload URL** | `POST /profiles/me/avatar-upload-url` — profiles have `avatar_url` but no upload endpoint |
| 4 | **boto3 client caching** | Currently creates a new S3 client on every presign call (TCP overhead per request) |
| 5 | **`delete_object` port method** | Forward-compatible stub for when image deletion schema migration lands |
| 6 | **R2 gateway unit tests** | Zero test coverage today |
| 7 | **Use case unit tests** | Add tests for new upload methods |

Two open questions are highlighted in the plan. Please review and click **Proceed** (or tell me your answers to the open questions) to begin implementation.



#	What	Why
1	Content-type validation	content_type currently accepts any string — needs an allow-list
2	Staff photo upload URL	POST /owner/me/staff/{staff_id}/photo-upload-url — staff have photo_url in DB but no upload endpoint
3	Avatar upload URL	POST /profiles/me/avatar-upload-url — profiles have avatar_url but no upload endpoint
4	boto3 client caching	Currently creates a new S3 client on every presign call (TCP overhead per request)
5	delete_object port method	Forward-compatible stub for when image deletion schema migration lands
6	R2 gateway unit tests	Zero test coverage today
7	Use case unit tests	Add tests for new upload methods