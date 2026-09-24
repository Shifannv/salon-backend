# Frontend integration

Frontend applications use an environment-specific API base URL and send JSON unless an
endpoint documents multipart upload.

Protected requests include the Supabase access token:

```http
Authorization: Bearer <access-token>
```

The backend verifies the token signature and resolves its `sub` against `profiles`.
Clients must not rely on role claims embedded in the JWT.

Useful entry points:

- `GET /health` for process health
- `GET /health/db` for database health
- `/docs` for the current OpenAPI/Swagger contract
- `/v1/auth/*` for session and actor operations
- `/v1/salons*` and `/v1/availability` for public discovery
- `/v1/bookings*` for authenticated booking operations
- `/v1/walkin/*` for the QR flow

Clients should handle `401`, `403`, `404`, `409`, and validation errors explicitly.
On a booking conflict, refresh availability before asking the user to choose another
slot.

Never place the Supabase service-role key, database URL, R2 secret, or Firebase service
account in a frontend environment.
