-- Prepared only. Apply explicitly after review; never at application startup.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='60s';
-- statement --
-- Nullable column without a default: a catalog-only change, no table rewrite.
ALTER TABLE public.bookings ADD COLUMN owner_archived_at timestamptz;
-- statement --
COMMENT ON COLUMN public.bookings.owner_archived_at IS
  'When salon staff hid this finished booking from the workspace list. Status and money are never changed by archiving.';
