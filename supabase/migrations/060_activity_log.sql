-- Migration: 060_activity_log.sql
-- ADR-063: Activity Log — Four-Layer Model
--
-- Introduces activity_log as the Activity layer in the four-layer model:
--   Memory (user_context) / Activity (activity_log) / Context (filesystem_items) / Work (deliverables)
--
-- Purpose: append-only system provenance log recording what YARNNN has done.
-- Written by: deliverable execution pipeline, platform sync worker, chat pipeline, TP memory tools.
-- Read by: working_memory.py (recent 10 events injected into TP session prompt).
--
-- event_type values:
--   'deliverable_run'   - a deliverable version was generated
--   'memory_written'    - TP wrote a memory entry (create_memory / update_memory)
--   'platform_synced'   - platform sync batch completed for a resource
--   'chat_session'      - a chat session ended with a notable summary

CREATE TABLE activity_log (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    event_type  TEXT        NOT NULL CHECK (event_type IN (
                                'deliverable_run',
                                'memory_written',
                                'platform_synced',
                                'chat_session'
                            )),
    event_ref   UUID,                       -- FK reference to related record (version_id, session_id, etc.)
    summary     TEXT        NOT NULL,       -- Human-readable one-liner for working memory injection
    metadata    JSONB,                      -- Event-specific structured detail
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: users can only read their own activity
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own activity"
    ON activity_log FOR SELECT
    USING (auth.uid() = user_id);

-- No INSERT/UPDATE/DELETE policies for users — log is service-role only (append-only)
-- Application code uses service role client to write events

-- Performance: recent activity is the primary query pattern
CREATE INDEX activity_log_user_recent
    ON activity_log (user_id, created_at DESC);

-- Secondary: filter by event type for specific history views
CREATE INDEX activity_log_event_type
    ON activity_log (user_id, event_type, created_at DESC);
