-- Prepared only. Explicit reviewed migration, never API startup.
-- Optional end date for an admin-set salon offer. NULL keeps today's behaviour: the offer stays
-- until an admin clears it. After this moment the plan list and checkout use the normal price again.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='30s';
-- statement --
ALTER TABLE public.salon_plan_prices ADD COLUMN IF NOT EXISTS valid_until timestamptz;
