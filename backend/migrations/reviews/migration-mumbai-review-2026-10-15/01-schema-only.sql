-- REVIEW ONLY / NOT EXECUTED / NOT AN ALEMBIC REVISION.
-- Destination: wqjlgpnbiapcrlkxumcp, ap-south-1 ONLY.
-- Independently verify the project before connection; shared pooler host is not identity.
-- Requires separate user approval. No data/history/stamp/deployment operations.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
SET LOCAL search_path = pg_catalog, public;

-- Adopt both legacy compatibility columns in a FUTURE expected head; never delete them.
-- Release gate: erasure classification/tests must cover both fields before a real
-- Alembic revision is created. This SQL does not implement erasure or authorize writes.
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
        RAISE EXCEPTION 'Compatibility-column definition differs; abort';
    END IF;
END
$review$;
ALTER TABLE public.bookings ADD COLUMN IF NOT EXISTS cancellation_reason_code text;
ALTER TABLE public.bookings ADD COLUMN IF NOT EXISTS cancellation_reason_text text;
-- Current Mumbai already contains both definitions: expected destination delta is zero.
-- No constraint, index, function body, trigger, grant, RLS policy or data change.
COMMIT;
