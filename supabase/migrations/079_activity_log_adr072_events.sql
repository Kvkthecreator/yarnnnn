-- Migration: 079_activity_log_adr072_events.sql
-- Extends activity_log event_type CHECK constraint to include ADR-072 system state events.
--
-- New event types:
--   'signal_processed'       - signal extraction reasoned over platform content
--   'deliverable_scheduled'  - deliverable queued for execution
--   'scheduler_heartbeat'    - scheduler execution cycle completed

-- Drop the old constraint and add the extended one
ALTER TABLE activity_log
    DROP CONSTRAINT IF EXISTS activity_log_event_type_check;

ALTER TABLE activity_log
    ADD CONSTRAINT activity_log_event_type_check
    CHECK (event_type IN (
        'deliverable_run',
        'deliverable_approved',
        'deliverable_rejected',
        'deliverable_scheduled',
        'memory_written',
        'platform_synced',
        'integration_connected',
        'integration_disconnected',
        'chat_session',
        'signal_processed',
        'scheduler_heartbeat'
    ));
