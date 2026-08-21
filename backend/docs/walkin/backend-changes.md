# Backend — QR Walk-In Changes

## What Already Exists (No Changes Needed)

The backend is almost fully ready for QR walk-in. The following are **already implemented**:

| Component | Status | Location |
|---|---|---|
| `salons.qr_token` column (32-char hex, unique) | ✅ Done | `migrations/001_supabase_schema.sql` line 133 |
| `get_salon_by_qr(p_qr_token)` DB function | ✅ Done | SQL section 14 |
| `GET /v1/walkin/{token}` — resolve QR, public | ✅ Done | `routes/walkin.py` |
| `POST /v1/walkin/{token}/verify-phone` — OTP | ✅ Done | `routes/walkin.py` |
| `POST /v1/walkin/{token}/bookings` — create booking | ✅ Done | `routes/walkin.py` |
| `WalkInSalonResponse` schema (salon + services + staff) | ✅ Done | `schemas/walkin.py` |
| `source: "qr_walkin"` enum value | ✅ Done | `schemas/platform.py` |
| `WalkInUseCases.resolve_qr_token()` | ✅ Done | `use_cases/walkin.py` |
| `WalkInUseCases.create_walkin_booking()` | ✅ Done | `use_cases/walkin.py` |
| `PlatformRepository.get_salon_by_qr()` | ✅ Done | `repositories/platform_repository.py` |
| `GET /v1/availability` is public (no auth) | ✅ Done | `routes/bookings.py` |

---

## Required Change — Phase 1 ✅ DONE

### 1. `qr_token` in `OwnerSalonResponse` — Already present

Checked: `qr_token: str` was already in `OwnerSalonResponse` at line 118 of `schemas/platform.py`.
No change needed.

---

### 2. Enrich `WalkInSalonResponse` with `address` and `image_url` ✅

The slot-first UI mini-header needs the salon address and optional hero image.

**`schemas/walkin.py`** — added two fields:
```python
class WalkInSalonResponse(BaseModel):
    ...
    address: str | None = None      # for the mini-header location line
    image_url: str | None = None    # for the optional hero thumbnail
    ...
```

**`repositories/platform_repository.py` — `get_salon_by_qr()`** — added a second query
to fetch `address` and `image_url` from the `salons` table after QR validation:
```python
# Step 2: fetch extra display fields from the salons table
extra = await self.session.execute(
    text("select address, image_url from salons where id = :salon_id"),
    {"salon_id": str(salon["id"])},
)
extra_row = extra.mappings().one_or_none()
if extra_row:
    salon["address"] = extra_row["address"]
    salon["image_url"] = extra_row["image_url"]
```
No migration needed — columns already exist in the `salons` table.

---

### 3. CORS — walk-in web dev port added ✅

**`.env`** — added `http://localhost:3001` (Next.js default dev port for the walk-in app):
```
BACKEND_CORS_ORIGINS=[..., "http://localhost:3001", ...]
```

> When deploying to production, add the Vercel URL here:
> ```
> BACKEND_CORS_ORIGINS=[..., "https://walkin.yourdomain.com"]
> ```

---

## Required Change — CORS Configuration

The walk-in web app (hosted on Vercel) will call the backend. Add the Vercel domain to the FastAPI CORS allowed origins.

#### File: `backend/app/main.py` or `backend/app/core/config.py`

```python
# config.py — add to Settings
walkin_cors_origins: list[str] = Field(
    default_factory=list,
    description="Extra CORS origins for the walk-in web app",
)
```

```python
# main.py — update CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://walkin.yourdomain.com",   # production
        "http://localhost:3000",            # local dev of web app
        *settings.walkin_cors_origins,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Set via environment variable: `WALKIN_CORS_ORIGINS=["https://walkin.yourdomain.com"]`

---

## Recommended Addition — `get_salon_by_qr` Returns Services + Staff

Currently the DB function `get_salon_by_qr` only returns:
```sql
id, name, description, city, timezone, approval_mode
```

But `WalkInSalonResponse` also includes `services[]` and `staff[]`. These are fetched separately in `PlatformRepository.get_salon_by_qr()`. This is fine — the repository handles the join. No SQL migration needed.

Verify the repository is fetching services and staff after the QR resolve:

```bash
grep -A 30 "async def get_salon_by_qr" \
  backend/app/infrastructure/db/repositories/platform_repository.py
```

---

## Optional Phase 2 Additions

### 2. QR Token Rotation Endpoint

Allow an owner to invalidate and regenerate their QR token if it's been compromised (e.g. shared outside the shop).

```python
# routes/owner.py
@router.post(
    "/me/qr/rotate",
    response_model=OwnerSalonResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate salon QR token",
)
async def rotate_qr_token(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> OwnerSalonResponse:
    row = await _use_cases(session).rotate_qr_token(actor)
    return OwnerSalonResponse(**row)
```

**DB function needed:**
```sql
create or replace function rotate_salon_qr(p_owner_id uuid)
returns void language plpgsql security definer as $$
begin
  update salons
  set qr_token = encode(gen_random_bytes(16), 'hex')
  where owner_id = p_owner_id and is_active;
end $$;
```

### 3. Walk-In Pause Toggle

```python
# schemas/platform.py
class UpdateSalonSettingsRequest(BaseModel):
    ...
    walkin_enabled: bool | None = None  # ADD

# SQL migration
alter table salons add column if not exists walkin_enabled bool not null default true;

# get_salon_by_qr — add condition:
where s.qr_token = p_qr_token
  and s.is_active
  and s.profile_completed
  and s.walkin_enabled    -- ADD THIS
```

When `walkin_enabled = false`, `GET /v1/walkin/{token}` returns 404, and the web app shows "Walk-in booking is paused for today."

### 4. Rate Limiting on QR Endpoint

The `GET /v1/walkin/{token}` endpoint is public and unauthenticated. Add IP-based rate limiting to prevent scraping.

```python
# Using slowapi (already a common FastAPI pattern)
pip install slowapi

# main.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# routes/walkin.py
@router.get("/{qr_token}", ...)
@limiter.limit("30/minute")
async def resolve_qr(...):
    ...
```

### 5. Walk-In Analytics (Future)

Track how many scans vs bookings each QR generates:

```sql
create table qr_scan_events (
  id uuid primary key default gen_random_uuid(),
  salon_id uuid not null references salons(id),
  scanned_at timestamptz not null default now(),
  ip_hash text,       -- hashed for privacy
  booked bool default false
);
```

---

## Summary

| Change | Priority | File |
|---|---|---|
| Add `qr_token` to `OwnerSalonResponse` | **Phase 1 — Required** | `schemas/platform.py` |
| Add walk-in web CORS origin | **Phase 1 — Required** | `main.py` / `config.py` |
| QR token rotation endpoint | Phase 2 | `routes/owner.py` + SQL |
| Walk-in pause toggle | Phase 2 | `schemas/platform.py` + SQL migration |
| Rate limiting on public walkin route | Phase 2 | `main.py` + slowapi |
| Walk-in scan analytics | Phase 3 | New table + endpoint |
