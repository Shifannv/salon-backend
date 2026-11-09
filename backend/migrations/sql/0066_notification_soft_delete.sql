-- Prepared only. Apply explicitly after review; never at application startup.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='60s';
-- statement --
-- Nullable column without a default: a catalog-only change, no table rewrite.
ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS deleted_at timestamptz;
-- statement --
COMMENT ON COLUMN public.notifications.deleted_at IS
  'When the recipient dismissed this notification. Every read path ignores rows where this is set; the retention job purges them.';
-- statement --
-- Serves the retention purge of dismissed rows.
CREATE INDEX IF NOT EXISTS idx_notifications_deleted_at
  ON public.notifications (deleted_at) WHERE deleted_at IS NOT NULL;
-- statement --
-- Serves the retention purge by age; idx_notifications_user starts with user_id and cannot.
CREATE INDEX IF NOT EXISTS idx_notifications_created_at
  ON public.notifications (created_at);
