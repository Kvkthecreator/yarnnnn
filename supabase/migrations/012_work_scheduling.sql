-- Migration: 012_work_scheduling.sql
-- ADR-009 Phase 3: Work Scheduling
-- Date: 2025-01-30
--
-- Adds scheduling capabilities to work_tickets:
-- - Templates (is_template=true) define recurring work patterns
-- - Templates spawn regular tickets when schedule is due
-- - Cron job processes due schedules every 5 minutes

-- =============================================================================
-- 1. ADD SCHEDULING COLUMNS TO WORK_TICKETS
-- =============================================================================

-- Template flag: templates are not executed, they spawn child tickets
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS is_template BOOLEAN DEFAULT false;

-- Scheduling fields (only used when is_template=true)
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS schedule_cron TEXT;
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS schedule_timezone TEXT DEFAULT 'UTC';
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS schedule_enabled BOOLEAN DEFAULT true;
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS schedule_next_run_at TIMESTAMPTZ;
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS schedule_last_run_at TIMESTAMPTZ;

-- Parent reference: links spawned tickets back to their template
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS parent_template_id UUID REFERENCES work_tickets(id) ON DELETE SET NULL;

-- User ID for direct ownership (simplifies RLS and enables user-scoped templates)
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);


-- =============================================================================
-- 2. INDEXES FOR SCHEDULING QUERIES
-- =============================================================================

-- Find templates due for execution
CREATE INDEX IF NOT EXISTS idx_tickets_schedule_due
    ON work_tickets(schedule_next_run_at)
    WHERE is_template = true AND schedule_enabled = true;

-- Find tickets by template
CREATE INDEX IF NOT EXISTS idx_tickets_parent_template
    ON work_tickets(parent_template_id)
    WHERE parent_template_id IS NOT NULL;

-- Find templates by user
CREATE INDEX IF NOT EXISTS idx_tickets_user_templates
    ON work_tickets(user_id, is_template)
    WHERE is_template = true;


-- =============================================================================
-- 3. BACKFILL USER_ID FROM EXISTING TICKETS
-- =============================================================================

-- Populate user_id from project->workspace->owner chain
UPDATE work_tickets wt
SET user_id = (
    SELECT w.owner_id
    FROM projects p
    JOIN workspaces w ON p.workspace_id = w.id
    WHERE p.id = wt.project_id
)
WHERE wt.user_id IS NULL;


-- =============================================================================
-- 4. FUNCTION: Calculate next run time from cron expression
-- =============================================================================

-- This is a simplified cron parser for common patterns.
-- Supports: */N (every N), specific values, and * (any)
-- For complex cron, the Python scheduler will handle calculation

CREATE OR REPLACE FUNCTION calculate_next_cron_run(
    cron_expr TEXT,
    timezone TEXT,
    from_time TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TIMESTAMPTZ
LANGUAGE plpgsql
AS $$
DECLARE
    parts TEXT[];
    minute_part TEXT;
    hour_part TEXT;
    next_run TIMESTAMPTZ;
    local_time TIMESTAMP;
    target_minute INT;
    target_hour INT;
BEGIN
    -- Parse cron expression (minute hour day month weekday)
    parts := string_to_array(cron_expr, ' ');
    IF array_length(parts, 1) != 5 THEN
        RETURN NULL; -- Invalid cron
    END IF;

    minute_part := parts[1];
    hour_part := parts[2];

    -- Convert to local time
    local_time := from_time AT TIME ZONE timezone;

    -- Handle simple cases: */N for minutes and specific hours
    -- For complex patterns, return NULL and let Python handle it

    IF minute_part ~ '^[0-9]+$' AND hour_part ~ '^[0-9]+$' THEN
        -- Specific minute and hour (e.g., "0 9" = 9:00 AM daily)
        target_minute := minute_part::INT;
        target_hour := hour_part::INT;

        -- Start with today at target time
        next_run := (date_trunc('day', local_time) +
                     (target_hour || ' hours')::INTERVAL +
                     (target_minute || ' minutes')::INTERVAL) AT TIME ZONE timezone;

        -- If that time has passed today, move to tomorrow
        IF next_run <= from_time THEN
            next_run := next_run + INTERVAL '1 day';
        END IF;

        RETURN next_run;

    ELSIF minute_part ~ '^\*/[0-9]+$' AND hour_part = '*' THEN
        -- Every N minutes (e.g., "*/30 *" = every 30 minutes)
        target_minute := substring(minute_part from 3)::INT;

        -- Round up to next interval
        next_run := date_trunc('hour', from_time) +
                    (((EXTRACT(MINUTE FROM from_time)::INT / target_minute) + 1) * target_minute || ' minutes')::INTERVAL;

        RETURN next_run;

    ELSIF minute_part = '0' AND hour_part ~ '^\*/[0-9]+$' THEN
        -- Every N hours (e.g., "0 */6" = every 6 hours at minute 0)
        target_hour := substring(hour_part from 3)::INT;

        -- Round up to next interval
        next_run := date_trunc('day', from_time) +
                    (((EXTRACT(HOUR FROM from_time)::INT / target_hour) + 1) * target_hour || ' hours')::INTERVAL;

        RETURN next_run;
    END IF;

    -- Complex pattern - return NULL, Python scheduler will calculate
    RETURN NULL;
END;
$$;


-- =============================================================================
-- 5. FUNCTION: Get templates due for execution
-- =============================================================================

CREATE OR REPLACE FUNCTION get_due_work_templates(check_time TIMESTAMPTZ DEFAULT NOW())
RETURNS TABLE (
    template_id UUID,
    task TEXT,
    agent_type TEXT,
    parameters JSONB,
    project_id UUID,
    user_id UUID,
    schedule_cron TEXT,
    schedule_timezone TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        wt.id as template_id,
        wt.task,
        wt.agent_type,
        wt.parameters,
        wt.project_id,
        wt.user_id,
        wt.schedule_cron,
        wt.schedule_timezone
    FROM work_tickets wt
    WHERE wt.is_template = true
      AND wt.schedule_enabled = true
      AND wt.schedule_next_run_at IS NOT NULL
      AND wt.schedule_next_run_at <= check_time;
END;
$$;


-- =============================================================================
-- 6. FUNCTION: Spawn ticket from template
-- =============================================================================

CREATE OR REPLACE FUNCTION spawn_ticket_from_template(template_id UUID)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    template work_tickets%ROWTYPE;
    new_ticket_id UUID;
    next_run TIMESTAMPTZ;
BEGIN
    -- Get template
    SELECT * INTO template FROM work_tickets WHERE id = template_id AND is_template = true;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Template not found: %', template_id;
    END IF;

    -- Create new ticket from template
    INSERT INTO work_tickets (
        task,
        agent_type,
        status,
        parameters,
        project_id,
        user_id,
        parent_template_id,
        is_template
    ) VALUES (
        template.task,
        template.agent_type,
        'pending',
        template.parameters,
        template.project_id,
        template.user_id,
        template_id,
        false
    )
    RETURNING id INTO new_ticket_id;

    -- Update template: last run and calculate next run
    next_run := calculate_next_cron_run(
        template.schedule_cron,
        template.schedule_timezone,
        NOW()
    );

    UPDATE work_tickets
    SET
        schedule_last_run_at = NOW(),
        schedule_next_run_at = next_run
    WHERE id = template_id;

    RETURN new_ticket_id;
END;
$$;


-- =============================================================================
-- 7. UPDATE RLS POLICIES
-- =============================================================================

-- Add policy for user-scoped template access
CREATE POLICY "Users can manage their own templates"
    ON work_tickets FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());
