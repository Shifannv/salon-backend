-- statement --
-- audience: which app a notification belongs to.
-- NULL means legacy / unknown: shown in both apps until backfilled.
ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS audience varchar(16)
        CHECK (audience IN ('owner', 'customer'));

-- statement --
-- Partial index: fast per-user queries filtered by audience.
CREATE INDEX IF NOT EXISTS notifications_audience_user
    ON notifications (user_id, audience)
    WHERE deleted_at IS NULL;

-- statement --
-- app: which client registered this push token.
-- NULL means registered before this migration: delivered to both apps for now.
ALTER TABLE device_tokens
    ADD COLUMN IF NOT EXISTS app varchar(16)
        CHECK (app IN ('owner', 'customer'));
