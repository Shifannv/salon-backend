-- PREPARED ONLY. Not executed. Alembic owns the transaction.
-- Both arbitrary text fields are scrubbed to NULL by account deletion, not retained
-- as legal/audit identifiers. No migration-time data erasure or backfill.
SET LOCAL lock_timeout = '5s';
-- statement --
SET LOCAL statement_timeout = '60s';
-- statement --
DO $review$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'bookings'
          AND column_name IN ('cancellation_reason_code', 'cancellation_reason_text')
          AND (data_type <> 'text' OR udt_schema <> 'pg_catalog' OR udt_name <> 'text'
               OR is_nullable <> 'YES' OR column_default IS NOT NULL
               OR is_generated <> 'NEVER' OR is_identity <> 'NO'
               OR domain_name IS NOT NULL OR collation_name IS NOT NULL)
    ) THEN
        RAISE EXCEPTION 'Cancellation compatibility definition differs; abort review';
    END IF;
END
$review$;
-- statement --
ALTER TABLE public.bookings ADD COLUMN IF NOT EXISTS cancellation_reason_code text;
-- statement --
ALTER TABLE public.bookings ADD COLUMN IF NOT EXISTS cancellation_reason_text text;
