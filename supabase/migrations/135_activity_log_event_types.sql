-- Migration 135: Update activity_log event_type check constraint
--
-- Adds task lifecycle event types (ADR-138/141) and removes dead project/signal types.
-- The Python whitelist in activity_log.py was updated but the DB constraint was not,
-- causing task_executed events to be silently rejected.

-- Drop the old constraint
ALTER TABLE activity_log DROP CONSTRAINT IF EXISTS activity_log_event_type_check;

-- Add updated constraint with current event types
ALTER TABLE activity_log ADD CONSTRAINT activity_log_event_type_check CHECK (
    event_type IN (
        -- Task lifecycle (ADR-138/141)
        'task_executed',           -- Task pipeline completed (scheduled or manual)
        'task_created',            -- Task created via TP primitive
        'task_triggered',          -- Task manually triggered (Run Now)
        'task_paused',             -- Task paused via TP primitive
        'task_resumed',            -- Task resumed via TP primitive
        -- Agent lifecycle
        'agent_run',               -- Legacy: pre-ADR-141 execution events (kept for historical rows)
        'agent_approved',
        'agent_rejected',
        'agent_bootstrapped',      -- ADR-110/140: Auto-created or scaffolded agent
        'agent_scheduled',         -- Composer lifecycle action
        -- Platform & sync
        'platform_synced',
        'integration_connected',
        'integration_disconnected',
        'content_cleanup',
        -- Sessions & memory
        'chat_session',
        'memory_written',
        'session_summary_written',
        -- System
        'scheduler_heartbeat',
        'composer_heartbeat'
    )
);
