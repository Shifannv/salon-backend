# Cloudflare R2 media storage

Cloudflare R2 is the backend's media provider. The API does not require or use ImageKit.

## Environment configuration

Configure these values in `backend/.env` for local development and in the deployment platform's secret settings for production:

```env
R2_ACCOUNT_ID=your-cloudflare-account-id
R2_ACCESS_KEY_ID=your-r2-s3-access-key-id
R2_SECRET_ACCESS_KEY=your-r2-s3-secret-access-key
R2_BUCKET=salon-images
R2_PUBLIC_URL=https://media.example.com
```

`R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY` must be the S3 credentials generated for a Cloudflare R2 API token. A Cloudflare global API key, account API token, or token value is not an S3 access-key pair.

The application also accepts the older `R2_ENDPOINT_URL` and `R2_BUCKET_NAME` variable names for compatibility. New environments should use `R2_ACCOUNT_ID` and `R2_BUCKET`.

`R2_PUBLIC_URL` must be the public base URL for the bucket, either an `r2.dev` address or a custom domain. Do not commit `backend/.env`; it is ignored by Git.

## Frontend upload flows

All routes use the `/v1` API prefix and require a Supabase bearer token unless stated otherwise.

### Salon gallery image

1. Call `POST /v1/salons/me/images/upload-url` with `content_type` and `filename`.
2. Upload the raw file bytes to the returned `upload_url` with `PUT` and the same `Content-Type` value.
3. Call `POST /v1/salons/me/images` with the returned `public_url` and the image metadata.

### Staff photo

1. Call `POST /v1/salons/me/staff/{staff_id}/photo-upload-url`.
2. Upload the raw file bytes to `upload_url` with `PUT` and the same content type.
3. Call `PATCH /v1/salons/me/staff/{staff_id}` with `photo_url` set to `public_url`.

### Profile avatar

The preferred direct-upload flow is:

1. Call `POST /v1/profiles/me/avatar-upload-url`.
2. Upload the raw file bytes to `upload_url` with `PUT` and the same content type.
3. Call `PATCH /v1/profiles/me` with `avatar_url` set to `public_url`.

The customer app can also call `POST /v1/customer/profile/avatar` as `multipart/form-data` with a file field named `image`. The backend validates the file, uploads it to R2, and updates the authenticated profile.

Presigned upload URLs expire after 300 seconds. Supported direct-upload content types are JPEG, PNG, WebP, HEIC, and HEIF. The multipart customer-avatar endpoint accepts JPEG, PNG, and WebP and limits the file to 5 MB.

## Deletion and replacement

Deleting a salon image soft-deletes its database row and then attempts to remove the R2 object. Replacing an R2-hosted profile avatar also attempts to remove the previous object. Database state remains consistent if the R2 cleanup request fails.

## QR codes

Owner QR generation is separate from media storage. `GET /v1/salons/me/qr` returns a public PNG URL or an SVG response. The image encodes the absolute walk-in page configured by `WALKIN_BASE_URL`. `PUBLIC_API_BASE_URL` is recommended in production for the returned public QR image URL.

## Troubleshooting

- `401 Unauthorized` from R2 means Cloudflare rejected the configured S3 credential pair. Create an R2 API token with Object Read & Write access to the selected bucket, then copy its Access Key ID and Secret Access Key into the matching variables.
- `403 Forbidden` usually means the credential exists but lacks access to the bucket or operation.
- A failed browser `PUT` can be caused by an R2 bucket CORS policy. Allow the deployed frontend origins, the `PUT` method, and the `Content-Type` header.
- A signature error commonly means the frontend sent a different `Content-Type` from the value used to request the upload URL.
- A working upload with a broken public image URL means `R2_PUBLIC_URL` or the bucket's public access/custom domain is not configured correctly.

Restart the backend after changing environment values so the settings and cached R2 client are recreated.
