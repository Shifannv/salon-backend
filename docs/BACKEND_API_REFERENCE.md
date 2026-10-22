# Complete backend API reference for frontend teams

Generated from the current local FastAPI routes and Pydantic OpenAPI models on
22 October 2026. This is a source snapshot, not confirmation of a deployed release.
Regenerate/compare with the target server's `/openapi.json` when the backend changes.

## How to use this reference

- Use [Client developer handoff](CLIENT_DEVELOPER_HANDOFF.md) for screens, workflows,
  client configuration and responsibilities. This file contains the full endpoint and
  data-model inventory rather than repeating those product instructions.
- Prepend the environment's API origin to each full path below. Most paths include
  `/v1`; health paths do not. Protected calls send `Authorization: Bearer <Supabase access token>`.
- Request bodies are JSON unless a different content type is stated. Model links lead
  to field tables. Required means required by the declared schema; nullable is shown
  as `or null`. Cross-field validators and business permissions can impose additional rules.
- Role gates shown are extracted from route dependencies. Where only Bearer is shown,
  it does **not** mean every signed-in role can perform the operation. See access notes
  below and application contracts; resource ownership remains server-enforced.
- No real environment file was loaded, application lifespan started or external
  service contacted for this export. No endpoint was exercised. Routes and model
  schemas were generated locally using isolated documentation settings.

## Access and availability notes

| Area | Additional behavior beyond route signatures |
| --- | --- |
| Public discovery/slots | Publication, activity, setup and booking eligibility apply; follow returned salon/payment capabilities |
| Auth/profile | Authenticated actor comes from verified JWT subject and active database profile; owner-access intentionally promotes customers |
| Owner workspace | Owning salon and role checks apply; pending salons retain permitted setup access, daily business requires approval |
| Bookings | Customer own-booking and owner/staff salon scope; source restrictions; transitions and collection guards enforced server-side |
| QR | Resolve/OTP public; booking requires customer role and token-matching salon; invalid tokens return qr_not_found |
| Payout details | Owner-only, including while pending; responses mask bank details |
| Payments | Provider capabilities, actor/booking ownership and ledger rules apply; disabled by default |
| Subscription billing | Owner scope; provider disabled by default; mobile native purchase is disallowed by current project contract |
| Admin | Database super_admin role; aal2 required when ADMIN_REQUIRE_MFA is enabled; do not expose public admin registration |
| Support | Ticket ownership/authorized salon/admin scope; email-event status belongs to its customer |
| Media gateway | Signed upload/result token is a credential; namespace, expiry, content and processing rules apply |
| Deletion | Actor-owned verification; final confirm locks account; status uses its separate private token |
| Webhook | Conditional mount only with configured payment/subscription webhook provider; provider-to-backend, never browser-to-backend |

Use idempotency keys for booking creation, collection and completion. Support/provider
operations require them in application logic even where a header is marked optional
by OpenAPI. Preserve the same key/body when retrying one unknown operation. Header
presence and schema alone do not describe all business requirements.

The webhook is included below by explicitly attaching its router **only to the local
documentation app**, without enabling any provider or changing application code. A
default provider-disabled server omits that operation. Other payment/billing routes
may be mounted while returning disabled/unavailable responses.

## Errors and schema limitations

Runtime application/validation errors use the centrally mapped envelope:

```json
{"error":{"code":"validation_error","message":"Request validation failed","details":[]}}
```

Handle 401, 403, 404, 409, 422, 429 and service/network errors. OpenAPI currently lists
FastAPI's generated HTTPValidationError/ValidationError models for many 422 responses;
those generated models do not override the actual custom runtime envelope above.
Success codes below are declared contracts, not executed test results. Error status
lists are incomplete in the generated OpenAPI. Never display raw database errors.

Pydantic validators/application guards can impose constraints not represented in model
tables. PATCH omission differs from explicit null, and payout PUT uses documented merge
semantics. A schema field default/enum is not evidence that a provider or premium
feature is operational. Provider payloads, raw signed uploads and signatures need
their specialized contracts. Conditional computed fields and typed money/status
variants must be interpreted per response model, not globally.

## Inventory

**142 operations**, including one conditionally mounted webhook; **136 named schemas**. GET and POST on the same path count separately.

| API group | Operations |
| --- | --- |
| [health](#group-health) | 4 |
| [account deletion](#group-account-deletion) | 7 |
| [media](#group-media) | 3 |
| [reports](#group-reports) | 1 |
| [auth](#group-auth) | 4 |
| [profiles](#group-profiles) | 3 |
| [admin](#group-admin) | 17 |
| [customer](#group-customer) | 2 |
| [salon owner](#group-salon-owner) | 33 |
| [payments](#group-payments) | 11 |
| [support](#group-support) | 4 |
| [salons](#group-salons) | 5 |
| [catalog](#group-catalog) | 2 |
| [bookings](#group-bookings) | 13 |
| [booking actions](#group-booking-actions) | 6 |
| [notifications](#group-notifications) | 5 |
| [walkin](#group-walkin) | 4 |
| [subscriptions](#group-subscriptions) | 9 |
| [subscription billing](#group-subscription-billing) | 8 |
| [webhooks](#group-webhooks) | 1 |

Framework documentation routes, separate from the business/health inventory: `GET /openapi.json`, `GET /docs`, `GET /docs/oauth2-redirect`, `GET /redoc` (default local configuration; deployment may restrict exposure).

<a id="group-health"></a>

## Health

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/health` | Check API process health | 200 |
| GET | `/health/db` | Check database connectivity | 200 |
| GET | `/health/redis` | Check Redis cache connectivity | 200 |
| GET | `/health/ready` | Readiness | 200 |

### GET `/health`

**Purpose:** Check API process health.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Return process health.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [HealthResponse](#model-healthresponse).

**Source:** [backend/app/api/v1/routes/health.py](../backend/app/api/v1/routes/health.py) (`health`).

### GET `/health/db`

**Purpose:** Check database connectivity.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Probe the database connection.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [DatabaseHealthResponse](#model-databasehealthresponse).

**Source:** [backend/app/api/v1/routes/health.py](../backend/app/api/v1/routes/health.py) (`database_health`).

### GET `/health/redis`

**Purpose:** Check Redis cache connectivity.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Probe the Redis cache connection.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [RedisHealthResponse](#model-redishealthresponse).

**Source:** [backend/app/api/v1/routes/health.py](../backend/app/api/v1/routes/health.py) (`redis_health`).

### GET `/health/ready`

**Purpose:** Readiness.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [HealthResponse](#model-healthresponse).

**Source:** [backend/app/api/v1/routes/health.py](../backend/app/api/v1/routes/health.py) (`readiness`).

<a id="group-account-deletion"></a>

## Account Deletion

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| POST | `/v1/account/deletion/challenges` | Send a deletion verification code to your own verified email or phone | 202 |
| POST | `/v1/account/deletion/challenges/{challenge_id}/verify` | Verify the code; returns a one-time confirmation token (nothing is deleted yet) | 200 |
| POST | `/v1/account/deletion` | Irreversibly delete the account (explicit confirmation) | 202 |
| GET | `/v1/account/deletion/{request_id}` | Deletion progress; authenticated by X-Status-Token, not the JWT | 200 |
| GET | `/v1/admin/account-deletions` | Account deletion ledger (no personal identifiers) | 200 |
| GET | `/v1/admin/deleted-salons` | Salons closed by their owner's account deletion (month-end review queue) | 200 |
| GET | `/v1/admin/deleted-salons/{salon_id}/statement` | Month-end money totals of a closed salon (no personal or booking detail) | 200 |

### POST `/v1/account/deletion/challenges`

**Purpose:** Send a deletion verification code to your own verified email or phone.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

**Body:** `application/json`, required; [StartDeletionChallengeRequest](#model-startdeletionchallengerequest).

**Success 202:** `application/json`: [DeletionChallengeResponse](#model-deletionchallengeresponse).

**Source:** [backend/app/api/v1/routes/account_deletion.py](../backend/app/api/v1/routes/account_deletion.py) (`start_deletion_challenge`).

### POST `/v1/account/deletion/challenges/{challenge_id}/verify`

**Purpose:** Verify the code; returns a one-time confirmation token (nothing is deleted yet).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `challenge_id` | path | yes | string (uuid) |  |

**Body:** `application/json`, required; [VerifyDeletionChallengeRequest](#model-verifydeletionchallengerequest).

**Success 200:** `application/json`: [VerifiedDeletionChallengeResponse](#model-verifieddeletionchallengeresponse).

**Source:** [backend/app/api/v1/routes/account_deletion.py](../backend/app/api/v1/routes/account_deletion.py) (`verify_deletion_challenge`).

### POST `/v1/account/deletion`

**Purpose:** Irreversibly delete the account (explicit confirmation).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Locks the account immediately and queues permanent erasure of the identity and personal data. There is no recovery. For an owner the worker first cancels every upcoming booking at their salons (customers are notified, online payments refunded) and only then erases.

**Body:** `application/json`, required; [ConfirmAccountDeletionRequest](#model-confirmaccountdeletionrequest).

**Success 202:** `application/json`: [AccountDeletionAcceptedResponse](#model-accountdeletionacceptedresponse).

**Source:** [backend/app/api/v1/routes/account_deletion.py](../backend/app/api/v1/routes/account_deletion.py) (`confirm_account_deletion`).

### GET `/v1/account/deletion/{request_id}`

**Purpose:** Deletion progress; authenticated by X-Status-Token, not the JWT.

**Access:** Private X-Status-Token from accepted deletion; no bearer.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `request_id` | path | yes | string (uuid) |  |
| `x-status-token` | header | yes | string | minLength=20; maxLength=128 |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [AccountDeletionStatusResponse](#model-accountdeletionstatusresponse).

**Source:** [backend/app/api/v1/routes/account_deletion.py](../backend/app/api/v1/routes/account_deletion.py) (`get_deletion_status`).

### GET `/v1/admin/account-deletions`

**Purpose:** Account deletion ledger (no personal identifiers).

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `limit` | query | no | integer | minimum=1; maximum=200; default=50 |
| `offset` | query | no | integer | minimum=0; default=0 |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [AdminAccountDeletionResponse](#model-adminaccountdeletionresponse).

**Source:** [backend/app/api/v1/routes/account_deletion.py](../backend/app/api/v1/routes/account_deletion.py) (`list_account_deletions`).

### GET `/v1/admin/deleted-salons`

**Purpose:** Salons closed by their owner's account deletion (month-end review queue).

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `limit` | query | no | integer | minimum=1; maximum=200; default=50 |
| `offset` | query | no | integer | minimum=0; default=0 |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [AdminAccountDeletionResponse](#model-adminaccountdeletionresponse).

**Source:** [backend/app/api/v1/routes/account_deletion.py](../backend/app/api/v1/routes/account_deletion.py) (`list_closed_salons`).

### GET `/v1/admin/deleted-salons/{salon_id}/statement`

**Purpose:** Month-end money totals of a closed salon (no personal or booking detail).

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `salon_id` | path | yes | string (uuid) |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [ClosedSalonStatementResponse](#model-closedsalonstatementresponse).

**Source:** [backend/app/api/v1/routes/account_deletion.py](../backend/app/api/v1/routes/account_deletion.py) (`closed_salon_statement`).

<a id="group-media"></a>

## Media

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| POST | `/v1/customer/profile/avatar` | Upload Avatar | 200 |
| PUT | `/v1/media/uploads/{token}` | Upload Signed Image | 204 |
| GET | `/v1/media/results/{token}` | Get Image Family | 200 |

### POST `/v1/customer/profile/avatar`

**Purpose:** Upload Avatar.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

**Body:** `multipart/form-data`, required; object.

**Success 200:** `application/json`: [AvatarResponse](#model-avatarresponse).

**Source:** [backend/app/api/v1/routes/media.py](../backend/app/api/v1/routes/media.py) (`upload_avatar`).

### PUT `/v1/media/uploads/{token}`

**Purpose:** Upload Signed Image.

**Access:** Signed URL/token capability; no bearer.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `token` | path | yes | string |  |

**Body:** Raw image bytes with matching Content-Type and signed grant; not an empty-body operation.

**Success 204:** No response body.

**Source:** [backend/app/api/v1/routes/media.py](../backend/app/api/v1/routes/media.py) (`upload_signed_image`).

### GET `/v1/media/results/{token}`

**Purpose:** Get Image Family.

**Access:** Signed URL/token capability; no bearer.

Read variant metadata with a read-only token; it cannot upload.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `token` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [ImageFamilyResponse](#model-imagefamilyresponse).

**Source:** [backend/app/api/v1/routes/media.py](../backend/app/api/v1/routes/media.py) (`get_image_family`).

<a id="group-reports"></a>

## Reports

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| POST | `/v1/reports` | Submit Report | 201 |

### POST `/v1/reports`

**Purpose:** Submit Report.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

**Body:** `application/json`, required; [ReportRequest](#model-reportrequest).

**Success 201:** `application/json`: [ReportResponse](#model-reportresponse).

**Source:** [backend/app/api/v1/routes/reports.py](../backend/app/api/v1/routes/reports.py) (`submit_report`).

<a id="group-auth"></a>

## Auth

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| POST | `/v1/auth/forgot-password` | Forgot Password | 202 |
| POST | `/v1/auth/refresh` | Refresh a Supabase Auth session | 200 |
| GET | `/v1/auth/me` | Get the current authenticated profile | 200 |
| POST | `/v1/auth/owner-access` | Claim salon-owner access for the current account | 200 |

### POST `/v1/auth/forgot-password`

**Purpose:** Forgot Password.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

**Body:** `application/json`, required; [ForgotPasswordRequest](#model-forgotpasswordrequest).

**Success 202:** `application/json`: [ForgotPasswordResponse](#model-forgotpasswordresponse).

**Source:** [backend/app/api/v1/routes/auth.py](../backend/app/api/v1/routes/auth.py) (`forgot_password`).

### POST `/v1/auth/refresh`

**Purpose:** Refresh a Supabase Auth session.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Refresh a Supabase Auth session using a refresh token.

**Body:** `application/json`, required; [RefreshRequest](#model-refreshrequest).

**Success 200:** `application/json`: [TokenResponse](#model-tokenresponse).

**Source:** [backend/app/api/v1/routes/auth.py](../backend/app/api/v1/routes/auth.py) (`refresh`).

### GET `/v1/auth/me`

**Purpose:** Get the current authenticated profile.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Return the profile resolved from the verified Supabase JWT subject.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [app__api__v1__schemas__auth__ProfileResponse](#model-app__api__v1__schemas__auth__profileresponse).

**Source:** [backend/app/api/v1/routes/auth.py](../backend/app/api/v1/routes/auth.py) (`me`).

### POST `/v1/auth/owner-access`

**Purpose:** Claim salon-owner access for the current account.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Ensure the signed-in account holds a salon-workspace role, and return it.

The owner app calls this once per sign-in. It is idempotent, so a returning owner
pays one no-op round-trip and a brand-new Google account gets the ``owner`` role it
needs before `GET /salons/me` is ever asked for.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [app__api__v1__schemas__auth__ProfileResponse](#model-app__api__v1__schemas__auth__profileresponse).

**Source:** [backend/app/api/v1/routes/auth.py](../backend/app/api/v1/routes/auth.py) (`owner_access`).

<a id="group-profiles"></a>

## Profiles

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/v1/profiles/me` | Get current profile | 200 |
| PATCH | `/v1/profiles/me` | Update current profile | 200 |
| POST | `/v1/profiles/me/avatar-upload-url` | Get a signed upload URL for profile avatar | 200 |

### GET `/v1/profiles/me`

**Purpose:** Get current profile.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Return the authenticated profile.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [app__api__v1__schemas__auth__ProfileResponse](#model-app__api__v1__schemas__auth__profileresponse).

**Source:** [backend/app/api/v1/routes/profiles.py](../backend/app/api/v1/routes/profiles.py) (`get_my_profile`).

### PATCH `/v1/profiles/me`

**Purpose:** Update current profile.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Update the authenticated user's profile (e.g. phone number or full name).

When ``avatar_url`` is changed, provider-owned cleanup is attempted where supported.

**Body:** `application/json`, required; [ProfileUpdateRequest](#model-profileupdaterequest).

**Success 200:** `application/json`: [app__api__v1__schemas__auth__ProfileResponse](#model-app__api__v1__schemas__auth__profileresponse).

**Source:** [backend/app/api/v1/routes/profiles.py](../backend/app/api/v1/routes/profiles.py) (`update_my_profile`).

### POST `/v1/profiles/me/avatar-upload-url`

**Purpose:** Get a signed upload URL for profile avatar.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Returns a short-lived signed PUT URL and the resulting public URL for uploading a profile avatar through the backend image validation gateway.

Available to all authenticated roles (customer, owner, staff).

**Upload flow:**
1. Call this endpoint to get `upload_url` and `public_url`.
2. `PUT <upload_url>` with the image binary and `Content-Type: <your_mime_type>` header.
3. Call `PATCH /profiles/me` with `{ "avatar_url": "<public_url>" }` to persist.

**Body:** `application/json`, required; [ImageUploadUrlRequest](#model-imageuploadurlrequest).

**Success 200:** `application/json`: [ImageUploadUrlResponse](#model-imageuploadurlresponse).

**Source:** [backend/app/api/v1/routes/profiles.py](../backend/app/api/v1/routes/profiles.py) (`get_avatar_upload_url`).

<a id="group-admin"></a>

## Admin

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| POST | `/v1/admin/salons` | Create salon owner and salon | 201 |
| GET | `/v1/admin/salons` | List all salons (admin) | 200 |
| GET | `/v1/admin/salons/{salon_id}` | Get Salon | 200 |
| PATCH | `/v1/admin/salons/{salon_id}` | Update salon (admin) | 200 |
| GET | `/v1/admin/salons/{salon_id}/onboarding` | Get Salon Onboarding | 200 |
| POST | `/v1/admin/salons/{salon_id}/approve` | Approve Salon | 200 |
| POST | `/v1/admin/salons/{salon_id}/reject` | Reject Salon | 200 |
| POST | `/v1/admin/salons/{salon_id}/deactivate` | Deactivate salon and ban owner | 200 |
| GET | `/v1/admin/catalog/categories` | List service categories (admin) | 200 |
| POST | `/v1/admin/catalog/categories` | Create service category | 201 |
| PATCH | `/v1/admin/catalog/categories/{category_id}` | Update service category | 200 |
| POST | `/v1/admin/catalog/categories/{category_id}/deactivate` | Deactivate service category | 200 |
| GET | `/v1/admin/catalog/categories/{category_id}/subcategories` | List subcategories (admin) | 200 |
| POST | `/v1/admin/catalog/subcategories` | Create service subcategory | 201 |
| PATCH | `/v1/admin/catalog/subcategories/{subcategory_id}` | Update service subcategory | 200 |
| POST | `/v1/admin/catalog/subcategories/{subcategory_id}/deactivate` | Deactivate service subcategory | 200 |
| GET | `/v1/admin/catalog/languages` | List supported languages | 200 |

### POST `/v1/admin/salons`

**Purpose:** Create salon owner and salon.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

Creates a Supabase Auth user and a salon in one transaction. If the salon insert fails, the auth user is banned to prevent orphans.

**Body:** `application/json`, required; [AdminCreateSalonRequest](#model-admincreatesalonrequest).

**Success 201:** `application/json`: [AdminSalonResponse](#model-adminsalonresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`create_salon`).

### GET `/v1/admin/salons`

**Purpose:** List all salons (admin).

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

List all salons with owner info — paginated.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `search` | query | no | string or null |  |
| `approval_status` | query | no | `"pending" \| "approved" \| "rejected"` or null |  |
| `limit` | query | no | integer | minimum=1; maximum=200; default=50 |
| `offset` | query | no | integer | minimum=0; default=0 |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [AdminSalonResponse](#model-adminsalonresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`list_salons`).

### GET `/v1/admin/salons/{salon_id}`

**Purpose:** Get Salon.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `salon_id` | path | yes | string (uuid) |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [AdminSalonResponse](#model-adminsalonresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`get_salon`).

### PATCH `/v1/admin/salons/{salon_id}`

**Purpose:** Update salon (admin).

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

Update admin-editable salon fields.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `salon_id` | path | yes | string |  |

**Body:** `application/json`, required; [AdminUpdateSalonRequest](#model-adminupdatesalonrequest).

**Success 200:** `application/json`: [AdminSalonResponse](#model-adminsalonresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`update_salon`).

### GET `/v1/admin/salons/{salon_id}/onboarding`

**Purpose:** Get Salon Onboarding.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `salon_id` | path | yes | string (uuid) |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [AdminSalonOnboardingResponse](#model-adminsalononboardingresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`get_salon_onboarding`).

### POST `/v1/admin/salons/{salon_id}/approve`

**Purpose:** Approve Salon.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `salon_id` | path | yes | string (uuid) |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [AdminSalonResponse](#model-adminsalonresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`approve_salon`).

### POST `/v1/admin/salons/{salon_id}/reject`

**Purpose:** Reject Salon.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `salon_id` | path | yes | string (uuid) |  |

**Body:** `application/json`, required; [AdminRejectSalonRequest](#model-adminrejectsalonrequest).

**Success 200:** `application/json`: [AdminSalonResponse](#model-adminsalonresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`reject_salon`).

### POST `/v1/admin/salons/{salon_id}/deactivate`

**Purpose:** Deactivate salon and ban owner.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

Soft-delete the salon and ban the owner's Supabase Auth account.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `salon_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [AdminDeactivateSalonResponse](#model-admindeactivatesalonresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`deactivate_salon`).

### GET `/v1/admin/catalog/categories`

**Purpose:** List service categories (admin).

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

List all service categories including inactive ones.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `include_inactive` | query | no | boolean | default=false |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [CategoryResponse](#model-categoryresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`list_categories`).

### POST `/v1/admin/catalog/categories`

**Purpose:** Create service category.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

Create a new service category.

**Body:** `application/json`, required; [CategoryCreateRequest](#model-categorycreaterequest).

**Success 201:** `application/json`: [CategoryResponse](#model-categoryresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`create_category`).

### PATCH `/v1/admin/catalog/categories/{category_id}`

**Purpose:** Update service category.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

Update a service category.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `category_id` | path | yes | string |  |

**Body:** `application/json`, required; [CategoryUpdateRequest](#model-categoryupdaterequest).

**Success 200:** `application/json`: [CategoryResponse](#model-categoryresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`update_category`).

### POST `/v1/admin/catalog/categories/{category_id}/deactivate`

**Purpose:** Deactivate service category.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

Soft-delete a service category.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `category_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [CategoryResponse](#model-categoryresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`deactivate_category`).

### GET `/v1/admin/catalog/categories/{category_id}/subcategories`

**Purpose:** List subcategories (admin).

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

List all subcategories for a category.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `category_id` | path | yes | string |  |
| `include_inactive` | query | no | boolean | default=false |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [SubcategoryResponse](#model-subcategoryresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`list_subcategories`).

### POST `/v1/admin/catalog/subcategories`

**Purpose:** Create service subcategory.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

Create a new service subcategory.

**Body:** `application/json`, required; [SubcategoryCreateRequest](#model-subcategorycreaterequest).

**Success 201:** `application/json`: [SubcategoryResponse](#model-subcategoryresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`create_subcategory`).

### PATCH `/v1/admin/catalog/subcategories/{subcategory_id}`

**Purpose:** Update service subcategory.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

Update a service subcategory.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `subcategory_id` | path | yes | string |  |

**Body:** `application/json`, required; [SubcategoryUpdateRequest](#model-subcategoryupdaterequest).

**Success 200:** `application/json`: [SubcategoryResponse](#model-subcategoryresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`update_subcategory`).

### POST `/v1/admin/catalog/subcategories/{subcategory_id}/deactivate`

**Purpose:** Deactivate service subcategory.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

Soft-delete a service subcategory.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `subcategory_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [SubcategoryResponse](#model-subcategoryresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`deactivate_subcategory`).

### GET `/v1/admin/catalog/languages`

**Purpose:** List supported languages.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Return the languages reference table (accessible to all authenticated users).

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [app__api__v1__schemas__admin__LanguageResponse](#model-app__api__v1__schemas__admin__languageresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`list_languages`).

<a id="group-customer"></a>

## Customer

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/v1/customer/profile` | Get customer profile | 200 |
| PATCH | `/v1/customer/profile` | Update customer profile | 200 |

### GET `/v1/customer/profile`

**Purpose:** Get customer profile.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Return the authenticated customer profile.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [app__api__v1__schemas__platform__ProfileResponse](#model-app__api__v1__schemas__platform__profileresponse).

**Source:** [backend/app/api/v1/routes/customer.py](../backend/app/api/v1/routes/customer.py) (`get_profile`).

### PATCH `/v1/customer/profile`

**Purpose:** Update customer profile.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Update the authenticated customer's profile.

**Body:** `application/json`, required; [ProfileUpdateRequest](#model-profileupdaterequest).

**Success 200:** `application/json`: [app__api__v1__schemas__platform__ProfileResponse](#model-app__api__v1__schemas__platform__profileresponse).

**Source:** [backend/app/api/v1/routes/customer.py](../backend/app/api/v1/routes/customer.py) (`update_profile`).

<a id="group-salon-owner"></a>

## Salon Owner

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/v1/salons/me` | Get owner salon | 200 |
| PATCH | `/v1/salons/me` | Update owner salon | 200 |
| POST | `/v1/salons/me/complete-profile` | Complete owner salon profile | 200 |
| PATCH | `/v1/salons/me/settings` | Update owner salon settings | 200 |
| GET | `/v1/salons/me/payout-account` | Get owner payout account (masked) | 200 |
| PUT | `/v1/salons/me/payout-account` | Save owner payout account | 200 |
| GET | `/v1/salons/me/payout-account/history` | Payout account change history | 200 |
| GET | `/v1/salons/me/setup-status` | Get owner setup checklist | 200 |
| GET | `/v1/salons/me/qr` | Get salon walk-in QR code URL or SVG | 200 |
| POST | `/v1/salons/me/images/upload-url` | Get a signed upload URL for a salon image | 200 |
| GET | `/v1/salons/me/images` | List owner salon images | 200 |
| POST | `/v1/salons/me/images` | Create owner salon image | 201 |
| PATCH | `/v1/salons/me/images/{image_id}` | Update owner salon image | 200 |
| DELETE | `/v1/salons/me/images/{image_id}` | Delete owner salon image | 204 |
| GET | `/v1/salons/me/holidays` | List owner salon holidays | 200 |
| POST | `/v1/salons/me/holidays` | Create owner salon holiday | 201 |
| DELETE | `/v1/salons/me/holidays/{holiday_id}` | Delete owner salon holiday | 204 |
| GET | `/v1/salons/me/services` | List Services | 200 |
| POST | `/v1/salons/me/services` | Create owner salon service | 201 |
| PATCH | `/v1/salons/me/services/{service_id}` | Update owner salon service | 200 |
| DELETE | `/v1/salons/me/services/{service_id}` | Deactivate owner salon service | 200 |
| GET | `/v1/salons/me/staff` | List Staff | 200 |
| POST | `/v1/salons/me/staff` | Create owner salon staff | 201 |
| PATCH | `/v1/salons/me/staff/{staff_id}` | Update owner salon staff | 200 |
| DELETE | `/v1/salons/me/staff/{staff_id}` | Deactivate owner salon staff | 200 |
| POST | `/v1/salons/me/staff/{staff_id}/services` | Assign service to staff | 200 |
| GET | `/v1/salons/me/staff/{staff_id}/services` | List services assigned to staff | 200 |
| POST | `/v1/salons/me/staff/{staff_id}/photo-upload-url` | Get a signed upload URL for a staff photo | 200 |
| GET | `/v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages` | List languages for a staff service assignment | 200 |
| PUT | `/v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages` | Set languages for a staff service assignment | 200 |
| GET | `/v1/salons/me/blocks` | List blocked slots for this salon | 200 |
| POST | `/v1/salons/me/blocks` | Create a blocked slot | 201 |
| DELETE | `/v1/salons/me/blocks/{block_id}` | Delete a blocked slot | 204 |

### GET `/v1/salons/me`

**Purpose:** Get owner salon.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Return the authenticated owner's salon.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [OwnerSalonResponse](#model-ownersalonresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`get_my_salon`).

### PATCH `/v1/salons/me`

**Purpose:** Update owner salon.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Update owner-editable salon profile fields.

**Body:** `application/json`, required; [OwnerSalonUpdateRequest](#model-ownersalonupdaterequest).

**Success 200:** `application/json`: [OwnerSalonResponse](#model-ownersalonresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`update_my_salon`).

### POST `/v1/salons/me/complete-profile`

**Purpose:** Complete owner salon profile.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Create/update the owner salon from onboarding data and mark it complete.

**Body:** `application/json`, optional; [OwnerSalonCompleteProfileRequest](#model-ownersaloncompleteprofilerequest) or null.

**Success 200:** `application/json`: [OwnerSalonResponse](#model-ownersalonresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`complete_profile`).

### PATCH `/v1/salons/me/settings`

**Purpose:** Update owner salon settings.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Update owner salon settings (approval mode, working hours, accepting bookings).

**Body:** `application/json`, required; [OwnerSalonSettingsRequest](#model-ownersalonsettingsrequest).

**Success 200:** `application/json`: [OwnerSalonResponse](#model-ownersalonresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`update_settings`).

### GET `/v1/salons/me/payout-account`

**Purpose:** Get owner payout account (masked).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Owner only. Works while the salon is still pending approval. The full bank account number is never returned, only its last 4 digits.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [OwnerPayoutAccountResponse](#model-ownerpayoutaccountresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`get_payout_account`).

### PUT `/v1/salons/me/payout-account`

**Purpose:** Save owner payout account.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Owner only. Merge semantics: omitted fields keep their stored value, an explicit null clears a field. The merged result needs an account holder name and either a UPI ID or both account number and IFSC, otherwise 422.

**Body:** `application/json`, required; [OwnerPayoutAccountRequest](#model-ownerpayoutaccountrequest).

**Success 200:** `application/json`: [OwnerPayoutAccountResponse](#model-ownerpayoutaccountresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`put_payout_account`).

### GET `/v1/salons/me/payout-account/history`

**Purpose:** Payout account change history.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Owner only. Newest first. Records who changed the destination and which fields changed; account numbers appear as their last 4 digits only.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `limit` | query | no | integer | minimum=1; maximum=200; default=50 |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [PayoutHistoryEntryResponse](#model-payouthistoryentryresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`get_payout_account_history`).

### GET `/v1/salons/me/setup-status`

**Purpose:** Get owner setup checklist.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Return which onboarding steps the owner has finished.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [OwnerSetupStatusResponse](#model-ownersetupstatusresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`get_setup_status`).

### GET `/v1/salons/me/qr`

**Purpose:** Get salon walk-in QR code URL or SVG.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Returns the authenticated owner's salon QR. The QR identity comes from the salon's existing database `qr_token`; this endpoint never creates or rotates the token. Repeated requests by the same owner therefore return the same QR identity.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `format` | query | no | string | pattern=^(png\|svg\|url)$; default="url" |
| `scale` | query | no | integer | minimum=4; maximum=30; default=12 |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [QrCodeUrlResponse](#model-qrcodeurlresponse); `image/svg+xml`: any.

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`get_my_qr`).

### POST `/v1/salons/me/images/upload-url`

**Purpose:** Get a signed upload URL for a salon image.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Returns a short-lived signed PUT URL and the resulting public URL for uploading a salon image through the backend image validation gateway.

**Upload flow:**
1. Call this endpoint to get `upload_url` and `public_url`.
2. `PUT <upload_url>` with the image binary and `Content-Type: <your_mime_type>` header.
3. Call `POST /v1/salons/me/images` with `{ "url": "<public_url>" }` to record it in the DB.

**Body:** `application/json`, required; [ImageUploadUrlRequest](#model-imageuploadurlrequest).

**Success 200:** `application/json`: [ImageUploadUrlResponse](#model-imageuploadurlresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`get_image_upload_url`).

### GET `/v1/salons/me/images`

**Purpose:** List owner salon images.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

List owner salon images.

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [SalonImageResponse](#model-salonimageresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`list_images`).

### POST `/v1/salons/me/images`

**Purpose:** Create owner salon image.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Create owner salon image.

**Body:** `application/json`, required; [SalonImageCreateRequest](#model-salonimagecreaterequest).

**Success 201:** `application/json`: [SalonImageResponse](#model-salonimageresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`create_image`).

### PATCH `/v1/salons/me/images/{image_id}`

**Purpose:** Update owner salon image.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Update owner salon image.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `image_id` | path | yes | string |  |

**Body:** `application/json`, required; [SalonImageUpdateRequest](#model-salonimageupdaterequest).

**Success 200:** `application/json`: [SalonImageResponse](#model-salonimageresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`update_image`).

### DELETE `/v1/salons/me/images/{image_id}`

**Purpose:** Delete owner salon image.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Soft-deletes the salon image (sets `is_active = false`) and best-effort removes the corresponding object from storage when the provider supports it. Returns 204 on success, 404 if the image is not found or already deleted.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `image_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 204:** No response body.

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`delete_image`).

### GET `/v1/salons/me/holidays`

**Purpose:** List owner salon holidays.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

List owner salon holidays.

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [HolidayResponse](#model-holidayresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`list_holidays`).

### POST `/v1/salons/me/holidays`

**Purpose:** Create owner salon holiday.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Create owner salon holiday.

**Body:** `application/json`, required; [HolidayCreateRequest](#model-holidaycreaterequest).

**Success 201:** `application/json`: [HolidayResponse](#model-holidayresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`create_holiday`).

### DELETE `/v1/salons/me/holidays/{holiday_id}`

**Purpose:** Delete owner salon holiday.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Soft-delete a holiday owned by the authenticated owner's salon.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `holiday_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 204:** No response body.

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`delete_holiday`).

### GET `/v1/salons/me/services`

**Purpose:** List Services.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

List owner salon services.

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [ServiceResponse](#model-serviceresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`list_services`).

### POST `/v1/salons/me/services`

**Purpose:** Create owner salon service.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Create owner salon service.

**Body:** `application/json`, required; [ServiceCreateRequest](#model-servicecreaterequest).

**Success 201:** `application/json`: [ServiceResponse](#model-serviceresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`create_service`).

### PATCH `/v1/salons/me/services/{service_id}`

**Purpose:** Update owner salon service.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Update owner salon service.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `service_id` | path | yes | string |  |

**Body:** `application/json`, required; [ServiceUpdateRequest](#model-serviceupdaterequest).

**Success 200:** `application/json`: [ServiceResponse](#model-serviceresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`update_service`).

### DELETE `/v1/salons/me/services/{service_id}`

**Purpose:** Deactivate owner salon service.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Soft-delete owner salon service.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `service_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [ServiceResponse](#model-serviceresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`deactivate_service`).

### GET `/v1/salons/me/staff`

**Purpose:** List Staff.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

List owner salon staff.

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [StaffResponse](#model-staffresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`list_staff`).

### POST `/v1/salons/me/staff`

**Purpose:** Create owner salon staff.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Create owner salon staff.

**Body:** `application/json`, required; [StaffCreateRequest](#model-staffcreaterequest).

**Success 201:** `application/json`: [StaffResponse](#model-staffresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`create_staff`).

### PATCH `/v1/salons/me/staff/{staff_id}`

**Purpose:** Update owner salon staff.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Update owner salon staff.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `staff_id` | path | yes | string |  |

**Body:** `application/json`, required; [StaffUpdateRequest](#model-staffupdaterequest).

**Success 200:** `application/json`: [StaffResponse](#model-staffresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`update_staff`).

### DELETE `/v1/salons/me/staff/{staff_id}`

**Purpose:** Deactivate owner salon staff.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Soft-delete owner salon staff.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `staff_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [StaffResponse](#model-staffresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`deactivate_staff`).

### POST `/v1/salons/me/staff/{staff_id}/services`

**Purpose:** Assign service to staff.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Assign a salon service to staff (with optional duration/price overrides).

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `staff_id` | path | yes | string |  |

**Body:** `application/json`, required; [StaffServiceAssignRequest](#model-staffserviceassignrequest).

**Success 200:** `application/json`: [StaffServiceResponse](#model-staffserviceresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`assign_staff_service`).

### GET `/v1/salons/me/staff/{staff_id}/services`

**Purpose:** List services assigned to staff.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Return service assignments for a staff member.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `staff_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [StaffServiceResponse](#model-staffserviceresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`list_staff_services`).

### POST `/v1/salons/me/staff/{staff_id}/photo-upload-url`

**Purpose:** Get a signed upload URL for a staff photo.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Returns a short-lived signed PUT URL and the resulting public URL for uploading a staff photo through the backend image validation gateway.

**Upload flow:**
1. Call this endpoint to get `upload_url` and `public_url`.
2. `PUT <upload_url>` with the image binary and `Content-Type: <your_mime_type>` header.
3. Call `PATCH /v1/salons/me/staff/{staff_id}` with `{ "photo_url": "<public_url>" }` to persist.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `staff_id` | path | yes | string |  |

**Body:** `application/json`, required; [ImageUploadUrlRequest](#model-imageuploadurlrequest).

**Success 200:** `application/json`: [ImageUploadUrlResponse](#model-imageuploadurlresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`get_staff_photo_upload_url`).

### GET `/v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages`

**Purpose:** List languages for a staff service assignment.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Return the languages a staff member supports for a specific service.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `staff_id` | path | yes | string |  |
| `staff_service_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [app__api__v1__schemas__platform__LanguageResponse](#model-app__api__v1__schemas__platform__languageresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`list_staff_service_languages`).

### PUT `/v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages`

**Purpose:** Set languages for a staff service assignment.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Idempotent PUT — replaces the full language list. Send an empty list to remove all languages.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `staff_id` | path | yes | string |  |
| `staff_service_id` | path | yes | string |  |

**Body:** `application/json`, required; [StaffServiceLanguagesRequest](#model-staffservicelanguagesrequest).

**Success 200:** `application/json`: array of [app__api__v1__schemas__platform__LanguageResponse](#model-app__api__v1__schemas__platform__languageresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`set_staff_service_languages`).

### GET `/v1/salons/me/blocks`

**Purpose:** List blocked slots for this salon.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Return all blocked slots (staff-scoped and salon-wide) for the owner's salon.

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [BlockedSlotResponse](#model-blockedslotresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`list_blocked_slots`).

### POST `/v1/salons/me/blocks`

**Purpose:** Create a blocked slot.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Create a staff-scoped block (set staff_id) or a salon-wide block (leave staff_id null). Slot engine honours both when computing availability.

**Body:** `application/json`, required; [BlockedSlotCreateRequest](#model-blockedslotcreaterequest).

**Success 201:** `application/json`: [BlockedSlotResponse](#model-blockedslotresponse).

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`create_blocked_slot`).

### DELETE `/v1/salons/me/blocks/{block_id}`

**Purpose:** Delete a blocked slot.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Hard-delete a blocked slot. Blocked slots have no is_active column in the schema.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `block_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 204:** No response body.

**Source:** [backend/app/api/v1/routes/owner.py](../backend/app/api/v1/routes/owner.py) (`delete_blocked_slot`).

<a id="group-payments"></a>

## Payments

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| POST | `/v1/bookings/quote` | Booking Quote | 200 |
| GET | `/v1/payments/config` | Is online payment available? | 200 |
| POST | `/v1/bookings/{booking_id}/payments/intent` | Start an online payment (customer) | 200 |
| POST | `/v1/bookings/{booking_id}/payments/confirm` | Confirm a client-side payment callback (customer) | 200 |
| POST | `/v1/bookings/{booking_id}/payments/refresh` | Refresh an online payment from the provider (customer) | 200 |
| POST | `/v1/bookings/{booking_id}/payments/cancel` | Cancel the open online payment (customer) | 200 |
| GET | `/v1/bookings/{booking_id}/payments` | Payment ledger for a booking (customer or salon) | 200 |
| POST | `/v1/bookings/{booking_id}/payments/{payment_id}/refund` | Refund an online payment (owner) | 200 |
| GET | `/v1/salons/me/earnings` | Owner earnings from the payment ledger | 200 |
| GET | `/v1/salons/me/settlement-account` | Provider settlement (payee) account state | 200 |
| POST | `/v1/salons/me/settlement-account/register` | Register the salon as a payee at the provider | 200 |

### POST `/v1/bookings/quote`

**Purpose:** Booking Quote.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

**Body:** `application/json`, required; [BookingQuoteRequest](#model-bookingquoterequest).

**Success 200:** `application/json`: [BookingQuoteResponse](#model-bookingquoteresponse).

**Source:** [backend/app/api/v1/routes/payments.py](../backend/app/api/v1/routes/payments.py) (`booking_quote`).

### GET `/v1/payments/config`

**Purpose:** Is online payment available?.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Always 200. `enabled: false` until a payment provider is configured.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [PaymentConfigResponse](#model-paymentconfigresponse).

**Source:** [backend/app/api/v1/routes/payments.py](../backend/app/api/v1/routes/payments.py) (`payment_config`).

### POST `/v1/bookings/{booking_id}/payments/intent`

**Purpose:** Start an online payment (customer).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Requires `Idempotency-Key`. The amount is derived server-side. 503 without a provider.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** `application/json`, optional; [PaymentIntentRequest](#model-paymentintentrequest) or null.

**Success 200:** `application/json`: [PaymentIntentResponse](#model-paymentintentresponse).

**Source:** [backend/app/api/v1/routes/payments.py](../backend/app/api/v1/routes/payments.py) (`create_payment_intent`).

### POST `/v1/bookings/{booking_id}/payments/confirm`

**Purpose:** Confirm a client-side payment callback (customer).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Requires `Idempotency-Key`. Providers that sign the client callback need `payment_ref` and `signature`; for the others this behaves exactly like `/refresh` and the body is ignored. Client-claimed success is never trusted.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** `application/json`, required; [PaymentConfirmRequest](#model-paymentconfirmrequest).

**Success 200:** `application/json`: [BookingPaymentsResponse](#model-bookingpaymentsresponse).

**Source:** [backend/app/api/v1/routes/payments.py](../backend/app/api/v1/routes/payments.py) (`confirm_payment`).

### POST `/v1/bookings/{booking_id}/payments/refresh`

**Purpose:** Refresh an online payment from the provider (customer).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Requires `Idempotency-Key`. The backend asks the provider for the order's status and applies it; nothing the client sends is trusted. Safe to call repeatedly.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** `application/json`, required; [PaymentRefreshRequest](#model-paymentrefreshrequest).

**Success 200:** `application/json`: [BookingPaymentsResponse](#model-bookingpaymentsresponse).

**Source:** [backend/app/api/v1/routes/payments.py](../backend/app/api/v1/routes/payments.py) (`refresh_payment`).

### POST `/v1/bookings/{booking_id}/payments/cancel`

**Purpose:** Cancel the open online payment (customer).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [BookingPaymentsResponse](#model-bookingpaymentsresponse).

**Source:** [backend/app/api/v1/routes/payments.py](../backend/app/api/v1/routes/payments.py) (`cancel_payment`).

### GET `/v1/bookings/{booking_id}/payments`

**Purpose:** Payment ledger for a booking (customer or salon).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [BookingPaymentsResponse](#model-bookingpaymentsresponse).

**Source:** [backend/app/api/v1/routes/payments.py](../backend/app/api/v1/routes/payments.py) (`list_booking_payments`).

### POST `/v1/bookings/{booking_id}/payments/{payment_id}/refund`

**Purpose:** Refund an online payment (owner).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Requires `Idempotency-Key`. Cash receipts cannot be refunded by the platform.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |
| `payment_id` | path | yes | string |  |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** `application/json`, required; [PaymentRefundRequest](#model-paymentrefundrequest).

**Success 200:** `application/json`: [BookingPaymentsResponse](#model-bookingpaymentsresponse).

**Source:** [backend/app/api/v1/routes/payments.py](../backend/app/api/v1/routes/payments.py) (`refund_payment`).

### GET `/v1/salons/me/earnings`

**Purpose:** Owner earnings from the payment ledger.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

**Body:** No declared request-body model.

**Success 200:** `application/json`: [EarningsResponse](#model-earningsresponse).

**Source:** [backend/app/api/v1/routes/payments.py](../backend/app/api/v1/routes/payments.py) (`my_earnings`).

### GET `/v1/salons/me/settlement-account`

**Purpose:** Provider settlement (payee) account state.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

**Body:** No declared request-body model.

**Success 200:** `application/json`: [SettlementAccountResponse](#model-settlementaccountresponse).

**Source:** [backend/app/api/v1/routes/payments.py](../backend/app/api/v1/routes/payments.py) (`get_settlement_account`).

### POST `/v1/salons/me/settlement-account/register`

**Purpose:** Register the salon as a payee at the provider.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Requires `Idempotency-Key`. Body carries KYC and bank/UPI details when the provider needs them; they are used once in memory and never stored, logged or returned.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** `application/json`, optional; [SettlementRegistrationRequest](#model-settlementregistrationrequest) or null.

**Success 200:** `application/json`: [SettlementAccountResponse](#model-settlementaccountresponse).

**Source:** [backend/app/api/v1/routes/payments.py](../backend/app/api/v1/routes/payments.py) (`register_settlement_account`).

<a id="group-support"></a>

## Support

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| POST | `/v1/support/tickets` | Create Ticket | 201 |
| GET | `/v1/support/tickets/{ticket_id}` | Read Ticket | 200 |
| POST | `/v1/support/tickets/{ticket_id}/reply` | Reply Ticket | 200 |
| GET | `/v1/email/events/{event_id}` | Email Event | 200 |

### POST `/v1/support/tickets`

**Purpose:** Create Ticket.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** `application/json`, required; [SupportCreateRequest](#model-supportcreaterequest).

**Success 201:** `application/json`: [SupportTicketResponse](#model-supportticketresponse).

**Source:** [backend/app/api/v1/routes/support.py](../backend/app/api/v1/routes/support.py) (`create_ticket`).

### GET `/v1/support/tickets/{ticket_id}`

**Purpose:** Read Ticket.

**Access:** Bearer; route role gate: customer, owner, super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `ticket_id` | path | yes | string (uuid) |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [SupportTicketResponse](#model-supportticketresponse).

**Source:** [backend/app/api/v1/routes/support.py](../backend/app/api/v1/routes/support.py) (`read_ticket`).

### POST `/v1/support/tickets/{ticket_id}/reply`

**Purpose:** Reply Ticket.

**Access:** Bearer; route role gate: owner, super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `ticket_id` | path | yes | string (uuid) |  |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** `application/json`, required; [SupportReplyRequest](#model-supportreplyrequest).

**Success 200:** `application/json`: [SupportTicketResponse](#model-supportticketresponse).

**Source:** [backend/app/api/v1/routes/support.py](../backend/app/api/v1/routes/support.py) (`reply_ticket`).

### GET `/v1/email/events/{event_id}`

**Purpose:** Email Event.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `event_id` | path | yes | string (uuid) |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [EmailEventResponse](#model-emaileventresponse).

**Source:** [backend/app/api/v1/routes/support.py](../backend/app/api/v1/routes/support.py) (`email_event`).

<a id="group-salons"></a>

## Salons

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/v1/salons` | List customer-visible salons | 200 |
| GET | `/v1/salons/nearby` | List nearby salons | 200 |
| GET | `/v1/salons/{salon_id}` | Get salon details | 200 |
| GET | `/v1/salons/{salon_id}/services` | List salon services | 200 |
| GET | `/v1/salons/{salon_id}/staff` | List salon staff | 200 |

### GET `/v1/salons`

**Purpose:** List customer-visible salons.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

List active completed salons — public, no auth required.

Services are NOT embedded. Call GET /salons/{salon_id}/services for service data.
Use `category` to filter by service category (e.g. ?category=Hair+Cutting) and `service` to search by
service name (e.g. ?service=haircut). `search` matches name, city or address.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `surface` | query | no | `"home" \| "search" \| "all"` or null |  |
| `shuffle_seed` | query | no | string | minLength=1; maxLength=80; default="default" |
| `search` | query | no | string or null |  |
| `city` | query | no | string or null |  |
| `service` | query | no | string or null |  |
| `lat` | query | no | number or null |  |
| `lng` | query | no | number or null |  |
| `ids` | query | no | array of string or null |  |
| `category` | query | no | string or null |  |
| `limit` | query | no | integer | minimum=1; maximum=100; default=50 |
| `offset` | query | no | integer | minimum=0; default=0 |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [SalonSummaryResponse](#model-salonsummaryresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`list_salons`).

### GET `/v1/salons/nearby`

**Purpose:** List nearby salons.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

List visible salons by display priority, then distance — public, no auth required.

Services are NOT embedded. Call GET /salons/{salon_id}/services for service data.
Use `category` to filter by service category (e.g. ?category=Hair+Cutting) and `service` to search by
service name (e.g. ?service=haircut). `search` matches name, city or address.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `lat` | query | no | number or null |  |
| `lng` | query | no | number or null |  |
| `latitude` | query | no | number or null |  |
| `longitude` | query | no | number or null |  |
| `search` | query | no | string or null |  |
| `city` | query | no | string or null |  |
| `service` | query | no | string or null |  |
| `ids` | query | no | array of string or null |  |
| `category` | query | no | string or null |  |
| `limit` | query | no | integer | minimum=1; maximum=100; default=50 |
| `offset` | query | no | integer | minimum=0; default=0 |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [SalonSummaryResponse](#model-salonsummaryresponse).

**Source:** [backend/app/api/v1/routes/customer.py](../backend/app/api/v1/routes/customer.py) (`nearby_salons`).

### GET `/v1/salons/{salon_id}`

**Purpose:** Get salon details.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Return active completed salon details — public, no auth required.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `salon_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [SalonDetailResponse](#model-salondetailresponse).

**Source:** [backend/app/api/v1/routes/admin.py](../backend/app/api/v1/routes/admin.py) (`get_salon`).

### GET `/v1/salons/{salon_id}/services`

**Purpose:** List salon services.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Return active customer-visible services for a salon — public, no auth required.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `salon_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [ServiceResponse](#model-serviceresponse).

**Source:** [backend/app/api/v1/routes/customer.py](../backend/app/api/v1/routes/customer.py) (`list_salon_services`).

### GET `/v1/salons/{salon_id}/staff`

**Purpose:** List salon staff.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Return active staff members for a customer-visible salon — public, no auth required.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `salon_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [PublicStaffResponse](#model-publicstaffresponse).

**Source:** [backend/app/api/v1/routes/customer.py](../backend/app/api/v1/routes/customer.py) (`list_salon_staff`).

<a id="group-catalog"></a>

## Catalog

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/v1/catalog/categories` | List active service categories — public | 200 |
| GET | `/v1/catalog/categories/{category_id}/subcategories` | List active subcategories for a category — public | 200 |

### GET `/v1/catalog/categories`

**Purpose:** List active service categories — public.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Returns all active service categories ordered by sort_order. Used by the owner app to populate the category picker when creating services, and by the customer app for category-based filtering.

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [CategoryResponse](#model-categoryresponse).

**Source:** [backend/app/api/v1/routes/customer.py](../backend/app/api/v1/routes/customer.py) (`list_public_categories`).

### GET `/v1/catalog/categories/{category_id}/subcategories`

**Purpose:** List active subcategories for a category — public.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Returns all active subcategories for the given category. Used by the owner app to let the barber pick a specific subcategory when creating or editing a service.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `category_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [SubcategoryResponse](#model-subcategoryresponse).

**Source:** [backend/app/api/v1/routes/customer.py](../backend/app/api/v1/routes/customer.py) (`list_public_subcategories`).

<a id="group-bookings"></a>

## Bookings

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| POST | `/v1/bookings/{booking_id}/check-in` | Check In | 200 |
| POST | `/v1/bookings/{booking_id}/no-show` | No Show | 200 |
| GET | `/v1/availability` | Get available booking slots | 200 |
| POST | `/v1/bookings` | Create booking | 201 |
| GET | `/v1/bookings` | List role-scoped bookings | 200 |
| GET | `/v1/bookings/{booking_id}` | Get booking details | 200 |
| POST | `/v1/bookings/{booking_id}/approve` | Approve booking | 200 |
| POST | `/v1/bookings/{booking_id}/reject` | Reject booking | 200 |
| POST | `/v1/bookings/{booking_id}/complete` | Complete booking | 200 |
| POST | `/v1/bookings/{booking_id}/delay` | Record a booking delay | 200 |
| POST | `/v1/bookings/{booking_id}/cancel` | Cancel booking (customer) | 200 |
| POST | `/v1/bookings/{booking_id}/cancel/barber` | Cancel booking (barber/owner) | 200 |
| POST | `/v1/bookings/{booking_id}/payment` | Record booking payment | 200 |

### POST `/v1/bookings/{booking_id}/check-in`

**Purpose:** Check In.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [BookingResponse](#model-bookingresponse).

**Source:** [backend/app/api/v1/routes/bookings.py](../backend/app/api/v1/routes/bookings.py) (`check_in`).

### POST `/v1/bookings/{booking_id}/no-show`

**Purpose:** No Show.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [BookingResponse](#model-bookingresponse).

**Source:** [backend/app/api/v1/routes/bookings.py](../backend/app/api/v1/routes/bookings.py) (`no_show`).

### GET `/v1/availability`

**Purpose:** Get available booking slots.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Delegates to the `get_available_slots` Postgres function. Never cached. Public — no auth required.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `staff_id` | query | yes | string |  |
| `date` | query | yes | string (date) |  |
| `service_ids` | query | yes | array of string | minItems=1 |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [AvailabilityResponse](#model-availabilityresponse).

**Source:** [backend/app/api/v1/routes/bookings.py](../backend/app/api/v1/routes/bookings.py) (`availability`).

### POST `/v1/bookings`

**Purpose:** Create booking.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Delegates to the `create_booking` Postgres function. Slot conflicts return 409.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** `application/json`, required; [BookingCreateRequest](#model-bookingcreaterequest).

**Success 201:** `application/json`: [BookingResponse](#model-bookingresponse).

**Source:** [backend/app/api/v1/routes/bookings.py](../backend/app/api/v1/routes/bookings.py) (`create_booking`).

### GET `/v1/bookings`

**Purpose:** List role-scoped bookings.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Owners see all bookings in their salon. Customers see only their own bookings.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `status` | query | no | `"pending" \| "confirmed" \| "checked_in" \| "no_show" \| "rejected" \| "completed" \| "cancelled"` or null |  |
| `source` | query | no | `"app" \| "manual_walkin" \| "qr_walkin"` or null |  |
| `date_from` | query | no | string (date) or null |  |
| `date_to` | query | no | string (date) or null |  |
| `limit` | query | no | integer or null |  |
| `offset` | query | no | integer | minimum=0; default=0 |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [BookingResponse](#model-bookingresponse).

**Source:** [backend/app/api/v1/routes/bookings.py](../backend/app/api/v1/routes/bookings.py) (`list_bookings`).

### GET `/v1/bookings/{booking_id}`

**Purpose:** Get booking details.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Return a booking visible to the actor.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [BookingResponse](#model-bookingresponse).

**Source:** [backend/app/api/v1/routes/bookings.py](../backend/app/api/v1/routes/bookings.py) (`get_booking`).

### POST `/v1/bookings/{booking_id}/approve`

**Purpose:** Approve booking.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Approve a pending booking. Notifies the customer via push.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [BookingResponse](#model-bookingresponse).

**Source:** [backend/app/api/v1/routes/bookings.py](../backend/app/api/v1/routes/bookings.py) (`approve_booking`).

### POST `/v1/bookings/{booking_id}/reject`

**Purpose:** Reject booking.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Reject a booking with a reason. Notifies the customer via push.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |

**Body:** `application/json`, required; [RejectBookingRequest](#model-rejectbookingrequest).

**Success 200:** `application/json`: [BookingResponse](#model-bookingresponse).

**Source:** [backend/app/api/v1/routes/bookings.py](../backend/app/api/v1/routes/bookings.py) (`reject_booking`).

### POST `/v1/bookings/{booking_id}/complete`

**Purpose:** Complete booking.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Complete a booking. Notifies the customer via push.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [BookingResponse](#model-bookingresponse).

**Source:** [backend/app/api/v1/routes/bookings.py](../backend/app/api/v1/routes/bookings.py) (`complete_booking`).

### POST `/v1/bookings/{booking_id}/delay`

**Purpose:** Record a booking delay.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Update the completion estimate and optionally notify affected customers.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |

**Body:** `application/json`, required; [DelayBookingRequest](#model-delaybookingrequest).

**Success 200:** `application/json`: [BookingResponse](#model-bookingresponse).

**Source:** [backend/app/api/v1/routes/bookings.py](../backend/app/api/v1/routes/bookings.py) (`delay_booking`).

### POST `/v1/bookings/{booking_id}/cancel`

**Purpose:** Cancel booking (customer).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Cancels a booking on behalf of the **customer**. Both `reason_code` and `reason_text` are optional — customers can cancel with a single tap and provide context later. To cancel as the **salon/barber**, use `POST /bookings/{id}/cancel/barber`.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |

**Body:** `application/json`, optional; [CancelBookingRequest](#model-cancelbookingrequest).

**Success 200:** `application/json`: [BookingResponse](#model-bookingresponse).

**Source:** [backend/app/api/v1/routes/bookings.py](../backend/app/api/v1/routes/bookings.py) (`cancel_booking`).

### POST `/v1/bookings/{booking_id}/cancel/barber`

**Purpose:** Cancel booking (barber/owner).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Cancels a booking on behalf of the **salon**. `reason_code` is **required** so the customer always receives a clear explanation. The combined reason is stored in `cancellation_reason` and included in the push notification sent to the customer.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |

**Body:** `application/json`, required; [BarberCancelBookingRequest](#model-barbercancelbookingrequest).

**Success 200:** `application/json`: [BookingResponse](#model-bookingresponse).

**Source:** [backend/app/api/v1/routes/bookings.py](../backend/app/api/v1/routes/bookings.py) (`barber_cancel_booking`).

### POST `/v1/bookings/{booking_id}/payment`

**Purpose:** Record booking payment.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Record booking payment.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** `application/json`, required; [PaymentRequest](#model-paymentrequest).

**Success 200:** `application/json`: [BookingResponse](#model-bookingresponse).

**Source:** [backend/app/api/v1/routes/bookings.py](../backend/app/api/v1/routes/bookings.py) (`record_payment`).

<a id="group-booking-actions"></a>

## Booking Actions

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| POST | `/v1/bookings/{booking_id}/payment-confirmation-requests` | Claim a Pay at Salon payment | 201 |
| POST | `/v1/bookings/{booking_id}/cancellation-requests` | Request cancellation after the immediate cutoff | 201 |
| GET | `/v1/booking-action-requests` | List salon booking action requests | 200 |
| POST | `/v1/booking-action-requests/{request_id}/respond` | Resolve a booking action request | 200 |
| POST | `/v1/salons/me/closures/preview` | Preview bookings affected by a salon closure | 200 |
| POST | `/v1/salons/me/closures` | Apply a confirmed salon closure | 201 |

### POST `/v1/bookings/{booking_id}/payment-confirmation-requests`

**Purpose:** Claim a Pay at Salon payment.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Keep the booking unpaid while asking the salon to verify payment.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |

**Body:** `application/json`, optional; [BookingActionCreateRequest](#model-bookingactioncreaterequest).

**Success 201:** `application/json`: [BookingActionRequestResponse](#model-bookingactionrequestresponse).

**Source:** [backend/app/api/v1/routes/booking_actions.py](../backend/app/api/v1/routes/booking_actions.py) (`create_payment_confirmation_request`).

### POST `/v1/bookings/{booking_id}/cancellation-requests`

**Purpose:** Request cancellation after the immediate cutoff.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Create a pending request without releasing the booking slot.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `booking_id` | path | yes | string |  |

**Body:** `application/json`, optional; [BookingActionCreateRequest](#model-bookingactioncreaterequest).

**Success 201:** `application/json`: [BookingActionRequestResponse](#model-bookingactionrequestresponse).

**Source:** [backend/app/api/v1/routes/booking_actions.py](../backend/app/api/v1/routes/booking_actions.py) (`create_cancellation_request`).

### GET `/v1/booking-action-requests`

**Purpose:** List salon booking action requests.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Return only requests belonging to the actor's salon workspace.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `status` | query | no | `"pending" \| "resolved"` or null |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [BookingActionRequestResponse](#model-bookingactionrequestresponse).

**Source:** [backend/app/api/v1/routes/booking_actions.py](../backend/app/api/v1/routes/booking_actions.py) (`list_booking_action_requests`).

### POST `/v1/booking-action-requests/{request_id}/respond`

**Purpose:** Resolve a booking action request.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Apply an owner/staff decision with row-lock and duplicate protection.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `request_id` | path | yes | string |  |

**Body:** `application/json`, required; [BookingActionRespondRequest](#model-bookingactionrespondrequest).

**Success 200:** `application/json`: [BookingActionRequestResponse](#model-bookingactionrequestresponse).

**Source:** [backend/app/api/v1/routes/booking_actions.py](../backend/app/api/v1/routes/booking_actions.py) (`respond_booking_action_request`).

### POST `/v1/salons/me/closures/preview`

**Purpose:** Preview bookings affected by a salon closure.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Return the exact active bookings overlapped by a holiday or leave.

**Body:** `application/json`, required; [ClosurePreviewRequest](#model-closurepreviewrequest).

**Success 200:** `application/json`: [ClosurePreviewResponse](#model-closurepreviewresponse).

**Source:** [backend/app/api/v1/routes/booking_actions.py](../backend/app/api/v1/routes/booking_actions.py) (`preview_closure`).

### POST `/v1/salons/me/closures`

**Purpose:** Apply a confirmed salon closure.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Block the interval and cancel/notify exactly the confirmed impact set.

**Body:** `application/json`, required; [ClosureApplyRequest](#model-closureapplyrequest).

**Success 201:** `application/json`: [ClosureApplyResponse](#model-closureapplyresponse).

**Source:** [backend/app/api/v1/routes/booking_actions.py](../backend/app/api/v1/routes/booking_actions.py) (`apply_closure`).

<a id="group-notifications"></a>

## Notifications

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/v1/notifications` | List notifications | 200 |
| POST | `/v1/notifications/{notification_id}/read` | Mark notification read | 200 |
| POST | `/v1/notifications/read-all` | Mark all notifications read | 200 |
| POST | `/v1/devices` | Register device token | 200 |
| DELETE | `/v1/devices/{token}` | Deactivate device token | 204 |

### GET `/v1/notifications`

**Purpose:** List notifications.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

List notifications owned by the actor.

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [NotificationResponse](#model-notificationresponse).

**Source:** [backend/app/api/v1/routes/notifications.py](../backend/app/api/v1/routes/notifications.py) (`list_notifications`).

### POST `/v1/notifications/{notification_id}/read`

**Purpose:** Mark notification read.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Mark one notification as read.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `notification_id` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [NotificationResponse](#model-notificationresponse).

**Source:** [backend/app/api/v1/routes/notifications.py](../backend/app/api/v1/routes/notifications.py) (`mark_notification_read`).

### POST `/v1/notifications/read-all`

**Purpose:** Mark all notifications read.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Mark every unread notification owned by the actor.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [MarkAllNotificationsReadResponse](#model-markallnotificationsreadresponse).

**Source:** [backend/app/api/v1/routes/notifications.py](../backend/app/api/v1/routes/notifications.py) (`mark_all_notifications_read`).

### POST `/v1/devices`

**Purpose:** Register device token.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Register or reactivate one device token for the authenticated user.

**Body:** `application/json`, required; [DeviceRegisterRequest](#model-deviceregisterrequest).

**Success 200:** `application/json`: [DeviceRegisterResponse](#model-deviceregisterresponse).

**Source:** [backend/app/api/v1/routes/notifications.py](../backend/app/api/v1/routes/notifications.py) (`register_device`).

### DELETE `/v1/devices/{token}`

**Purpose:** Deactivate device token.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Deactivate this actor's device token.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `token` | path | yes | string |  |

**Body:** No declared request-body model.

**Success 204:** No response body.

**Source:** [backend/app/api/v1/routes/notifications.py](../backend/app/api/v1/routes/notifications.py) (`deactivate_device`).

<a id="group-walkin"></a>

## Walkin

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/v1/walkin/{qr_token}` | Resolve QR token — public | 200 |
| GET | `/v1/walkin/{qr_token}/qr` | Get salon walk-in QR code image — public | 200 |
| POST | `/v1/walkin/{qr_token}/verify-phone` | Send or verify phone OTP | 200 |
| POST | `/v1/walkin/{qr_token}/bookings` | Create walk-in booking via QR | 201 |

### GET `/v1/walkin/{qr_token}`

**Purpose:** Resolve QR token — public.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Returns salon info, services, and staff for the scanned QR code. No authentication required. Rate-limited by IP.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `qr_token` | path | yes | string |  |
| `fresh` | query | no | boolean | default=false |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [WalkInSalonResponse](#model-walkinsalonresponse).

**Source:** [backend/app/api/v1/routes/walkin.py](../backend/app/api/v1/routes/walkin.py) (`resolve_qr`).

### GET `/v1/walkin/{qr_token}/qr`

**Purpose:** Get salon walk-in QR code image — public.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Returns the QR code for this salon as a PNG (default) or SVG. No authentication required. The QR encodes: <WALKIN_BASE_URL>/<qr_token>. Embed directly in the web app or download for printing.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `qr_token` | path | yes | string |  |
| `format` | query | no | string | pattern=^(png\|svg)$; default="png" |
| `scale` | query | no | integer | minimum=4; maximum=30; default=10 |

**Body:** No declared request-body model.

**Success 200:** `application/json`: any; `image/png`: string (binary); `image/svg+xml`: string.

**Source:** [backend/app/api/v1/routes/walkin.py](../backend/app/api/v1/routes/walkin.py) (`get_qr_image`).

### POST `/v1/walkin/{qr_token}/verify-phone`

**Purpose:** Send or verify phone OTP.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Step 1: POST with phone only → Supabase sends OTP. Step 2: POST with phone + otp → returns JWT on success.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `qr_token` | path | yes | string |  |

**Body:** `application/json`, required; [WalkInVerifyPhoneRequest](#model-walkinverifyphonerequest).

**Success 200:** `application/json`: [WalkInVerifyPhoneResponse](#model-walkinverifyphoneresponse).

**Source:** [backend/app/api/v1/routes/walkin.py](../backend/app/api/v1/routes/walkin.py) (`verify_phone`).

### POST `/v1/walkin/{qr_token}/bookings`

**Purpose:** Create walk-in booking via QR.

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Creates a booking with source='qr_walkin'. Requires the JWT obtained from verify-phone.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `qr_token` | path | yes | string |  |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** `application/json`, required; [BookingCreateRequest](#model-bookingcreaterequest).

**Success 201:** `application/json`: [BookingResponse](#model-bookingresponse).

**Source:** [backend/app/api/v1/routes/walkin.py](../backend/app/api/v1/routes/walkin.py) (`create_walkin_booking`).

<a id="group-subscriptions"></a>

## Subscriptions

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/v1/admin/subscription-plans` | List subscription plans (admin) | 200 |
| POST | `/v1/admin/subscription-plans` | Create subscription plan | 201 |
| PATCH | `/v1/admin/subscription-plans/{plan_id}` | Update subscription plan | 200 |
| POST | `/v1/admin/subscription-plans/{plan_id}/deactivate` | Deactivate subscription plan | 200 |
| GET | `/v1/admin/salons/{salon_id}/subscription` | View a salon's subscription (admin) | 200 |
| POST | `/v1/admin/salons/{salon_id}/subscription/test` | Create a test subscription (admin, manual activation only) | 201 |
| POST | `/v1/admin/subscriptions/{subscription_id}/cancel` | Cancel subscription (admin) | 200 |
| POST | `/v1/admin/subscriptions/{subscription_id}/suspend` | Suspend subscription (admin) | 200 |
| GET | `/v1/admin/subscription-events` | List subscription events (admin) | 200 |

### GET `/v1/admin/subscription-plans`

**Purpose:** List subscription plans (admin).

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `include_inactive` | query | no | boolean | default=false |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [PlanResponse](#model-planresponse).

**Source:** [backend/app/api/v1/routes/subscriptions.py](../backend/app/api/v1/routes/subscriptions.py) (`list_plans`).

### POST `/v1/admin/subscription-plans`

**Purpose:** Create subscription plan.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

**Body:** `application/json`, required; [PlanCreateRequest](#model-plancreaterequest).

**Success 201:** `application/json`: [PlanResponse](#model-planresponse).

**Source:** [backend/app/api/v1/routes/subscriptions.py](../backend/app/api/v1/routes/subscriptions.py) (`create_plan`).

### PATCH `/v1/admin/subscription-plans/{plan_id}`

**Purpose:** Update subscription plan.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `plan_id` | path | yes | string (uuid) |  |

**Body:** `application/json`, required; [PlanUpdateRequest](#model-planupdaterequest).

**Success 200:** `application/json`: [PlanResponse](#model-planresponse).

**Source:** [backend/app/api/v1/routes/subscriptions.py](../backend/app/api/v1/routes/subscriptions.py) (`update_plan`).

### POST `/v1/admin/subscription-plans/{plan_id}/deactivate`

**Purpose:** Deactivate subscription plan.

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `plan_id` | path | yes | string (uuid) |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [PlanResponse](#model-planresponse).

**Source:** [backend/app/api/v1/routes/subscriptions.py](../backend/app/api/v1/routes/subscriptions.py) (`deactivate_plan`).

### GET `/v1/admin/salons/{salon_id}/subscription`

**Purpose:** View a salon's subscription (admin).

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `salon_id` | path | yes | string (uuid) |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [SubscriptionResponse](#model-subscriptionresponse) or null.

**Source:** [backend/app/api/v1/routes/subscriptions.py](../backend/app/api/v1/routes/subscriptions.py) (`get_salon_subscription`).

### POST `/v1/admin/salons/{salon_id}/subscription/test`

**Purpose:** Create a test subscription (admin, manual activation only).

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

Creates a subscription record for testing. This is NOT payment activation — no external provider is called. Label: manual/test activation.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `salon_id` | path | yes | string (uuid) |  |

**Body:** `application/json`, required; [ManualSubscriptionCreateRequest](#model-manualsubscriptioncreaterequest).

**Success 201:** `application/json`: [SubscriptionResponse](#model-subscriptionresponse).

**Source:** [backend/app/api/v1/routes/subscriptions.py](../backend/app/api/v1/routes/subscriptions.py) (`create_test_subscription`).

### POST `/v1/admin/subscriptions/{subscription_id}/cancel`

**Purpose:** Cancel subscription (admin).

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `subscription_id` | path | yes | string (uuid) |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [SubscriptionResponse](#model-subscriptionresponse).

**Source:** [backend/app/api/v1/routes/subscriptions.py](../backend/app/api/v1/routes/subscriptions.py) (`cancel_subscription`).

### POST `/v1/admin/subscriptions/{subscription_id}/suspend`

**Purpose:** Suspend subscription (admin).

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `subscription_id` | path | yes | string (uuid) |  |

**Body:** No declared request-body model.

**Success 200:** `application/json`: [SubscriptionResponse](#model-subscriptionresponse).

**Source:** [backend/app/api/v1/routes/subscriptions.py](../backend/app/api/v1/routes/subscriptions.py) (`suspend_subscription`).

### GET `/v1/admin/subscription-events`

**Purpose:** List subscription events (admin).

**Access:** Bearer; route role gate: super_admin; application scope checks also apply.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `subscription_id` | query | no | string or null |  |
| `limit` | query | no | integer | minimum=1; maximum=200; default=50 |
| `offset` | query | no | integer | minimum=0; default=0 |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [SubscriptionEventResponse](#model-subscriptioneventresponse).

**Source:** [backend/app/api/v1/routes/subscriptions.py](../backend/app/api/v1/routes/subscriptions.py) (`list_events`).

<a id="group-subscription-billing"></a>

## Subscription Billing

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/v1/subscriptions/config` | Is subscription billing available? | 200 |
| GET | `/v1/subscription-plans` | Purchasable subscription plans (owner) | 200 |
| GET | `/v1/salons/me/subscription` | My salon subscription and entitlement (owner) | 200 |
| GET | `/v1/salons/me/access-state` | Access state implied by the subscription alone (owner) | 200 |
| POST | `/v1/salons/me/subscription/checkout` | Start a subscription payment (owner, website) | 200 |
| POST | `/v1/salons/me/subscription/verify` | Verify a subscription payment with the provider (owner) | 200 |
| POST | `/v1/salons/me/subscription/cancel` | Cancel future renewal (owner) | 200 |
| GET | `/v1/salons/me/subscription/payments` | Subscription billing history (owner) | 200 |

### GET `/v1/subscriptions/config`

**Purpose:** Is subscription billing available?.

**Access:** Public (no bearer); provider/rate-limit checks may apply.

Always 200, no auth. `native_purchase_allowed` is always false (store policy).

**Body:** No declared request-body model.

**Success 200:** `application/json`: [SubscriptionConfigResponse](#model-subscriptionconfigresponse).

**Source:** [backend/app/api/v1/routes/subscription_billing.py](../backend/app/api/v1/routes/subscription_billing.py) (`subscription_config`).

### GET `/v1/subscription-plans`

**Purpose:** Purchasable subscription plans (owner).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [PurchasablePlanResponse](#model-purchasableplanresponse).

**Source:** [backend/app/api/v1/routes/subscription_billing.py](../backend/app/api/v1/routes/subscription_billing.py) (`list_purchasable_plans`).

### GET `/v1/salons/me/subscription`

**Purpose:** My salon subscription and entitlement (owner).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

**Body:** No declared request-body model.

**Success 200:** `application/json`: [SubscriptionStateResponse](#model-subscriptionstateresponse).

**Source:** [backend/app/api/v1/routes/subscription_billing.py](../backend/app/api/v1/routes/subscription_billing.py) (`my_subscription`).

### GET `/v1/salons/me/access-state`

**Purpose:** Access state implied by the subscription alone (owner).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Thin read of the subscription-derived state; trial and soft-lock states are extended later.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [AccessStateResponse](#model-accessstateresponse).

**Source:** [backend/app/api/v1/routes/subscription_billing.py](../backend/app/api/v1/routes/subscription_billing.py) (`my_access_state`).

### POST `/v1/salons/me/subscription/checkout`

**Purpose:** Start a subscription payment (owner, website).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Requires `Idempotency-Key`. The price is the plan price at this moment, snapshotted server-side; nothing about money is accepted from the client. 503 when billing is off.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `Idempotency-Key` | header | no | string or null |  |

**Body:** `application/json`, required; [CheckoutRequest](#model-checkoutrequest).

**Success 200:** `application/json`: [CheckoutResponse](#model-checkoutresponse).

**Source:** [backend/app/api/v1/routes/subscription_billing.py](../backend/app/api/v1/routes/subscription_billing.py) (`checkout`).

### POST `/v1/salons/me/subscription/verify`

**Purpose:** Verify a subscription payment with the provider (owner).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

The backend asks the provider; a client signature, if sent, only selects which payment to fetch. Safe to call repeatedly: activation happens at most once.

**Body:** `application/json`, required; [VerifyRequest](#model-verifyrequest).

**Success 200:** `application/json`: [SubscriptionStateResponse](#model-subscriptionstateresponse).

**Source:** [backend/app/api/v1/routes/subscription_billing.py](../backend/app/api/v1/routes/subscription_billing.py) (`verify`).

### POST `/v1/salons/me/subscription/cancel`

**Purpose:** Cancel future renewal (owner).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

Idempotent. Paid-through access remains until the period ends.

**Body:** No declared request-body model.

**Success 200:** `application/json`: [SubscriptionStateResponse](#model-subscriptionstateresponse).

**Source:** [backend/app/api/v1/routes/subscription_billing.py](../backend/app/api/v1/routes/subscription_billing.py) (`cancel`).

### GET `/v1/salons/me/subscription/payments`

**Purpose:** Subscription billing history (owner).

**Access:** Bearer; role/resource permissions enforced in application use cases (not unrestricted).

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `limit` | query | no | integer | minimum=1; maximum=200; default=50 |
| `offset` | query | no | integer | minimum=0; default=0 |

**Body:** No declared request-body model.

**Success 200:** `application/json`: array of [BillingPaymentResponse](#model-billingpaymentresponse).

**Source:** [backend/app/api/v1/routes/subscription_billing.py](../backend/app/api/v1/routes/subscription_billing.py) (`payments`).

<a id="group-webhooks"></a>

## Webhooks

| Method | Full path | Purpose | Success |
| --- | --- | --- | --- |
| POST | `/v1/webhooks/{provider}` | Payment provider webhook | 200 |

### POST `/v1/webhooks/{provider}`

**Purpose:** Payment provider webhook.

**Access:** Provider signature over raw body; not a frontend call.

No auth: the provider signature over the raw body is the credential. Bad signature -> 400 and nothing is stored. Unknown events are acknowledged 200.

| Parameter | Location | Required | Type | Declared constraints/default |
| --- | --- | --- | --- | --- |
| `provider` | path | yes | string |  |

**Body:** Raw provider bytes with provider-specific signature headers; not inferred from a Pydantic body model.

**Success 200:** `application/json`: [WebhookAckResponse](#model-webhookackresponse).

**Source:** [backend/app/api/v1/routes/webhooks.py](../backend/app/api/v1/routes/webhooks.py) (`payment_webhook`).

## Data models

Shared models are defined once below. A missing property in required means the schema permits omission, not that all business workflows can omit it. Defaults shown are schema defaults, not values read from a deployed service.

<a id="model-accessstateresponse"></a>

### AccessStateResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `accepts_new_bookings` | yes | boolean |  |  |
| `subscription_wall` | yes | boolean |  |  |
| `wall_messages` | no | array of string |  |  |
| `trial_started_at` | no | string (date-time) or null |  |  |
| `trial_ends_at` | no | string (date-time) or null |  |  |
| `trial_booking_limit` | no | integer or null |  |  |
| `trial_bookings_counted` | no | integer or null |  |  |
| `access_state` | yes | `"not_subscribed" \| "subscribed" \| "subscribed_growth" \| "subscribed_premium"` |  |  |
| `entitlement_active` | yes | boolean |  |  |
| `entitlement_state` | yes | string |  |  |
| `features` | no | object |  |  |
| `paid_through` | no | string (date-time) or null |  |  |
| `grace_ends_at` | no | string (date-time) or null |  |  |
| `source` | no | `"subscription"` | default="subscription" |  |

<a id="model-accountdeletionacceptedresponse"></a>

### AccountDeletionAcceptedResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `request_id` | yes | string (uuid) |  |  |
| `status` | yes | `"pending" \| "processing" \| "completed" \| "failed"` |  |  |
| `status_token` | yes | string |  | Send as the X-Status-Token header to GET /v1/account/deletion/{request_id}. The JWT stops working as soon as deletion is confirmed. |

<a id="model-accountdeletionstatusresponse"></a>

### AccountDeletionStatusResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `request_id` | yes | string (uuid) |  |  |
| `status` | yes | `"pending" \| "processing" \| "completed" \| "failed"` |  |  |
| `stage` | yes | `"queued" \| "refunding" \| "waiting_for_refunds" \| "erasing" \| "completed"` |  | queued -> (owners) refunding -> waiting_for_refunds -> erasing -> completed. While refunds settle, status stays pending and stage is waiting_for_refunds. |
| `requested_at` | yes | string (date-time) |  |  |
| `completed_at` | no | string (date-time) or null |  |  |

<a id="model-adminaccountdeletionresponse"></a>

### AdminAccountDeletionResponse

Ledger row: no name, email, phone or user id. ``salon_name``/``salon_city`` hold the
live business snapshot only until completion, then the anonymised shell values.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string (uuid) |  |  |
| `role` | yes | `"customer" \| "owner"` |  |  |
| `salon_id` | no | string (uuid) or null |  |  |
| `salon_name` | no | string or null |  |  |
| `salon_city` | no | string or null |  |  |
| `status` | yes | `"pending" \| "processing" \| "completed" \| "failed"` |  |  |
| `requested_at` | yes | string (date-time) |  |  |
| `completed_at` | no | string (date-time) or null |  |  |
| `attempts` | no | integer | default=0 |  |
| `last_error_code` | no | string or null |  | Exception class of the last failed step, or refunds_pending while waiting for refunds. Null when completed. |
| `next_attempt_at` | no | string (date-time) or null |  |  |
| `updated_at` | no | string (date-time) or null |  |  |

<a id="model-admincreatesalonrequest"></a>

### AdminCreateSalonRequest

Request to create a salon owner + salon.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `email` | yes | string (email) |  |  |
| `password` | yes | string | minLength=8 |  |
| `full_name` | yes | string | minLength=1 |  |
| `salon_name` | yes | string | minLength=1 |  |
| `timezone` | no | string | default="Asia/Kolkata" |  |

<a id="model-admindeactivatesalonresponse"></a>

### AdminDeactivateSalonResponse

Response after deactivating a salon.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `owner_id` | yes | string |  |  |

<a id="model-adminrejectsalonrequest"></a>

### AdminRejectSalonRequest

Body for rejecting a salon.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `rejection_reason` | yes | string | minLength=1 | Reason shown to the owner |

<a id="model-adminsalononboardingresponse"></a>

### AdminSalonOnboardingResponse

Full salon submission, accessible only to super admins.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `owner_id` | yes | string |  |  |
| `owner_email` | no | string or null |  |  |
| `owner_name` | no | string or null |  |  |
| `owner_phone` | no | string or null |  |  |
| `owner_avatar_url` | no | string or null |  |  |
| `owner_phone_verified` | no | boolean or null |  |  |
| `owner_is_active` | no | boolean or null |  |  |
| `name` | yes | string |  |  |
| `category` | no | string or null |  |  |
| `address` | no | string or null |  |  |
| `city` | no | string or null |  |  |
| `lat` | no | number or null |  |  |
| `lng` | no | number or null |  |  |
| `working_hours` | no | object |  |  |
| `slot_interval_minutes` | no | integer or null |  |  |
| `qr_token` | no | string or null |  |  |
| `timezone` | yes | string |  |  |
| `approval_mode` | yes | string |  |  |
| `profile_completed` | yes | boolean |  |  |
| `is_active` | yes | boolean |  |  |
| `approval_status` | yes | `"pending" \| "approved" \| "rejected"` |  |  |
| `approved_at` | no | string (date-time) or null |  |  |
| `approved_by` | no | string or null |  |  |
| `rejection_reason` | no | string or null |  |  |
| `display_priority` | no | integer | default=0 |  |
| `discovery_visibility` | no | `"listed" \| "search_only" \| "hidden"` | default="listed" |  |
| `home_placement` | no | `"top" \| "normal" \| "below" \| "random"` | default="normal" |  |
| `created_at` | yes | string (date-time) |  |  |
| `updated_at` | yes | string (date-time) |  |  |
| `updated_by` | no | string or null |  |  |
| `images` | no | array of [SalonImageResponse](#model-salonimageresponse) | maxItems=3 | One separate cover (is_main=true) and at most two distinct gallery slides. |
| `services` | no | array of [ServiceResponse](#model-serviceresponse) |  |  |
| `staff` | no | array of [StaffResponse](#model-staffresponse) |  |  |

<a id="model-adminsalonresponse"></a>

### AdminSalonResponse

Admin view of a salon (includes owner info).

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `owner_id` | yes | string |  |  |
| `owner_email` | no | string or null |  |  |
| `owner_name` | no | string or null |  |  |
| `owner_phone` | no | string or null |  |  |
| `owner_avatar_url` | no | string or null |  |  |
| `owner_phone_verified` | no | boolean or null |  |  |
| `owner_is_active` | no | boolean or null |  |  |
| `name` | yes | string |  |  |
| `category` | no | string or null |  |  |
| `address` | no | string or null |  |  |
| `city` | no | string or null |  |  |
| `lat` | no | number or null |  |  |
| `lng` | no | number or null |  |  |
| `working_hours` | no | object |  |  |
| `slot_interval_minutes` | no | integer or null |  |  |
| `qr_token` | no | string or null |  |  |
| `timezone` | yes | string |  |  |
| `approval_mode` | yes | string |  |  |
| `profile_completed` | yes | boolean |  |  |
| `is_active` | yes | boolean |  |  |
| `approval_status` | yes | `"pending" \| "approved" \| "rejected"` |  |  |
| `approved_at` | no | string (date-time) or null |  |  |
| `approved_by` | no | string or null |  |  |
| `rejection_reason` | no | string or null |  |  |
| `display_priority` | no | integer | default=0 |  |
| `discovery_visibility` | no | `"listed" \| "search_only" \| "hidden"` | default="listed" |  |
| `home_placement` | no | `"top" \| "normal" \| "below" \| "random"` | default="normal" |  |
| `created_at` | yes | string (date-time) |  |  |
| `updated_at` | yes | string (date-time) |  |  |
| `updated_by` | no | string or null |  |  |

<a id="model-adminupdatesalonrequest"></a>

### AdminUpdateSalonRequest

Admin-editable salon fields.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `name` | no | string or null |  |  |
| `timezone` | no | string or null |  |  |
| `display_priority` | no | integer or null |  |  |
| `discovery_visibility` | no | `"listed" \| "search_only" \| "hidden"` or null |  |  |
| `home_placement` | no | `"top" \| "normal" \| "below" \| "random"` or null |  |  |

Unknown fields are forbidden by this model.

<a id="model-availabilityresponse"></a>

### AvailabilityResponse

Available slot response.

Frontend ``TimeSlotPicker`` expects:
  - ``id``         — stable key for the slot (formatted start time, e.g. "09:00 AM")
  - ``time``       — human-readable label shown in the UI (same value as ``id``)
  - ``barberName`` — optional barber context displayed beside the time chip

We also keep ``slot_start`` / ``slot_end`` for any consumer that needs the
raw datetimes.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `slot_start` | yes | string (date-time) |  |  |
| `slot_end` | yes | string (date-time) |  |  |
| `id` | yes | string |  |  |
| `time` | yes | string |  |  |
| `barberName` | no | string or null |  |  |

<a id="model-avatarresponse"></a>

### AvatarResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `avatar_url` | yes | string |  |  |
| `family_id` | no | string or null |  |  |
| `policy_version` | no | string or null |  |  |
| `variants` | no | map of [ImageVariantResponse](#model-imagevariantresponse) |  |  |

<a id="model-barbercancelbookingrequest"></a>

### BarberCancelBookingRequest

Request body for the barber/owner cancel-booking endpoint.

``reason_code`` is **required** when the salon cancels so the customer
always receives a clear, localised explanation.  ``reason_text`` is
optional additional context.

The combined human-readable string (e.g. ``"Barber unavailable — staffing
issue this week"``) is stored in ``bookings.cancellation_reason`` and sent
to the customer as a push notification body.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `reason_code` | yes | `"barber_unavailable" \| "salon_emergency" \| "overbooking" \| "customer_no_show" \| "equipment_issue" \| "other"` |  | Structured reason chip shown to the customer. |
| `reason_text` | no | string or null |  | Optional free-text note with additional context (shown to the customer). |

<a id="model-billingpaymentresponse"></a>

### BillingPaymentResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `plan_code` | yes | string |  |  |
| `status` | yes | `"created" \| "authorized" \| "paid" \| "failed" \| "expired" \| "refunded" \| "partially_refunded"` |  |  |
| `amount` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*(?:\d{0,8}\|(?=[\d.]{1,11}0*$)\d{0,8}\.\d{0,2}0*$) |  |
| `currency` | yes | string |  |  |
| `billing_interval` | yes | string |  |  |
| `tax_amount` | no | string or null |  |  |
| `tax_inclusive` | no | boolean or null |  |  |
| `refunded_amount` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*(?:\d{0,8}\|(?=[\d.]{1,11}0*$)\d{0,8}\.\d{0,2}0*$) |  |
| `order_ref` | no | string or null |  |  |
| `receipt` | yes | string |  |  |
| `period_start` | no | string (date-time) or null |  |  |
| `period_end` | no | string (date-time) or null |  |  |
| `expires_at` | yes | string (date-time) |  |  |
| `paid_at` | no | string (date-time) or null |  |  |
| `applied_at` | no | string (date-time) or null |  |  |
| `payment_verified` | yes | boolean |  |  |
| `entitlement_applied` | yes | boolean |  |  |
| `created_at` | yes | string (date-time) |  |  |

<a id="model-blockedslotcreaterequest"></a>

### BlockedSlotCreateRequest

Create a blocked slot (staff-scoped or salon-wide).

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `staff_id` | no | string or null |  | Staff member to block. Leave null for a salon-wide block. |
| `start_datetime` | yes | string (date-time) |  |  |
| `end_datetime` | yes | string (date-time) |  |  |
| `block_type` | no | `"leave" \| "break" \| "lunch" \| "training" \| "holiday" \| "other"` | default="other" |  |
| `reason` | no | string or null |  |  |
| `is_full_day` | no | boolean | default=false |  |
| `is_recurring` | no | boolean | default=false |  |
| `recurrence_rule` | no | string or null |  | iCal RRULE string. Stored but not yet interpreted. |
| `recurrence_end` | no | string (date) or null |  |  |

<a id="model-blockedslotresponse"></a>

### BlockedSlotResponse

Blocked slot response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `staff_id` | no | string or null |  |  |
| `salon_id` | no | string or null |  |  |
| `start_datetime` | yes | string (date-time) |  |  |
| `end_datetime` | yes | string (date-time) |  |  |
| `block_type` | yes | string |  |  |
| `reason` | no | string or null |  |  |
| `is_full_day` | yes | boolean |  |  |
| `is_recurring` | yes | boolean |  |  |
| `recurrence_rule` | no | string or null |  |  |
| `recurrence_end` | no | string (date) or null |  |  |
| `created_at` | yes | string (date-time) |  |  |
| `updated_at` | yes | string (date-time) |  |  |

<a id="model-bookingactioncreaterequest"></a>

### BookingActionCreateRequest

Optional customer context attached to an action request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `reason` | no | string or null |  |  |

<a id="model-bookingactionrequestresponse"></a>

### BookingActionRequestResponse

Persisted customer request shown by both apps.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `booking_id` | yes | string |  |  |
| `kind` | yes | `"payment_confirmation" \| "cancellation"` |  |  |
| `status` | yes | `"pending" \| "resolved"` |  |  |
| `customer_name` | yes | string |  |  |
| `service_names` | no | array of string |  |  |
| `start_datetime` | yes | string (date-time) |  |  |
| `total_price` | yes | number | minimum=0.0 |  |
| `reason` | no | string or null |  |  |
| `decision` | no | string or null |  |  |
| `decision_reason` | no | string or null |  |  |
| `resolved_at` | no | string (date-time) or null |  |  |
| `created_at` | yes | string (date-time) |  |  |
| `booking` | no | [BookingResponse](#model-bookingresponse) or null |  |  |

<a id="model-bookingactionrespondrequest"></a>

### BookingActionRespondRequest

Owner/staff decision for one pending request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `decision` | yes | `"received" \| "not_received" \| "approve" \| "decline"` |  |  |
| `reason` | no | string or null |  |  |
| `payment_method` | no | `"cash" \| "online"` | default="cash" |  |

<a id="model-bookingcreaterequest"></a>

### BookingCreateRequest

Create booking request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `salon_id` | yes | string |  |  |
| `staff_id` | yes | string |  |  |
| `service_ids` | yes | array of string | minItems=1 |  |
| `start_datetime` | yes | string (date-time) |  |  |
| `customer_name` | yes | string |  |  |
| `customer_phone` | no | string or null |  |  |
| `source` | no | `"app" \| "manual_walkin" \| "qr_walkin"` | default="app" |  |
| `notes` | no | string or null |  |  |
| `payment_preference` | no | `"pay_at_salon" \| "pay_advance" \| "pay_full"` or null |  |  |

<a id="model-bookinglineresponse"></a>

### BookingLineResponse

Booking service line response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `service_id` | yes | string |  |  |
| `service_name` | yes | string |  |  |
| `duration_minutes` | yes | integer |  |  |
| `price` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |

<a id="model-bookingpaymentresponse"></a>

### BookingPaymentResponse

One ledger row.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `booking_id` | yes | string |  |  |
| `channel` | yes | string |  |  |
| `purpose` | yes | string |  |  |
| `settlement_model` | yes | string |  |  |
| `provider` | no | string or null |  |  |
| `method` | no | string or null |  |  |
| `instrument` | no | string or null |  |  |
| `amount` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `currency` | yes | string |  |  |
| `status` | yes | string |  |  |
| `overcollected_amount` | no | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$; default="0.00" |  |
| `failure_code` | no | string or null |  |  |
| `expires_at` | no | string (date-time) or null |  |  |
| `captured_at` | no | string (date-time) or null |  |  |
| `created_at` | yes | string (date-time) |  |  |
| `payment_mode` | yes | `"PAY_ONLINE" \| "PAY_AT_SALON"` |  |  |
| `payment_status` | yes | string |  |  |
| `collection_method` | no | `"CASH" \| "UPI_DIRECT"` or null |  |  |
| `service_amount` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `online_processing_charge` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `total_payable` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `cashfree_order_id` | no | string or null |  |  |
| `cashfree_payment_session_id` | no | string or null |  |  |
| `provider_payment_reference` | no | string or null |  |  |
| `collected_by_owner` | no | boolean | default=false |  |
| `collected_at` | no | string (date-time) or null |  |  |

<a id="model-bookingpaymentsresponse"></a>

### BookingPaymentsResponse

Everything money-related about one booking.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `booking_id` | yes | string |  |  |
| `currency` | yes | string |  |  |
| `total_price` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `deposit_amount` | no | string or null |  |  |
| `paid_amount` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `refunded_amount` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `payment_status` | yes | string |  |  |
| `payment_state` | yes | string |  |  |
| `payments` | yes | array of [BookingPaymentResponse](#model-bookingpaymentresponse) |  |  |
| `refunds` | yes | array of [RefundResponse](#model-refundresponse) |  |  |

<a id="model-bookingquoterequest"></a>

### BookingQuoteRequest

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `salon_id` | yes | string (uuid) |  |  |
| `staff_id` | yes | string (uuid) |  |  |
| `service_ids` | yes | array of string (uuid) | minItems=1; maxItems=30 |  |
| `start_datetime` | yes | string (date-time) |  |  |
| `payment_mode` | yes | `"PAY_ONLINE" \| "PAY_AT_SALON"` |  |  |

Unknown fields are forbidden by this model.

<a id="model-bookingquoteresponse"></a>

### BookingQuoteResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `payment_mode` | yes | `"PAY_ONLINE" \| "PAY_AT_SALON"` |  |  |
| `currency` | no | string | default="INR" |  |
| `service_amount` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `online_processing_charge_percent` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `online_processing_charge` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `total_payable` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `charge_label` | yes | string or null |  |  |
| `instructions` | yes | array of string |  |  |
| `accepts_bookings` | yes | boolean |  |  |
| `payment_options` | yes | array of string |  |  |
| `online_payment_available` | yes | boolean |  |  |
| `online_payment_unavailable_reason` | yes | string or null |  |  |

<a id="model-bookingresponse"></a>

### BookingResponse

Booking response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `salon_id` | yes | string |  |  |
| `staff_id` | yes | string |  |  |
| `customer_id` | no | string or null |  |  |
| `customer_name` | yes | string |  |  |
| `customer_phone` | no | string or null |  |  |
| `phone_verified` | yes | boolean |  |  |
| `source` | yes | string |  |  |
| `status` | yes | string |  |  |
| `start_datetime` | yes | string (date-time) |  |  |
| `end_datetime` | yes | string (date-time) |  |  |
| `estimated_end_datetime` | no | string (date-time) or null |  |  |
| `total_duration_minutes` | yes | integer |  |  |
| `total_price` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `payment_status` | yes | string |  |  |
| `payment_method` | no | string or null |  |  |
| `payment_preference` | no | string or null |  |  |
| `currency` | no | string | default="INR" |  |
| `deposit_amount` | no | string or null |  |  |
| `paid_amount` | no | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$; default="0" |  |
| `refunded_amount` | no | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$; default="0" |  |
| `payment_state` | no | string | default="unpaid" |  |
| `payment_mode` | no | string | default="PAY_AT_SALON" |  |
| `checkout_payment_status` | no | string | default="PAY_AT_SALON_PENDING" |  |
| `service_amount` | no | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$; default="0" |  |
| `online_processing_charge` | no | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$; default="0" |  |
| `total_payable` | no | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$; default="0" |  |
| `pending_amount_to_collect` | no | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$; default="0" |  |
| `collection_instructions` | no | string or null |  |  |
| `rejection_reason` | no | string or null |  |  |
| `cancellation_reason` | no | string or null |  |  |
| `notes` | no | string or null |  |  |
| `services` | no | array of [BookingLineResponse](#model-bookinglineresponse) |  |  |
| `salon_name` | no | string or null |  |  |
| `salon_address` | no | string or null |  |  |
| `salon_image` | no | string or null |  |  |
| `staff_name` | no | string or null |  |  |
| `staff_photo_url` | no | string or null |  |  |
| `created_at` | yes | string (date-time) |  |  |
| `updated_at` | yes | string (date-time) |  |  |
| `latest_payment_request_status` | no | string or null |  |  |
| `latest_payment_request_decision` | no | string or null |  |  |
| `latest_payment_request_reason` | no | string or null |  |  |
| `latest_cancellation_request_status` | no | string or null |  |  |
| `latest_cancellation_request_decision` | no | string or null |  |  |
| `latest_cancellation_request_reason` | no | string or null |  |  |
| `can_cancel` | no | boolean | default=false |  |
| `can_request_cancellation` | no | boolean | default=false |  |
| `can_confirm_payment` | no | boolean | default=false |  |

<a id="model-cancelbookingrequest"></a>

### CancelBookingRequest

Optional body for the customer cancel-booking endpoint.

Both fields are optional so customers who cancel without specifying a
reason (e.g. one-tap cancel) continue to work unchanged.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `reason_code` | no | `"schedule_conflict" \| "found_better" \| "personal_emergency" \| "booked_by_mistake" \| "service_not_needed" \| "other"` or null |  | Structured reason chip from the customer cancellation flow UI. |
| `reason_text` | no | string or null |  | Free-text note typed by the customer (may be empty). |

<a id="model-categorycreaterequest"></a>

### CategoryCreateRequest

Create service category request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `name` | yes | string | minLength=1 |  |
| `slug` | yes | string | minLength=1; pattern=^[a-z0-9-]+$ |  |
| `image_url` | no | string or null |  |  |
| `description` | no | string or null |  |  |
| `sort_order` | no | integer | default=0 |  |

<a id="model-categoryresponse"></a>

### CategoryResponse

Service category response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `name` | yes | string |  |  |
| `slug` | yes | string |  |  |
| `image_url` | no | string or null |  |  |
| `description` | no | string or null |  |  |
| `sort_order` | yes | integer |  |  |
| `is_active` | yes | boolean |  |  |
| `created_at` | yes | string (date-time) |  |  |
| `updated_at` | yes | string (date-time) |  |  |

<a id="model-categoryupdaterequest"></a>

### CategoryUpdateRequest

Update service category request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `name` | no | string or null |  |  |
| `slug` | no | string or null |  |  |
| `image_url` | no | string or null |  |  |
| `description` | no | string or null |  |  |
| `sort_order` | no | integer or null |  |  |
| `is_active` | no | boolean or null |  |  |

<a id="model-checkoutrequest"></a>

### CheckoutRequest

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `plan_id` | yes | string (uuid) |  |  |

<a id="model-checkoutresponse"></a>

### CheckoutResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `billing_id` | yes | string |  |  |
| `provider` | yes | string |  |  |
| `order_ref` | yes | string |  |  |
| `receipt` | yes | string |  |  |
| `plan_id` | yes | string |  |  |
| `plan_code` | yes | string |  |  |
| `amount` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*(?:\d{0,8}\|(?=[\d.]{1,11}0*$)\d{0,8}\.\d{0,2}0*$) |  |
| `currency` | yes | string |  |  |
| `billing_interval` | yes | string |  |  |
| `expires_at` | yes | string (date-time) |  |  |
| `client_payload` | yes | object |  |  |

<a id="model-closedsalonfigures"></a>

### ClosedSalonFigures

Money totals only: no booking, customer, staff or payment-level detail.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `currency` | yes | string |  |  |
| `online_collected` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Online payments settled, excluding overcollection. |
| `online_refunded` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `platform_fees` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Platform commission charged on online payments. |
| `commission_reversed` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Commission returned on refunds. |
| `platform_commission_net` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `overcollected` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `online_net` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Salon's online net: collected - refunded - net commission. |
| `manual_recorded` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Cash/UPI the salon recorded itself. |
| `subscription_paid` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Subscription fees the salon paid the platform. |
| `subscription_refunded` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Attributed to the month the subscription fee was PAID (the billing record has no refund date). |
| `platform_revenue` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Net commission + subscription paid - refunded. |
| `online_count` | yes | integer |  |  |
| `manual_count` | yes | integer |  |  |

<a id="model-closedsalonmonth"></a>

### ClosedSalonMonth

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `currency` | yes | string |  |  |
| `online_collected` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Online payments settled, excluding overcollection. |
| `online_refunded` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `platform_fees` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Platform commission charged on online payments. |
| `commission_reversed` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Commission returned on refunds. |
| `platform_commission_net` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `overcollected` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `online_net` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Salon's online net: collected - refunded - net commission. |
| `manual_recorded` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Cash/UPI the salon recorded itself. |
| `subscription_paid` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Subscription fees the salon paid the platform. |
| `subscription_refunded` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Attributed to the month the subscription fee was PAID (the billing record has no refund date). |
| `platform_revenue` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ | Net commission + subscription paid - refunded. |
| `online_count` | yes | integer |  |  |
| `manual_count` | yes | integer |  |  |
| `month` | yes | string | pattern=^\d{4}-\d{2}$ | Calendar month in Asia/Kolkata. |

<a id="model-closedsalonstatementresponse"></a>

### ClosedSalonStatementResponse

Month-end statement of a salon closed by its owner's account deletion.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `salon_id` | yes | string (uuid) |  |  |
| `months` | yes | array of [ClosedSalonMonth](#model-closedsalonmonth) |  |  |
| `totals` | yes | array of [ClosedSalonFigures](#model-closedsalonfigures) |  | One row per currency. |

<a id="model-closureaffectedbookingresponse"></a>

### ClosureAffectedBookingResponse

Booking whose reserved interval overlaps a proposed closure.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `booking_id` | yes | string |  |  |
| `customer_id` | no | string or null |  |  |
| `customer_name` | yes | string |  |  |
| `staff_id` | yes | string |  |  |
| `service_names` | no | array of string |  |  |
| `start_datetime` | yes | string (date-time) |  |  |
| `end_datetime` | yes | string (date-time) |  |  |
| `status` | yes | string |  |  |

<a id="model-closureapplyrequest"></a>

### ClosureApplyRequest

Confirmed closure with the exact previewed bookings and owner reason.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `kind` | yes | `"holiday" \| "leave"` |  |  |
| `holiday_date` | no | string (date) or null |  |  |
| `staff_id` | no | string or null |  |  |
| `start_datetime` | no | string (date-time) or null |  |  |
| `end_datetime` | no | string (date-time) or null |  |  |
| `reason` | yes | string | minLength=1; maxLength=500 |  |
| `affected_booking_ids` | no | array of string |  |  |
| `resolution` | no | `"cancel"` | default="cancel" |  |
| `title` | no | string or null |  |  |

<a id="model-closureapplyresponse"></a>

### ClosureApplyResponse

Applied closure and bookings cancelled in the same transaction.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `affected_count` | yes | integer | minimum=0.0 |  |
| `affected_bookings` | yes | array of [ClosureAffectedBookingResponse](#model-closureaffectedbookingresponse) |  |  |
| `closure_kind` | yes | `"holiday" \| "leave"` |  |  |
| `closure_id` | yes | string |  |  |
| `reason` | yes | string |  |  |

<a id="model-closurepreviewrequest"></a>

### ClosurePreviewRequest

Describe a holiday or staff/salon leave before it is applied.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `kind` | yes | `"holiday" \| "leave"` |  |  |
| `holiday_date` | no | string (date) or null |  |  |
| `staff_id` | no | string or null |  |  |
| `start_datetime` | no | string (date-time) or null |  |  |
| `end_datetime` | no | string (date-time) or null |  |  |

<a id="model-closurepreviewresponse"></a>

### ClosurePreviewResponse

Current server-owned impact set for a proposed closure.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `affected_count` | yes | integer | minimum=0.0 |  |
| `affected_bookings` | yes | array of [ClosureAffectedBookingResponse](#model-closureaffectedbookingresponse) |  |  |

<a id="model-confirmaccountdeletionrequest"></a>

### ConfirmAccountDeletionRequest

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `challenge_id` | yes | string (uuid) |  |  |
| `confirmation_token` | yes | string | minLength=20; maxLength=128 |  |
| `confirm` | yes | `"DELETE"` |  | Must be exactly "DELETE". |

Unknown fields are forbidden by this model.

<a id="model-databasehealthresponse"></a>

### DatabaseHealthResponse

Database health-check response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `status` | yes | string |  |  |
| `database` | yes | string |  |  |

<a id="model-delaybookingrequest"></a>

### DelayBookingRequest

Owner/staff request to record a delayed completion estimate.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `estimated_end_datetime` | yes | string (date-time) |  |  |
| `notify_affected_customers` | no | boolean | default=true |  |

<a id="model-deletionchallengeresponse"></a>

### DeletionChallengeResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `challenge_id` | yes | string (uuid) |  |  |
| `channel` | yes | `"email" \| "phone"` |  |  |
| `masked_destination` | yes | string |  |  |
| `expires_at` | yes | string (date-time) |  |  |
| `resend_available_at` | yes | string (date-time) |  |  |
| `bookings_to_cancel` | no | integer | default=0 | Owners only: upcoming pending/confirmed bookings that confirming will cancel (customers are notified and online payments refunded). Always 0 for customers. |

<a id="model-deviceregisterrequest"></a>

### DeviceRegisterRequest

Device registration request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `token` | yes | string |  |  |
| `platform` | no | string or null |  |  |
| `device_name` | no | string or null |  |  |

<a id="model-deviceregisterresponse"></a>

### DeviceRegisterResponse

Device registration response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `token` | yes | string |  |  |
| `platform` | no | string or null |  |  |

<a id="model-earningsresponse"></a>

### EarningsResponse

Owner earnings derived from the ledger.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `currency` | yes | string |  |  |
| `online_collected` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `online_refunded` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `platform_fees` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `commission_reversed` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `platform_commission_net` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `overcollected` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `online_net` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `manual_recorded` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `online_payment_count` | yes | integer |  |  |
| `manual_payment_count` | yes | integer |  |  |
| `note` | yes | string |  |  |

<a id="model-emaileventresponse"></a>

### EmailEventResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string (uuid) |  |  |
| `event_type` | yes | string |  |  |
| `status` | yes | string |  |  |
| `created_at` | yes | string (date-time) |  |  |
| `sent_at` | yes | string (date-time) or null |  |  |

<a id="model-forgotpasswordrequest"></a>

### ForgotPasswordRequest

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `email` | yes | string (email) |  |  |

<a id="model-forgotpasswordresponse"></a>

### ForgotPasswordResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `message` | no | string | default="If an account exists, a password reset email has been requested." |  |

<a id="model-httpvalidationerror"></a>

### HTTPValidationError

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `detail` | no | array of [ValidationError](#model-validationerror) |  |  |

<a id="model-healthresponse"></a>

### HealthResponse

Health-check response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `status` | yes | string |  |  |

<a id="model-holidaycreaterequest"></a>

### HolidayCreateRequest

Create salon holiday request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `holiday_date` | yes | string (date) |  |  |
| `title` | no | string or null |  |  |
| `is_recurring` | no | boolean | default=false |  |

<a id="model-holidayresponse"></a>

### HolidayResponse

Salon holiday response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `salon_id` | yes | string |  |  |
| `holiday_date` | yes | string (date) |  |  |
| `title` | no | string or null |  |  |
| `is_recurring` | yes | boolean |  |  |
| `created_at` | yes | string (date-time) |  |  |
| `updated_at` | yes | string (date-time) |  |  |

<a id="model-imagefamilyresponse"></a>

### ImageFamilyResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `public_url` | yes | string |  |  |
| `family_id` | yes | string |  |  |
| `policy_version` | yes | string |  |  |
| `variants` | yes | map of [ImageVariantResponse](#model-imagevariantresponse) |  |  |

<a id="model-imageuploadurlrequest"></a>

### ImageUploadUrlRequest

Request body for generating a short-lived backend upload capability.

The client PUTs image bytes to the backend validation gateway using the returned URL.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `content_type` | no | string | default="image/jpeg" | MIME type of the image to upload (e.g. 'image/jpeg', 'image/png'). |
| `filename` | yes | string | minLength=1 | Original filename (e.g. 'cover.jpg'). Used only to derive the file extension. |

<a id="model-imageuploadurlresponse"></a>

### ImageUploadUrlResponse

Response containing the signed upload URL and resulting public URL.

Upload flow:
1. POST /v1/salons/me/images/upload-url  → receive upload_url + public_url
2. PUT <upload_url> with the image binary and a 'Content-Type: <mime>' header
3. POST /v1/salons/me/images { "url": "<public_url>", ... } to record in DB

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `upload_url` | yes | string |  | Signed PUT URL. Client must PUT to this within expires_in seconds. |
| `result_url` | no | string or null |  | Read-only URL (cannot upload). GET it after PUT for WebP variant URLs and metadata. |
| `public_url` | yes | string |  | Permanent public URL of the uploaded object. Store this in the DB. |
| `expires_in` | yes | integer |  | Upload URL TTL in seconds. |

<a id="model-imagevariantresponse"></a>

### ImageVariantResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `variant` | yes | string |  |  |
| `url` | yes | string |  |  |
| `width` | yes | integer |  |  |
| `height` | yes | integer |  |  |
| `mime` | yes | string |  |  |
| `size` | yes | integer |  |  |
| `sha256` | yes | string |  |  |

<a id="model-manualsubscriptioncreaterequest"></a>

### ManualSubscriptionCreateRequest

Manual/test activation — admin only.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `salon_id` | yes | string |  |  |
| `plan_id` | yes | string |  |  |
| `status` | no | `"pending" \| "trialing" \| "active" \| "past_due"` | default="pending" |  |
| `starts_at` | no | string (date-time) or null |  |  |
| `current_period_start` | no | string (date-time) or null |  |  |
| `current_period_end` | no | string (date-time) or null |  |  |

<a id="model-markallnotificationsreadresponse"></a>

### MarkAllNotificationsReadResponse

Number of unread notifications marked as read.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `updated_count` | yes | integer | minimum=0.0 |  |

<a id="model-notificationresponse"></a>

### NotificationResponse

Notification response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `user_id` | yes | string |  |  |
| `booking_id` | no | string or null |  |  |
| `type` | no | string or null |  |  |
| `title` | yes | string |  |  |
| `body` | no | string or null |  |  |
| `read` | yes | boolean |  |  |
| `read_at` | no | string (date-time) or null |  |  |
| `created_at` | yes | string (date-time) |  |  |

<a id="model-ownerpayoutaccountrequest"></a>

### OwnerPayoutAccountRequest

Partial update of the owner's payout destination (merge semantics).

Omitted fields keep their stored value; an explicit ``null`` clears the field.
Error messages never include the submitted value.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `account_holder_name` | no | string or null |  |  |
| `upi_id` | no | string or null |  |  |
| `bank_name` | no | string or null |  |  |
| `bank_account_number` | no | string or null |  |  |
| `ifsc` | no | string or null |  |  |

Unknown fields are forbidden by this model.

<a id="model-ownerpayoutaccountresponse"></a>

### OwnerPayoutAccountResponse

Masked payout account. The full account number is never returned.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `configured` | yes | boolean |  |  |
| `account_holder_name` | no | string or null |  |  |
| `upi_id` | no | string or null |  |  |
| `bank_name` | no | string or null |  |  |
| `bank_account_last4` | no | string or null |  |  |
| `ifsc` | no | string or null |  |  |
| `has_upi` | yes | boolean |  |  |
| `has_bank` | yes | boolean |  |  |
| `updated_at` | no | string (date-time) or null |  |  |

<a id="model-ownersaloncompleteprofilerequest"></a>

### OwnerSalonCompleteProfileRequest

Final onboarding payload used to submit an owner salon for admin review.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `name` | no | string or null |  |  |
| `category` | no | string or null |  |  |
| `address` | no | string or null |  |  |
| `city` | no | string or null |  |  |
| `lat` | no | number or null |  |  |
| `lng` | no | number or null |  |  |
| `timezone` | no | string or null |  |  |
| `working_hours` | no | object or null |  |  |
| `approval_mode` | no | `"auto" \| "manual"` or null |  |  |

Unknown fields are forbidden by this model.

<a id="model-ownersalonresponse"></a>

### OwnerSalonResponse

Owner salon response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `owner_id` | yes | string |  |  |
| `name` | yes | string |  |  |
| `category` | no | string or null |  |  |
| `address` | no | string or null |  |  |
| `city` | no | string or null |  |  |
| `lat` | no | number or null |  |  |
| `lng` | no | number or null |  |  |
| `timezone` | yes | string |  |  |
| `working_hours` | yes | object |  |  |
| `approval_mode` | yes | string |  |  |
| `accepting_bookings` | yes | boolean |  |  |
| `slot_interval_minutes` | yes | integer |  |  |
| `qr_token` | yes | string |  |  |
| `profile_completed` | yes | boolean |  |  |
| `approval_status` | yes | `"pending" \| "approved" \| "rejected"` |  |  |
| `approved_at` | no | string (date-time) or null |  |  |
| `approved_by` | no | string or null |  |  |
| `rejection_reason` | no | string or null |  |  |
| `is_active` | yes | boolean |  |  |
| `images` | no | array of [SalonImageResponse](#model-salonimageresponse) | maxItems=3 | One separate cover (is_main=true) and at most two distinct gallery slides. |
| `created_at` | yes | string (date-time) |  |  |
| `updated_at` | yes | string (date-time) |  |  |

<a id="model-ownersalonsettingsrequest"></a>

### OwnerSalonSettingsRequest

Owner salon settings request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `approval_mode` | no | `"auto" \| "manual"` or null |  |  |
| `working_hours` | no | object or null |  |  |
| `accepting_bookings` | no | boolean or null |  |  |

<a id="model-ownersalonupdaterequest"></a>

### OwnerSalonUpdateRequest

Owner salon update request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `name` | no | string or null |  |  |
| `category` | no | string or null |  |  |
| `address` | no | string or null |  |  |
| `city` | no | string or null |  |  |
| `lat` | no | number or null |  |  |
| `lng` | no | number or null |  |  |
| `timezone` | no | string or null |  |  |
| `working_hours` | no | object or null |  |  |
| `approval_mode` | no | `"auto" \| "manual"` or null |  |  |

Unknown fields are forbidden by this model.

<a id="model-ownersetupstatusresponse"></a>

### OwnerSetupStatusResponse

Authoritative checklist of what a new owner still has to finish.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `completed_count` | yes | integer |  |  |
| `total_count` | yes | integer |  |  |
| `is_complete` | yes | boolean |  |  |
| `items` | yes | array of [SetupItemResponse](#model-setupitemresponse) |  |  |

<a id="model-paymentconfigresponse"></a>

### PaymentConfigResponse

What the apps need to decide whether to offer online payment.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `enabled` | yes | boolean |  |  |
| `online_payment_available` | no | boolean | default=false |  |
| `online_payment_unavailable_reason` | no | string or null | default="Online payment coming soon." |  |
| `provider` | no | string or null |  |  |
| `public_key` | no | string or null |  |  |
| `currency` | yes | string |  |  |
| `advance_percent` | yes | integer |  |  |
| `settlement_model` | no | string or null |  |  |
| `confirmation` | no | string or null |  |  |

<a id="model-paymentconfirmrequest"></a>

### PaymentConfirmRequest

Client-side success callback, verified server-side before anything is trusted.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `order_ref` | yes | string | minLength=1; maxLength=200 |  |
| `payment_ref` | no | string or null |  |  |
| `signature` | no | string or null |  |  |

Unknown fields are forbidden by this model.

<a id="model-paymentintentrequest"></a>

### PaymentIntentRequest

Start an online payment for a booking. The amount is NEVER client supplied.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `purpose` | no | `"deposit" \| "balance" \| "full"` or null |  |  |

Unknown fields are forbidden by this model.

<a id="model-paymentintentresponse"></a>

### PaymentIntentResponse

Open payment order plus the opaque payload the checkout SDK needs.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `payment_id` | yes | string |  |  |
| `provider` | yes | string |  |  |
| `order_ref` | yes | string |  |  |
| `purpose` | yes | string |  |  |
| `amount` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `currency` | yes | string |  |  |
| `client_payload` | no | object |  |  |
| `expires_at` | no | string (date-time) or null |  |  |

<a id="model-paymentrefreshrequest"></a>

### PaymentRefreshRequest

Ask the backend to re-read the order from the provider. Carries no proof of payment.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `order_ref` | yes | string | minLength=1; maxLength=200 |  |

Unknown fields are forbidden by this model.

<a id="model-paymentrefundrequest"></a>

### PaymentRefundRequest

Refund a captured online payment (omit amount for the full remainder).

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `amount` | no | number or string or null |  |  |
| `reason` | no | string or null |  |  |

Unknown fields are forbidden by this model.

<a id="model-paymentrequest"></a>

### PaymentRequest

Record booking payment request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `payment_method` | yes | `"cash" \| "upi_direct"` |  |  |

<a id="model-payouthistoryentryresponse"></a>

### PayoutHistoryEntryResponse

One change to the payout destination.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `changed_at` | yes | string (date-time) |  |  |
| `action` | yes | `"created" \| "updated"` |  |  |
| `changed_fields` | no | array of string |  |  |
| `changed_by_name` | no | string or null |  |  |
| `before` | no | [PayoutSnapshotResponse](#model-payoutsnapshotresponse) or null |  |  |
| `after` | yes | [PayoutSnapshotResponse](#model-payoutsnapshotresponse) |  |  |

<a id="model-payoutsnapshotresponse"></a>

### PayoutSnapshotResponse

Point-in-time payout destination; the account number is last four digits only.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `account_holder_name` | no | string or null |  |  |
| `upi_id` | no | string or null |  |  |
| `bank_name` | no | string or null |  |  |
| `ifsc` | no | string or null |  |  |
| `bank_account_last4` | no | string or null |  |  |

<a id="model-plancreaterequest"></a>

### PlanCreateRequest

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `code` | yes | string | minLength=1; maxLength=60 |  |
| `name` | yes | string | minLength=1; maxLength=120 |  |
| `description` | no | string or null |  |  |
| `tier` | no | integer | minimum=0.0; default=0 |  |
| `ranking_weight` | no | integer | minimum=0.0; maximum=100000.0; default=0 |  |
| `price_amount` | no | number or string | default="0" |  |
| `currency` | no | string | pattern=^[A-Z]{3}$; default="INR" |  |
| `billing_interval` | no | `"monthly" \| "quarterly" \| "semiannual" \| "yearly"` | default="monthly" |  |

<a id="model-planresponse"></a>

### PlanResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `code` | yes | string |  |  |
| `name` | yes | string |  |  |
| `description` | no | string or null |  |  |
| `tier` | yes | integer |  |  |
| `ranking_weight` | yes | integer |  |  |
| `price_amount` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*(?:\d{0,8}\|(?=[\d.]{1,11}0*$)\d{0,8}\.\d{0,2}0*$) |  |
| `currency` | yes | string |  |  |
| `billing_interval` | yes | string |  |  |
| `features` | no | object |  |  |
| `tax_inclusive` | no | boolean or null |  |  |
| `is_active` | yes | boolean |  |  |
| `created_at` | yes | string (date-time) |  |  |
| `updated_at` | yes | string (date-time) |  |  |

<a id="model-plansummary"></a>

### PlanSummary

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `code` | yes | string |  |  |
| `name` | yes | string |  |  |
| `tier` | yes | integer |  |  |

<a id="model-planupdaterequest"></a>

### PlanUpdateRequest

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `name` | no | string or null |  |  |
| `description` | no | string or null |  |  |
| `tier` | no | integer or null |  |  |
| `ranking_weight` | no | integer or null |  |  |
| `price_amount` | no | number or string or null |  |  |
| `currency` | no | string or null |  |  |
| `billing_interval` | no | `"monthly" \| "quarterly" \| "semiannual" \| "yearly"` or null |  |  |
| `is_active` | no | boolean or null |  |  |

<a id="model-profileupdaterequest"></a>

### ProfileUpdateRequest

Shared profile update request (PATCH /profiles/me).

Used by owners, staff, and customers — not customer-only despite the name.
Fields are all optional; only explicitly sent fields are written.
Sending ``null`` for a nullable field (e.g. ``phone``) clears it.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `full_name` | no | string or null |  |  |
| `phone` | no | string or null |  |  |
| `avatar_url` | no | string or null |  |  |

<a id="model-publicstaffresponse"></a>

### PublicStaffResponse

Customer-facing staff/barber summary for salon detail and booking flow.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `name` | yes | string |  |  |
| `photo_url` | no | string or null |  |  |
| `specialization` | no | string or null |  |  |

<a id="model-purchasableplanresponse"></a>

### PurchasablePlanResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `code` | yes | string |  |  |
| `name` | yes | string |  |  |
| `description` | no | string or null |  |  |
| `tier` | yes | integer |  |  |
| `price_amount` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*(?:\d{0,8}\|(?=[\d.]{1,11}0*$)\d{0,8}\.\d{0,2}0*$) |  |
| `currency` | yes | string |  |  |
| `billing_interval` | yes | `"monthly" \| "quarterly" \| "semiannual" \| "yearly"` |  |  |
| `features` | no | object |  |  |
| `tax_inclusive` | no | boolean or null |  |  |

<a id="model-qrcodeurlresponse"></a>

### QrCodeUrlResponse

Public image URL that can be displayed without an Authorization header.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `url` | yes | string |  |  |
| `cached` | no | boolean | default=false |  |

<a id="model-redishealthresponse"></a>

### RedisHealthResponse

Redis health-check response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `status` | yes | string |  |  |
| `redis` | yes | string |  |  |

<a id="model-refreshrequest"></a>

### RefreshRequest

Refresh-token request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `refresh_token` | yes | string | minLength=1 |  |

<a id="model-refundresponse"></a>

### RefundResponse

One refund.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `payment_id` | yes | string |  |  |
| `amount` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `status` | yes | string |  |  |
| `reason` | no | string or null |  |  |
| `applies_to_excess` | no | boolean | default=false |  |
| `created_at` | yes | string (date-time) |  |  |
| `processed_at` | no | string (date-time) or null |  |  |

<a id="model-rejectbookingrequest"></a>

### RejectBookingRequest

Reject booking request.

The barber must pick a reason so the customer knows why their booking
was declined.  Free-form text is the backing field; the UI is expected
to offer preset chips that map to localised strings.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `rejection_reason` | yes | string | minLength=1; maxLength=500 | Human-readable reason shown to the customer in the push notification and booking detail screen. |

<a id="model-reportrequest"></a>

### ReportRequest

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `salon_id` | yes | string (uuid) |  |  |
| `reason` | yes | string | minLength=1; maxLength=200 |  |
| `details` | no | string | maxLength=5000; default="" |  |
| `salon_name` | no | string or null |  |  |
| `created_at` | no | string (date-time) or null |  |  |

<a id="model-reportresponse"></a>

### ReportResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string (uuid) |  |  |
| `status` | yes | `"received"` |  |  |

<a id="model-role"></a>

### Role

Supported platform roles.

`"super_admin" \| "owner" \| "staff" \| "customer"`

<a id="model-salondetailresponse"></a>

### SalonDetailResponse

Salon detail response.

Images are embedded here as they are always needed for the detail view.
Services and staff are NOT embedded — use the dedicated endpoints:
  - GET /salons/{salon_id}/services
  - GET /salons/{salon_id}/staff

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `accepts_bookings` | no | boolean | default=true | False while the salon is paused or not bookable. |
| `payment_options` | no | array of `"PAY_AT_SALON" \| "PAY_ONLINE"` |  | Payment methods currently permitted for a new booking at this salon. |
| `online_payment_available` | no | boolean | default=false | True only when PAY_ONLINE is listed. |
| `online_payment_unavailable_reason` | no | string or null | default="Online payment coming soon." | Customer-facing reason online payment is not offered; null when it is available. |
| `id` | yes | string |  |  |
| `name` | yes | string |  |  |
| `category` | no | string or null |  |  |
| `address` | no | string or null |  |  |
| `city` | no | string or null |  |  |
| `lat` | no | number or null |  |  |
| `lng` | no | number or null |  |  |
| `timezone` | yes | string |  |  |
| `working_hours` | yes | object |  |  |
| `approval_mode` | yes | string |  |  |
| `accepting_bookings` | no | boolean | default=true |  |
| `profile_completed` | yes | boolean |  |  |
| `is_active` | yes | boolean |  |  |
| `images` | no | array of [SalonImageResponse](#model-salonimageresponse) | maxItems=3 | One separate cover (is_main=true) and at most two distinct gallery slides. |

<a id="model-salonimagecreaterequest"></a>

### SalonImageCreateRequest

Create salon image request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `url` | yes | string |  |  |
| `caption` | no | string or null |  |  |
| `is_main` | no | boolean | default=false |  |
| `sort_order` | no | integer | default=0 |  |

<a id="model-salonimageresponse"></a>

### SalonImageResponse

Salon image response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `salon_id` | yes | string |  |  |
| `url` | yes | string |  |  |
| `caption` | no | string or null |  |  |
| `is_main` | yes | boolean |  |  |
| `sort_order` | yes | integer |  |  |
| `created_at` | yes | string (date-time) |  |  |
| `updated_at` | yes | string (date-time) |  |  |

<a id="model-salonimageupdaterequest"></a>

### SalonImageUpdateRequest

Update salon image request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `url` | no | string or null |  |  |
| `caption` | no | string or null |  |  |
| `is_main` | no | boolean or null |  |  |
| `sort_order` | no | integer or null |  |  |

<a id="model-salonsummaryresponse"></a>

### SalonSummaryResponse

Salon list response item.

Services are NOT embedded here. Call GET /salons/{salon_id}/services
to fetch services for a specific salon.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `accepts_bookings` | no | boolean | default=true | False while the salon is paused or not bookable. |
| `payment_options` | no | array of `"PAY_AT_SALON" \| "PAY_ONLINE"` |  | Payment methods currently permitted for a new booking at this salon. |
| `online_payment_available` | no | boolean | default=false | True only when PAY_ONLINE is listed. |
| `online_payment_unavailable_reason` | no | string or null | default="Online payment coming soon." | Customer-facing reason online payment is not offered; null when it is available. |
| `id` | yes | string |  |  |
| `name` | yes | string |  |  |
| `category` | no | string or null |  |  |
| `address` | no | string or null |  |  |
| `city` | no | string or null |  |  |
| `lat` | no | number or null |  |  |
| `lng` | no | number or null |  |  |
| `timezone` | yes | string |  |  |
| `approval_mode` | yes | string |  |  |
| `accepting_bookings` | no | boolean | default=true |  |
| `profile_completed` | yes | boolean |  |  |
| `is_active` | yes | boolean |  |  |
| `working_hours` | no | object or null |  |  |
| `image_url` | no | string or null |  |  |
| `starting_price` | no | string or null |  |  |
| `distance_km` | no | number or null |  |  |

<a id="model-servicecreaterequest"></a>

### ServiceCreateRequest

Create service request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `category_name` | no | string or null |  |  |
| `subcategory_name` | no | string or null |  |  |
| `photo_url` | no | string or null |  |  |
| `subcategory_id` | no | string or null |  |  |
| `name` | yes | string |  |  |
| `duration_minutes` | yes | integer | exclusiveMinimum=0.0 |  |
| `price` | yes | number or string |  |  |
| `is_active` | no | boolean | default=true |  |

Unknown fields are forbidden by this model.

<a id="model-serviceresponse"></a>

### ServiceResponse

Service response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `salon_id` | yes | string |  |  |
| `subcategory_id` | yes | string |  |  |
| `name` | yes | string |  |  |
| `duration_minutes` | yes | integer |  |  |
| `price` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `is_active` | yes | boolean |  |  |
| `category_name` | no | string or null |  |  |
| `subcategory_name` | no | string or null |  |  |
| `photo_url` | no | string or null |  |  |
| `created_at` | no | string (date-time) or null |  |  |
| `updated_at` | no | string (date-time) or null |  |  |

<a id="model-serviceupdaterequest"></a>

### ServiceUpdateRequest

Update service request; omitted fields retain their stored values.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `category_name` | no | string or null |  |  |
| `subcategory_name` | no | string or null |  |  |
| `photo_url` | no | string or null |  |  |
| `subcategory_id` | no | string or null |  |  |
| `name` | no | string or null |  |  |
| `duration_minutes` | no | integer or null |  |  |
| `price` | no | number or string or null |  |  |
| `is_active` | no | boolean or null |  |  |

Unknown fields are forbidden by this model.

<a id="model-settlementaccountresponse"></a>

### SettlementAccountResponse

Salon payee account at the provider (split-settlement model only).

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `provider_enabled` | yes | boolean |  |  |
| `supported` | yes | boolean |  |  |
| `requires_details` | no | boolean | default=false |  |
| `onboarding_status` | yes | string |  |  |
| `requirements` | no | array of string |  |  |
| `account_reference_masked` | no | string or null |  |  |

<a id="model-settlementregistrationrequest"></a>

### SettlementRegistrationRequest

KYC and payout details for payee registration.

Used once in memory to call the provider. Never stored, logged, echoed in errors or
returned. Either (bank_account_number + ifsc) or upi_id is required, not both.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `legal_name` | yes | string | minLength=2; maxLength=100 |  |
| `contact_email` | yes | string (email) |  |  |
| `contact_phone` | yes | string | pattern=^[6-9][0-9]{9}$ |  |
| `account_type` | yes | `"individual" \| "business"` |  |  |
| `business_type` | yes | string | minLength=2; maxLength=60 |  |
| `pan` | yes | string | pattern=^[A-Z]{5}[0-9]{4}[A-Z]$ |  |
| `bank_account_number` | no | string or null |  |  |
| `ifsc` | no | string or null |  |  |
| `upi_id` | no | string or null |  |  |

Unknown fields are forbidden by this model.

<a id="model-setupitemresponse"></a>

### SetupItemResponse

One step of the new-owner setup checklist.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `key` | yes | `"profile_basics" \| "working_hours" \| "photos" \| "services" \| "staff" \| "payout"` |  |  |
| `title` | yes | string |  |  |
| `description` | yes | string |  |  |
| `done` | yes | boolean |  |  |
| `action` | yes | `"business_profile" \| "working_hours" \| "photos" \| "services" \| "staff" \| "payout"` |  |  |

<a id="model-staffcreaterequest"></a>

### StaffCreateRequest

Create staff request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `profile_id` | no | string or null |  |  |
| `name` | yes | string |  |  |
| `photo_url` | no | string or null |  |  |
| `specialization` | no | string or null |  |  |
| `experience` | no | string or null |  |  |
| `working_hours` | no | object or null |  |  |

<a id="model-staffresponse"></a>

### StaffResponse

Staff response (owner-facing, includes full detail).

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `salon_id` | yes | string |  |  |
| `profile_id` | no | string or null |  |  |
| `name` | yes | string |  |  |
| `photo_url` | no | string or null |  |  |
| `specialization` | no | string or null |  |  |
| `experience` | no | string or null |  |  |
| `working_hours` | no | object or null |  |  |
| `is_active` | yes | boolean |  |  |
| `created_at` | yes | string (date-time) |  |  |
| `updated_at` | yes | string (date-time) |  |  |

<a id="model-staffserviceassignrequest"></a>

### StaffServiceAssignRequest

Assign service to staff request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `service_id` | yes | string |  |  |
| `duration_minutes` | no | integer or null |  |  |
| `price_override` | no | number or string or null |  |  |
| `specialization` | no | string or null |  |  |

<a id="model-staffservicelanguagesrequest"></a>

### StaffServiceLanguagesRequest

Set language codes for a staff service assignment (idempotent PUT).

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `language_codes` | yes | array of string |  | ISO 639-1 codes, e.g. ['en', 'ml']. Replaces the current list. |

<a id="model-staffserviceresponse"></a>

### StaffServiceResponse

Staff service response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `staff_id` | yes | string |  |  |
| `service_id` | yes | string |  |  |
| `duration_minutes` | no | integer or null |  |  |
| `price_override` | no | string or null |  |  |
| `specialization` | no | string or null |  |  |
| `is_active` | yes | boolean |  |  |
| `created_at` | yes | string (date-time) |  |  |
| `updated_at` | yes | string (date-time) |  |  |

<a id="model-staffupdaterequest"></a>

### StaffUpdateRequest

Update staff request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `profile_id` | no | string or null |  |  |
| `name` | no | string or null |  |  |
| `photo_url` | no | string or null |  |  |
| `specialization` | no | string or null |  |  |
| `experience` | no | string or null |  |  |
| `working_hours` | no | object or null |  |  |
| `is_active` | no | boolean or null |  |  |

<a id="model-startdeletionchallengerequest"></a>

### StartDeletionChallengeRequest

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `channel` | yes | `"email" \| "phone"` |  |  |
| `contact` | no | string or null |  | Optional. If sent it must equal the account's verified contact; the code is only ever delivered to the account's own verified contact. |

Unknown fields are forbidden by this model.

<a id="model-subcategorycreaterequest"></a>

### SubcategoryCreateRequest

Create service subcategory request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `category_id` | yes | string |  |  |
| `name` | yes | string | minLength=1 |  |
| `slug` | yes | string | minLength=1; pattern=^[a-z0-9-]+$ |  |
| `image_url` | no | string or null |  |  |
| `description` | no | string or null |  |  |
| `sort_order` | no | integer | default=0 |  |

<a id="model-subcategoryresponse"></a>

### SubcategoryResponse

Service subcategory response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `category_id` | yes | string |  |  |
| `name` | yes | string |  |  |
| `slug` | yes | string |  |  |
| `image_url` | no | string or null |  |  |
| `description` | no | string or null |  |  |
| `sort_order` | yes | integer |  |  |
| `is_active` | yes | boolean |  |  |
| `created_at` | yes | string (date-time) |  |  |
| `updated_at` | yes | string (date-time) |  |  |

<a id="model-subcategoryupdaterequest"></a>

### SubcategoryUpdateRequest

Update service subcategory request.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `name` | no | string or null |  |  |
| `slug` | no | string or null |  |  |
| `image_url` | no | string or null |  |  |
| `description` | no | string or null |  |  |
| `sort_order` | no | integer or null |  |  |
| `is_active` | no | boolean or null |  |  |

<a id="model-subscriptionconfigresponse"></a>

### SubscriptionConfigResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `enabled` | yes | boolean |  |  |
| `provider` | no | string or null |  |  |
| `mode` | no | `"one_time"` | default="one_time" |  |
| `renewal` | no | `"manual"` | default="manual" |  |
| `native_purchase_allowed` | no | `false` | default=false |  |
| `public_key` | no | string or null |  |  |
| `currency` | no | string | default="INR" |  |

<a id="model-subscriptioneventresponse"></a>

### SubscriptionEventResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `salon_subscription_id` | no | string or null |  |  |
| `provider_name` | no | string or null |  |  |
| `event_type` | yes | string |  |  |
| `processing_status` | yes | string |  |  |
| `received_at` | yes | string (date-time) |  |  |
| `processed_at` | no | string (date-time) or null |  |  |
| `error_message` | no | string or null |  |  |

<a id="model-subscriptionresponse"></a>

### SubscriptionResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `salon_id` | yes | string |  |  |
| `plan_id` | yes | string |  |  |
| `plan_code` | no | string or null |  |  |
| `plan_name` | no | string or null |  |  |
| `plan_tier` | no | integer or null |  |  |
| `plan_ranking_weight` | no | integer or null |  |  |
| `status` | yes | `"pending" \| "trialing" \| "active" \| "past_due" \| "cancelled" \| "expired" \| "suspended"` |  |  |
| `starts_at` | no | string (date-time) or null |  |  |
| `current_period_start` | no | string (date-time) or null |  |  |
| `current_period_end` | no | string (date-time) or null |  |  |
| `cancelled_at` | no | string (date-time) or null |  |  |
| `expires_at` | no | string (date-time) or null |  |  |
| `grace_period_end` | no | string (date-time) or null |  |  |
| `created_at` | yes | string (date-time) |  |  |
| `updated_at` | yes | string (date-time) |  |  |

<a id="model-subscriptionstateresponse"></a>

### SubscriptionStateResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `provider_enabled` | yes | boolean |  |  |
| `status` | no | string or null |  |  |
| `plan` | no | [PlanSummary](#model-plansummary) or null |  |  |
| `entitlement_active` | yes | boolean |  |  |
| `entitlement_state` | yes | `"none" \| "active" \| "cancelled_paid_through" \| "grace" \| "expired" \| "suspended"` |  |  |
| `features` | no | object |  |  |
| `paid_through` | no | string (date-time) or null |  |  |
| `grace_ends_at` | no | string (date-time) or null |  |  |
| `in_grace` | yes | boolean |  |  |
| `renewal` | no | `"manual"` | default="manual" |  |
| `cancelled` | yes | boolean |  |  |
| `cancelled_at` | no | string (date-time) or null |  |  |
| `latest_payment` | no | [BillingPaymentResponse](#model-billingpaymentresponse) or null |  |  |
| `open_checkout` | no | [BillingPaymentResponse](#model-billingpaymentresponse) or null |  |  |
| `verification` | no | string or null |  |  |

<a id="model-supportcreaterequest"></a>

### SupportCreateRequest

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `subject` | yes | string | minLength=1; maxLength=200 |  |
| `body` | yes | string | minLength=1; maxLength=5000 |  |
| `salon_id` | no | string (uuid) or null |  |  |

Unknown fields are forbidden by this model.

<a id="model-supportmessageresponse"></a>

### SupportMessageResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string (uuid) |  |  |
| `author_id` | yes | string (uuid) or null |  |  |
| `body` | yes | string |  |  |
| `created_at` | yes | string (date-time) |  |  |

<a id="model-supportreplyrequest"></a>

### SupportReplyRequest

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `body` | yes | string | minLength=1; maxLength=5000 |  |

Unknown fields are forbidden by this model.

<a id="model-supportticketresponse"></a>

### SupportTicketResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string (uuid) |  |  |
| `customer_id` | yes | string (uuid) |  |  |
| `salon_id` | yes | string (uuid) or null |  |  |
| `subject` | yes | string |  |  |
| `status` | yes | string |  |  |
| `created_at` | yes | string (date-time) |  |  |
| `updated_at` | yes | string (date-time) |  |  |
| `messages` | no | array of [SupportMessageResponse](#model-supportmessageresponse) |  |  |

<a id="model-tokenresponse"></a>

### TokenResponse

Supabase token response returned by the API.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `access_token` | yes | string |  |  |
| `refresh_token` | no | string or null |  |  |
| `token_type` | no | string | default="bearer" |  |
| `expires_in` | no | integer or null |  |  |

<a id="model-validationerror"></a>

### ValidationError

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `loc` | yes | array of string or integer |  |  |
| `msg` | yes | string |  |  |
| `type` | yes | string |  |  |
| `input` | no | any |  |  |
| `ctx` | no | object |  |  |

<a id="model-verifieddeletionchallengeresponse"></a>

### VerifiedDeletionChallengeResponse

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `confirmation_token` | yes | string |  |  |
| `expires_at` | yes | string (date-time) |  |  |

<a id="model-verifydeletionchallengerequest"></a>

### VerifyDeletionChallengeRequest

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `code` | yes | string | minLength=4; maxLength=12; pattern=^[0-9A-Za-z]+$ |  |

Unknown fields are forbidden by this model.

<a id="model-verifyrequest"></a>

### VerifyRequest

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `order_ref` | yes | string | minLength=1; maxLength=100 |  |
| `payment_ref` | no | string or null |  |  |
| `signature` | no | string or null |  |  |

<a id="model-walkinsalonresponse"></a>

### WalkInSalonResponse

Walk-in salon page — salon info + services + staff.

Returned by GET /v1/walkin/{qr_token}.
The web app uses this as the single data fetch on page load:
- Mini-header: name, city, address, image_url
- Service chips: services[]
- Staff chips: staff[]
Slot availability is fetched separately via GET /v1/availability.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `accepts_bookings` | no | boolean | default=true | False while the salon is paused or not bookable. |
| `payment_options` | no | array of `"PAY_AT_SALON" \| "PAY_ONLINE"` |  | Payment methods currently permitted for a new booking at this salon. |
| `online_payment_available` | no | boolean | default=false | True only when PAY_ONLINE is listed. |
| `online_payment_unavailable_reason` | no | string or null | default="Online payment coming soon." | Customer-facing reason online payment is not offered; null when it is available. |
| `id` | yes | string |  |  |
| `name` | yes | string |  |  |
| `city` | no | string or null |  |  |
| `address` | no | string or null |  |  |
| `image_url` | no | string or null |  |  |
| `images` | no | array of [SalonImageResponse](#model-salonimageresponse) | maxItems=3 | One separate cover (is_main=true) and at most two distinct gallery slides. |
| `qr_token` | no | string or null |  |  |
| `timezone` | yes | string |  |  |
| `approval_mode` | yes | string |  |  |
| `accepting_bookings` | no | boolean | default=true |  |
| `working_hours` | no | object |  |  |
| `services` | no | array of [WalkInServiceSummary](#model-walkinservicesummary) |  |  |
| `staff` | no | array of [WalkInStaffSummary](#model-walkinstaffsummary) |  |  |

<a id="model-walkinservicesummary"></a>

### WalkInServiceSummary

Service summary for walk-in display.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `salon_id` | yes | string |  |  |
| `subcategory_id` | yes | string |  |  |
| `name` | yes | string |  |  |
| `duration_minutes` | yes | integer |  |  |
| `price` | yes | string | pattern=^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$ |  |
| `is_active` | yes | boolean |  |  |
| `category_name` | no | string or null |  |  |
| `subcategory_name` | no | string or null |  |  |
| `photo_url` | no | string or null |  |  |

<a id="model-walkinstaffsummary"></a>

### WalkInStaffSummary

Staff member summary for walk-in display.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `name` | yes | string |  |  |
| `photo_url` | no | string or null |  |  |
| `specialization` | no | string or null |  |  |
| `service_ids` | no | array of string |  |  |

<a id="model-walkinverifyphonerequest"></a>

### WalkInVerifyPhoneRequest

Phone OTP send/verify request.

Send with phone only to trigger the OTP.
Send with phone + otp to verify and get a JWT.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `phone` | yes | string |  | Phone number including country code, e.g. +919876543210 |
| `otp` | no | string or null |  | 6-digit OTP received by SMS |

<a id="model-walkinverifyphoneresponse"></a>

### WalkInVerifyPhoneResponse

OTP send or verify response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `verified` | yes | boolean |  |  |
| `access_token` | no | string or null |  |  |
| `refresh_token` | no | string or null |  |  |

<a id="model-webhookackresponse"></a>

### WebhookAckResponse

Acknowledgement of a webhook delivery.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `status` | yes | `"accepted" \| "duplicate" \| "ignored"` |  |  |

<a id="model-app__api__v1__schemas__admin__languageresponse"></a>

### app__api__v1__schemas__admin__LanguageResponse

Language reference response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `code` | yes | string |  |  |
| `name` | yes | string |  |  |

<a id="model-app__api__v1__schemas__auth__profileresponse"></a>

### app__api__v1__schemas__auth__ProfileResponse

Current profile response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `role` | yes | [Role](#model-role) |  |  |
| `full_name` | yes | string or null |  |  |
| `email` | yes | string (email) or null |  |  |
| `phone` | yes | string or null |  |  |
| `phone_verified` | yes | boolean |  |  |
| `avatar_url` | yes | string or null |  |  |
| `is_active` | yes | boolean |  |  |

<a id="model-app__api__v1__schemas__platform__languageresponse"></a>

### app__api__v1__schemas__platform__LanguageResponse

Language reference data response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `code` | yes | string |  |  |
| `name` | yes | string |  |  |

<a id="model-app__api__v1__schemas__platform__profileresponse"></a>

### app__api__v1__schemas__platform__ProfileResponse

Profile response.

| Field | Required | Type | Constraints/default | Description |
| --- | --- | --- | --- | --- |
| `id` | yes | string |  |  |
| `role` | yes | string |  |  |
| `full_name` | yes | string or null |  |  |
| `email` | yes | string or null |  |  |
| `phone` | yes | string or null |  |  |
| `phone_verified` | yes | boolean |  |  |
| `avatar_url` | yes | string or null |  |  |
| `is_active` | yes | boolean |  |  |

## Related behavioral contracts

- [Client workflow handoff](CLIENT_DEVELOPER_HANDOFF.md)
- [Customer details](Customer-App-Backend-API-Document.md)
- [Owner details](Salon-Owner-App-Backend-API-Document.md)
- [Public discovery and QR](PUBLIC_DISCOVERY_AND_BOOKING_CONTRACT.md)
- [Newer checkout/trial/collection behavior](../backend/docs/PRODUCTION_VERIFICATION.md)
- [Payments and provider rules](../backend/docs/PAYMENTS.md)
- [Subscription rules](../backend/docs/SUBSCRIPTIONS.md)
- [Media gateway](../backend/docs/IMAGE_MEDIA.md)
- [Account erasure](../backend/docs/ACCOUNT_DELETION.md)
- [Known audit findings and verification limits](../backend/docs/verification/FULL_API_ARCHITECTURE_AUDIT_2026-10-21.md)

This reference does not certify correctness or security of every implementation. Known audit findings and provider/deployment prerequisites still apply. No test-suite or live-service pass is claimed by documentation generation.
