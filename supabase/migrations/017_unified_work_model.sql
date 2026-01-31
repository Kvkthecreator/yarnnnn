-- Migration: 017_unified_work_model.sql
-- ADR-017: Unified Work Model
-- Date: 2026-01-31
--
-- Transforms the work system from template-based to unified frequency-based model:
-- - Renames work_tickets → work
-- - Adds frequency column, renames schedule columns
-- - Moves status tracking to work_outputs
-- - Drops is_template and parent_template_id columns

-- =============================================================================
-- PHASE 1: ADD NEW COLUMNS (backward compatible)
-- =============================================================================

-- Add frequency column (defaults to 'once' for existing one-time work)
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS frequency TEXT DEFAULT 'once';

-- Rename schedule_cron to frequency_cron (keep old for now)
-- We'll use a view/alias approach for backward compatibility
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS frequency_cron TEXT;

-- Copy existing schedule_cron values to frequency_cron
UPDATE work_tickets
SET frequency_cron = schedule_cron
WHERE schedule_cron IS NOT NULL;

-- Set frequency based on existing data
UPDATE work_tickets
SET frequency = CASE
    WHEN schedule_cron IS NOT NULL THEN 'recurring'  -- Will display as human-readable
    ELSE 'once'
END;

-- Add timezone column if not exists (rename from schedule_timezone)
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
UPDATE work_tickets
SET timezone = COALESCE(schedule_timezone, 'UTC');

-- Rename schedule_enabled to is_active
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT FALSE;
UPDATE work_tickets
SET is_active = COALESCE(schedule_enabled, FALSE);

-- For one-time work, is_active should be false (no more runs)
UPDATE work_tickets
SET is_active = FALSE
WHERE frequency = 'once' OR schedule_cron IS NULL;

-- Add updated_at column
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Rename schedule_next_run_at to next_run_at
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS next_run_at TIMESTAMPTZ;
UPDATE work_tickets
SET next_run_at = schedule_next_run_at;

-- Rename schedule_last_run_at to last_run_at
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS last_run_at TIMESTAMPTZ;
UPDATE work_tickets
SET last_run_at = schedule_last_run_at;


-- =============================================================================
-- PHASE 2: UPDATE work_outputs FOR STATUS TRACKING
-- =============================================================================

-- Add run_number for recurring work outputs
ALTER TABLE work_outputs ADD COLUMN IF NOT EXISTS run_number INTEGER DEFAULT 1;

-- Add execution status columns
ALTER TABLE work_outputs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE work_outputs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE work_outputs ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Update status column to execution status (pending/running/completed/failed)
-- Note: existing 'delivered' status maps to 'completed'
UPDATE work_outputs
SET status = 'completed'
WHERE status = 'delivered';

-- Backfill run_number for existing outputs (1 for each unique ticket)
WITH numbered AS (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY ticket_id ORDER BY created_at) as rn
    FROM work_outputs
)
UPDATE work_outputs wo
SET run_number = numbered.rn
FROM numbered
WHERE wo.id = numbered.id;


-- =============================================================================
-- PHASE 3: UPDATE FUNCTIONS FOR NEW MODEL
-- =============================================================================

-- Drop old functions that reference is_template
DROP FUNCTION IF EXISTS get_due_work_templates(TIMESTAMPTZ);
DROP FUNCTION IF EXISTS spawn_ticket_from_template(UUID);

-- New function: Get work due for execution
CREATE OR REPLACE FUNCTION get_due_work(check_time TIMESTAMPTZ DEFAULT NOW())
RETURNS TABLE (
    work_id UUID,
    task TEXT,
    agent_type TEXT,
    parameters JSONB,
    project_id UUID,
    user_id UUID,
    frequency_cron TEXT,
    timezone TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        wt.id as work_id,
        wt.task,
        wt.agent_type,
        wt.parameters,
        wt.project_id,
        wt.user_id,
        wt.frequency_cron,
        wt.timezone
    FROM work_tickets wt
    WHERE wt.is_active = true
      AND wt.next_run_at IS NOT NULL
      AND wt.next_run_at <= check_time
      AND wt.frequency_cron IS NOT NULL;
END;
$$;

-- New function: Create output for work execution
CREATE OR REPLACE FUNCTION create_work_output(
    p_work_id UUID,
    p_user_id UUID
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    new_output_id UUID;
    next_run_number INTEGER;
BEGIN
    -- Calculate next run number
    SELECT COALESCE(MAX(run_number), 0) + 1
    INTO next_run_number
    FROM work_outputs
    WHERE ticket_id = p_work_id;

    -- Create output record
    INSERT INTO work_outputs (
        ticket_id,
        user_id,
        run_number,
        status,
        started_at
    ) VALUES (
        p_work_id,
        p_user_id,
        next_run_number,
        'pending',
        NOW()
    )
    RETURNING id INTO new_output_id;

    RETURN new_output_id;
END;
$$;


-- =============================================================================
-- PHASE 4: UPDATE INDEXES
-- =============================================================================

-- Drop old indexes
DROP INDEX IF EXISTS idx_tickets_schedule_due;
DROP INDEX IF EXISTS idx_tickets_parent_template;
DROP INDEX IF EXISTS idx_tickets_user_templates;

-- New indexes for unified model
CREATE INDEX IF NOT EXISTS idx_work_due
    ON work_tickets(next_run_at)
    WHERE is_active = true AND frequency_cron IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_work_user_active
    ON work_tickets(user_id, is_active)
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_work_outputs_work
    ON work_outputs(ticket_id, run_number DESC);


-- =============================================================================
-- PHASE 5: UPDATE TRIGGER FOR updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION update_work_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS work_tickets_updated_at ON work_tickets;
CREATE TRIGGER work_tickets_updated_at
    BEFORE UPDATE ON work_tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_work_updated_at();


-- =============================================================================
-- NOTES FOR FUTURE CLEANUP (Phase 6 - separate migration)
-- =============================================================================
--
-- After verifying the new model works, run a cleanup migration to:
-- 1. DROP COLUMN is_template
-- 2. DROP COLUMN parent_template_id
-- 3. DROP COLUMN schedule_cron (replaced by frequency_cron)
-- 4. DROP COLUMN schedule_timezone (replaced by timezone)
-- 5. DROP COLUMN schedule_enabled (replaced by is_active)
-- 6. DROP COLUMN schedule_next_run_at (replaced by next_run_at)
-- 7. DROP COLUMN schedule_last_run_at (replaced by last_run_at)
-- 8. DROP COLUMN status from work_tickets (now on work_outputs)
-- 9. RENAME TABLE work_tickets TO work
-- 10. RENAME COLUMN work_outputs.ticket_id TO work_id
--
-- These changes are deferred to avoid breaking existing code during transition.
