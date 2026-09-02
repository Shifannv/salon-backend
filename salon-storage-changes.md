# Cloudflare R2 Image Storage — Changes & Status Report

This document details the full Cloudflare R2 image upload functionality implemented in the backend, what has been fixed/upgraded, what remains pending (future roadmap), and how the frontend applications should integrate with these endpoints.

---

## 1. Overview of Changes

| Area | Before | After (Fixed & Implemented) | Status |
|---|---|---|---|
| **MIME Validation** | Unrestricted string input | Enforced allow-list (`image/jpeg`, `image/png`, `image/webp`, `image/heic`, `image/heif`) via Pydantic validator (`HTTP 422` on invalid) | ✅ Fixed |
| **Salon Gallery Upload** | `POST /owner/me/images/upload-url` (had clean architecture leak with local settings import) | Fixed clean architecture, path organized: `salon-images/{salon_id}/{uuid}.{ext}` | ✅ Fixed |
| **Staff Photo Upload** | ❌ No endpoint existed | Added `POST /owner/me/staff/{staff_id}/photo-upload-url`, path: `staff-photos/{salon_id}/{staff_id}/{uuid}.{ext}` | ✅ Implemented |
| **User Avatar Upload** | ❌ No endpoint existed | Added `POST /profiles/me/avatar-upload-url` (available for customer, owner, staff), path: `avatars/{profile_id}/{uuid}.{ext}` | ✅ Implemented |
| **boto3 Performance** | Created a new S3 client on every presigned URL generation call | Lazy-initialized, thread-safe instance caching with `threading.Lock` | ✅ Fixed |
| **StorageGateway Port** | Only had upload and public URL methods | Added `_ALLOWED_CONTENT_TYPES` constant + `delete_object` abstract method and R2 implementation | ✅ Fixed |
| **Unit Test Coverage** | Zero unit tests for R2 gateway and upload use cases | 11 comprehensive gateway tests + use case tests for all upload paths | ✅ 92/92 Passing |

---

## 2. API Endpoints & Request/Response Contracts

### A. Salon Gallery Images (Owner/Staff)
- **Endpoint**: `POST /api/v1/owner/me/images/upload-url`
- **Auth**: Bearer Token (Owner / Staff)
- **Request Body**:
  ```json
  {
    "content_type": "image/jpeg",
    "filename": "salon_interior.jpg"
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "upload_url": "https://<account_id>.r2.cloudflarestorage.com/...",
    "public_url": "https://pub-xxx.r2.dev/salon-images/<salon_id>/<uuid>.jpeg",
    "expires_in": 300
  }
  ```
- **Post-Upload Persistence**:
  `POST /api/v1/owner/me/images` with `{ "url": "<public_url>", "caption": "Front view", "is_main": true }`

---

### B. Staff Member Photo (Owner/Staff)
- **Endpoint**: `POST /api/v1/owner/me/staff/{staff_id}/photo-upload-url`
- **Auth**: Bearer Token (Owner / Staff)
- **Request Body**:
  ```json
  {
    "content_type": "image/png",
    "filename": "barber_ameen.png"
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "upload_url": "https://<account_id>.r2.cloudflarestorage.com/...",
    "public_url": "https://pub-xxx.r2.dev/staff-photos/<salon_id>/<staff_id>/<uuid>.png",
    "expires_in": 300
  }
  ```
- **Post-Upload Persistence**:
  `PATCH /api/v1/owner/me/staff/{staff_id}` with `{ "photo_url": "<public_url>" }`

---

### C. Profile Avatar (Customers, Owners, Staff)
- **Endpoint**: `POST /api/v1/profiles/me/avatar-upload-url`
- **Auth**: Bearer Token (Any authenticated user)
- **Request Body**:
  ```json
  {
    "content_type": "image/webp",
    "filename": "my_avatar.webp"
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "upload_url": "https://<account_id>.r2.cloudflarestorage.com/...",
    "public_url": "https://pub-xxx.r2.dev/avatars/<profile_id>/<uuid>.webp",
    "expires_in": 300
  }
  ```
- **Post-Upload Persistence**:
  `PATCH /api/v1/profiles/me` with `{ "avatar_url": "<public_url>" }`

---

## 3. Frontend Client Direct-Upload Flow

Every image upload follows the secure 3-step direct-to-R2 pattern without streaming binary data through the FastAPI app server:

```
[ Frontend App ]               [ FastAPI Backend ]              [ Cloudflare R2 ]
       │                                │                               │
  1.   │─── POST /.../upload-url ───────▶│                               │
       │    {content_type, filename}    │                               │
       │                                │  Generates presigned PUT URL  │
       │◀── {upload_url, public_url} ───│                               │
       │                                                                │
  2.   │─── PUT <upload_url> (binary body + Content-Type header) ──────▶│
       │◀── 200 OK ─────────────────────────────────────────────────────│
       │                                                                │
  3.   │─── POST/PATCH with {"...url": public_url} ───▶│                │
       │    (Saves URL string in PostgreSQL DB)        │                │
       │◀── 200 OK (Updated entity response) ──────────│                │
```

### Direct Upload Code Example (Expo / Fetch):
```typescript
// Step 1: Request presigned URL
const { upload_url, public_url } = await api.post('/profiles/me/avatar-upload-url', {
  content_type: 'image/jpeg',
  filename: 'avatar.jpg'
});

// Step 2: Binary upload directly to Cloudflare R2
const fileBlob = await (await fetch(localImageUri)).blob();
const uploadRes = await fetch(upload_url, {
  method: 'PUT',
  headers: {
    'Content-Type': 'image/jpeg',
  },
  body: fileBlob,
});

if (!uploadRes.ok) {
  throw new Error('Failed to upload image to R2');
}

// Step 3: Persist URL in database
await api.patch('/profiles/me', {
  avatar_url: public_url
});
```

---

## 4. What Is Pending (Future Roadmap & Scope)

| Item | Reason / Dependency | Status |
|---|---|---|
| **Image Deletion from Database (`DELETE /owner/me/images/{id}`)** | The current PostgreSQL schema (`001_supabase_schema.sql`) does not have `is_active` on `salon_images`. Per project rules, soft delete is required and hard deletes are disallowed. The route currently returns `HTTP 501 Not Implemented`. When a reviewed Alembic migration adds `is_active`, this can be enabled. | ⏳ Pending DB Migration |
| **Physical R2 Object Cleanup on Deletion** | The `delete_object` method is implemented in `R2StorageGateway` and `StorageGateway` port. Once image deletion endpoint is active, it can optionally trigger R2 deletion or background object lifecycle cleanup. | ⏳ Ready in code, waiting for delete route |
| **Image Resizing / CDN Variants (Cloudflare Images)** | Direct transforms (e.g. `@200w`, `@thumb`) can be configured at Cloudflare CDN layer using Cloudflare Image Resizing with custom domains. | 💡 Optional Infrastructure Enhancement |

---

## 5. Testing & Validation

All tests pass cleanly:
```bash
./.venv/bin/python -m pytest
# 92 passed in 0.97s

./.venv/bin/python -m ruff check app tests
# All checks passed!
```
