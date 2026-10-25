-- Prepared only. Deploy compatible readers/writers before this explicit step.
-- Fail rather than waiting on a busy salon table or cascading into other objects.
SET LOCAL lock_timeout = '5s';
-- statement --
SET LOCAL statement_timeout = '30s';
-- statement --
ALTER TABLE public.salons DROP COLUMN IF EXISTS category RESTRICT;
