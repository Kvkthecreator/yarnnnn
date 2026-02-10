-- Migration: 036_background_work_execution.sql
-- ADR-039: Background Work Agents
--
-- Adds support for background work execution with progress tracking.
-- Enables long-running tasks without HTTP timeout issues.

-- =============================================================================
-- 1. Add columns to work_tickets for background execution
-- =============================================================================

-- Execution mode: 'foreground' (default, blocks) or 'background' (queued)
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS
    execution_mode TEXT DEFAULT 'foreground';

-- Progress tracking for background jobs
-- Schema: {stage: string, percent: int, message: string, updated_at: string}
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS
    progress JSONB DEFAULT '{}';

-- When the job was added to the queue
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS
    queued_at TIMESTAMPTZ;

-- External job ID from RQ (Redis Queue)
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS
    job_id TEXT;

-- Add check constraint for execution_mode
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'work_tickets_execution_mode_check'
    ) THEN
        ALTER TABLE work_tickets
        ADD CONSTRAINT work_tickets_execution_mode_check
        CHECK (execution_mode IN ('foreground', 'background'));
    END IF;
END $$;

-- =============================================================================
-- 2. Create execution log table for debugging
-- =============================================================================

CREATE TABLE IF NOT EXISTS work_execution_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES work_tickets(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    stage TEXT NOT NULL,  -- 'queued', 'started', 'progress', 'tool_call', 'completed', 'failed'
    message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Index for efficient log queries
CREATE INDEX IF NOT EXISTS idx_work_execution_log_ticket_id
    ON work_execution_log(ticket_id);
CREATE INDEX IF NOT EXISTS idx_work_execution_log_timestamp
    ON work_execution_log(ticket_id, timestamp DESC);

-- =============================================================================
-- 3. RLS Policies for work_execution_log
-- =============================================================================

ALTER TABLE work_execution_log ENABLE ROW LEVEL SECURITY;

-- Users can view logs for their own work tickets
CREATE POLICY "Users can view execution logs for own tickets"
    ON work_execution_log
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM work_tickets wt
            WHERE wt.id = work_execution_log.ticket_id
            AND wt.user_id = auth.uid()
        )
    );

-- Service role can insert/update logs (workers use service key)
CREATE POLICY "Service can manage execution logs"
    ON work_execution_log
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- =============================================================================
-- 4. Helper function to get background work status
-- =============================================================================

CREATE OR REPLACE FUNCTION get_work_status(p_ticket_id UUID)
RETURNS TABLE (
    ticket_id UUID,
    status TEXT,
    execution_mode TEXT,
    progress JSONB,
    queued_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    recent_logs JSONB
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        wt.id AS ticket_id,
        wt.status,
        wt.execution_mode,
        wt.progress,
        wt.queued_at,
        wt.started_at,
        wt.completed_at,
        wt.error_message,
        (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'stage', wel.stage,
                    'message', wel.message,
                    'timestamp', wel.timestamp
                ) ORDER BY wel.timestamp DESC
            )
            FROM work_execution_log wel
            WHERE wel.ticket_id = wt.id
            LIMIT 10
        ) AS recent_logs
    FROM work_tickets wt
    WHERE wt.id = p_ticket_id;
END;
$$;

-- =============================================================================
-- 5. Index for querying background jobs
-- =============================================================================

-- Index for finding pending background jobs (used by worker)
CREATE INDEX IF NOT EXISTS idx_work_tickets_background_pending
    ON work_tickets(execution_mode, status, queued_at)
    WHERE execution_mode = 'background' AND status IN ('pending', 'queued');

-- =============================================================================
-- 6. Add 'queued' to status enum (if not exists)
-- =============================================================================

-- Note: work_tickets.status is TEXT with check constraint
-- We need to update the constraint to include 'queued'
DO $$
BEGIN
    -- Drop old constraint if exists
    ALTER TABLE work_tickets DROP CONSTRAINT IF EXISTS work_tickets_status_check;

    -- Add updated constraint with 'queued' status
    ALTER TABLE work_tickets
    ADD CONSTRAINT work_tickets_status_check
    CHECK (status IN ('pending', 'queued', 'running', 'completed', 'failed', 'cancelled'));
EXCEPTION
    WHEN others THEN
        -- Constraint might not exist or have different name, that's ok
        RAISE NOTICE 'Could not update status constraint: %', SQLERRM;
END $$;

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON COLUMN work_tickets.execution_mode IS
    'foreground: synchronous execution, background: queued for worker';

COMMENT ON COLUMN work_tickets.progress IS
    'Progress tracking for background jobs: {stage, percent, message, updated_at}';

COMMENT ON COLUMN work_tickets.queued_at IS
    'When the job was added to the background queue';

COMMENT ON COLUMN work_tickets.job_id IS
    'External job ID from Redis Queue (RQ)';

COMMENT ON TABLE work_execution_log IS
    'Execution log for debugging background work (ADR-039)';
