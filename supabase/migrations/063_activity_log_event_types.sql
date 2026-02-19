-- Migration: 063_activity_log_event_types.sql
-- Extends activity_log event_type CHECK constraint to include integration lifecycle
-- and deliverable review events.
--
-- New event types:
--   'integration_connected'    - user connected a platform (OAuth callback success)
--   'integration_disconnected' - user disconnected a platform
--   'deliverable_approved'     - user approved a deliverable version
--   'deliverable_rejected'     - user rejected a deliverable version

-- Drop the old constraint and add the extended one
ALTER TABLE activity_log
    DROP CONSTRAINT IF EXISTS activity_log_event_type_check;

ALTER TABLE activity_log
    ADD CONSTRAINT activity_log_event_type_check
    CHECK (event_type IN (
        'deliverable_run',
        'memory_written',
        'platform_synced',
        'chat_session',
        'integration_connected',
        'integration_disconnected',
        'deliverable_approved',
        'deliverable_rejected'
    ));
