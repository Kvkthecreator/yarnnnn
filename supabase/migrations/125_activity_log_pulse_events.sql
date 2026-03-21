-- Migration 125: Add missing activity_log event types
--
-- Multiple ADRs introduced event types that were never added to the CHECK constraint:
-- - agent_pulsed (ADR-126: pulse decisions)
-- - pm_pulsed (ADR-120: PM heartbeat pulse)
-- - project_scaffolded (ADR-122: project bootstrap)
-- - project_contributor_steered (ADR-121: PM steering briefs)
-- - project_quality_assessed (ADR-121: PM quality assessment)
-- - project_file_triaged (ADR-127: PM file triage)
--
-- These events were silently dropped due to the CHECK constraint + bare except: pass

ALTER TABLE activity_log DROP CONSTRAINT IF EXISTS activity_log_event_type_check;

ALTER TABLE activity_log ADD CONSTRAINT activity_log_event_type_check CHECK (
  event_type = ANY (ARRAY[
    -- Core agent lifecycle
    'agent_run',
    'agent_approved',
    'agent_rejected',
    'agent_scheduled',
    'agent_generated',
    'agent_bootstrapped',
    -- Pulse (ADR-126)
    'agent_pulsed',
    'pm_pulsed',
    -- Memory & content
    'memory_written',
    'platform_synced',
    'content_cleanup',
    'session_summary_written',
    -- Integrations
    'integration_connected',
    'integration_disconnected',
    -- Analysis
    'chat_session',
    'signal_processed',
    'pattern_detected',
    'conversation_analyzed',
    -- Scheduler & Composer
    'scheduler_heartbeat',
    'composer_heartbeat',
    'duty_promoted',
    -- Projects (ADR-120/121/122/127)
    'project_heartbeat',
    'project_assembled',
    'project_escalated',
    'project_contributor_advanced',
    'project_scaffolded',
    'project_contributor_steered',
    'project_quality_assessed',
    'project_file_triaged'
  ])
);
