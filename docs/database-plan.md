# Database plan

Supabase Postgres stores profiles, salons, catalog data, staff, bookings,
notifications, device tokens, blocked slots, holidays, images, and salon reports.

The schema starts with `backend/migrations/001_supabase_schema.sql`. Alembic revision
`0001_baseline` applies that file, and later revisions apply required incremental
changes. Existing migration history must not be deleted or rewritten after deployment.

Rules:

- Apply schema changes only through reviewed Alembic revisions.
- Create bookings only through the Postgres `create_booking` function.
- Read availability only through `get_available_slots`.
- Use `is_active` for soft deletion where the schema supports it.
- Keep RLS enabled and mirror its access rules in application use cases.
- Set transaction-local `request.jwt.claims` for authenticated database work so audit
  triggers receive the verified actor ID.
- Never expose raw database errors, SQL, or constraint names through HTTP responses.

See [the migration guide](../backend/migrations/README.md) for safe commands.
