-- Migration 104: Update activity_log CHECK constraint for agent terminology
--
-- The ADR-103 rename (deliverable → agent) updated Python VALID_EVENT_TYPES
-- but missed the DB CHECK constraint, which still has deliverable_* values.
-- This causes INSERT failures when the scheduler writes agent_run, agent_scheduled, etc.

-- 1. Drop old constraint
ALTER TABLE activity_log DROP CONSTRAINT IF EXISTS activity_log_event_type_check;

-- 2. Backfill any existing rows with old event_type names
UPDATE activity_log SET event_type = 'agent_run' WHERE event_type = 'deliverable_run';
UPDATE activity_log SET event_type = 'agent_approved' WHERE event_type = 'deliverable_approved';
UPDATE activity_log SET event_type = 'agent_rejected' WHERE event_type = 'deliverable_rejected';
UPDATE activity_log SET event_type = 'agent_scheduled' WHERE event_type = 'deliverable_scheduled';
UPDATE activity_log SET event_type = 'agent_generated' WHERE event_type = 'deliverable_generated';

-- 3. Add updated constraint with agent_* names
ALTER TABLE activity_log ADD CONSTRAINT activity_log_event_type_check
  CHECK (event_type IN (
    'agent_run',
    'agent_approved',
    'agent_rejected',
    'agent_scheduled',
    'agent_generated',
    'memory_written',
    'platform_synced',
    'integration_connected',
    'integration_disconnected',
    'chat_session',
    'signal_processed',
    'scheduler_heartbeat',
    'content_cleanup',
    'session_summary_written',
    'pattern_detected',
    'conversation_analyzed'
  ));
