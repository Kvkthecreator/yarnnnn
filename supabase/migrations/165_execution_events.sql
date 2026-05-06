-- Migration 165: execution_events table — ADR-250 Phase 2
-- Authoritative structured record of every invocation attempt.
-- One row per invocation, always written regardless of outcome.
-- Replaces the fragmented pattern of partial data in agent_runs.metadata.

CREATE TABLE IF NOT EXISTS execution_events (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    slug                text NOT NULL,
    shape               text NOT NULL,        -- deliverable | accumulation | action | maintenance
    trigger_type        text NOT NULL,        -- scheduled | manual | back_office
    status              text NOT NULL,        -- success | failed | skipped
    error_reason        text,                 -- balance_exhausted | capability_unavailable | spend_ceiling | exception | empty_draft | NULL
    error_detail        text,                 -- exception message, max 2000 chars
    tool_rounds         int,
    input_tokens        bigint,
    output_tokens       bigint,
    cache_read_tokens   bigint,
    cache_create_tokens bigint,
    cost_usd            numeric(10,6),        -- cache-inclusive accurate cost (not legacy cache-agnostic)
    duration_ms         int,
    agent_run_id        uuid REFERENCES agent_runs(id) ON DELETE SET NULL,  -- NULL for failures
    created_at          timestamptz NOT NULL DEFAULT now()
);

-- Query patterns: per-user cost over time, per-task cost, failure analysis, runaway detection
CREATE INDEX idx_execution_events_user_date ON execution_events (user_id, created_at DESC);
CREATE INDEX idx_execution_events_slug      ON execution_events (user_id, slug, created_at DESC);
CREATE INDEX idx_execution_events_status    ON execution_events (status, created_at DESC);

-- RLS: users see only their own rows; service key bypasses for scheduler writes
ALTER TABLE execution_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own execution events"
    ON execution_events FOR SELECT
    USING (auth.uid() = user_id);

-- Writes come from the scheduler (service key) — no user INSERT policy needed
