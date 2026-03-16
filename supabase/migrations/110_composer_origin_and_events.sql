-- ADR-111: Add 'composer' origin + 'composer_heartbeat' activity event type
-- Composer creates/adjusts agents via Heartbeat lifecycle assessment

ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_origin_check;
ALTER TABLE agents ADD CONSTRAINT agents_origin_check
  CHECK (origin IN ('user_configured', 'analyst_suggested', 'signal_emergent', 'coordinator_created', 'system_bootstrap', 'composer'));

ALTER TABLE activity_log DROP CONSTRAINT IF EXISTS activity_log_event_type_check;
ALTER TABLE activity_log ADD CONSTRAINT activity_log_event_type_check
  CHECK (event_type IN (
    'agent_run', 'agent_approved', 'agent_rejected', 'agent_scheduled',
    'agent_generated', 'memory_written', 'platform_synced',
    'integration_connected', 'integration_disconnected', 'chat_session',
    'signal_processed', 'scheduler_heartbeat', 'content_cleanup',
    'session_summary_written', 'pattern_detected', 'conversation_analyzed',
    'agent_bootstrapped', 'composer_heartbeat'
  ));
