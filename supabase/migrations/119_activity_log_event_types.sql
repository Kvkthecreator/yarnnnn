-- Migration 119: Add ADR-117 Phase 3 event types to activity_log CHECK constraint
--
-- Adds 5 new event types for project activity + duty promotion:
--   project_heartbeat, project_assembled, project_escalated,
--   project_contributor_advanced, duty_promoted

ALTER TABLE activity_log DROP CONSTRAINT IF EXISTS activity_log_event_type_check;

ALTER TABLE activity_log ADD CONSTRAINT activity_log_event_type_check
    CHECK (event_type = ANY (ARRAY[
        'agent_run', 'agent_approved', 'agent_rejected',
        'agent_scheduled', 'agent_generated',
        'memory_written', 'platform_synced',
        'integration_connected', 'integration_disconnected',
        'chat_session', 'signal_processed',
        'scheduler_heartbeat', 'content_cleanup',
        'session_summary_written', 'pattern_detected',
        'conversation_analyzed', 'agent_bootstrapped',
        'composer_heartbeat',
        -- ADR-117 Phase 3: Project activity + duty promotion
        'project_heartbeat',
        'project_assembled',
        'project_escalated',
        'project_contributor_advanced',
        'duty_promoted'
    ]));
