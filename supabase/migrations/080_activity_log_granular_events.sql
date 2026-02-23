-- 080: Add granular activity_log event types for background processing visibility
--
-- New event types:
--   deliverable_generated  - Deliverable content actually generated (not just scheduled)
--   content_cleanup        - Expired platform_content cleaned up
--   session_summary_written - Session compaction summaries generated
--   pattern_detected       - Activity pattern detection completed
--   conversation_analyzed  - Conversation analysis + suggestions created

ALTER TABLE activity_log DROP CONSTRAINT IF EXISTS activity_log_event_type_check;

ALTER TABLE activity_log ADD CONSTRAINT activity_log_event_type_check
  CHECK (event_type = ANY (ARRAY[
    'deliverable_run',
    'deliverable_approved',
    'deliverable_rejected',
    'deliverable_scheduled',
    'deliverable_generated',
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
  ]));
