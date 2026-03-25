-- ADR-138: Clean Slate + Tasks Schema
-- Phase 1: Wipe all test data, create tasks table, simplify agents table
-- This is a DESTRUCTIVE migration — only valid pre-launch with test data only.

-- ============================================================
-- Step 1: Wipe all test data (order matters for FK constraints)
-- ============================================================

-- Child tables first
TRUNCATE session_messages CASCADE;
TRUNCATE chat_sessions CASCADE;
TRUNCATE agent_runs CASCADE;
TRUNCATE agent_context_log CASCADE;
TRUNCATE activity_log CASCADE;
TRUNCATE render_usage CASCADE;
TRUNCATE workspace_files CASCADE;

-- Agent-dependent tables
TRUNCATE agents CASCADE;

-- Project-dependent tables
TRUNCATE project_resources CASCADE;
TRUNCATE integration_sync_config CASCADE;

-- Projects themselves
TRUNCATE projects CASCADE;

-- ============================================================
-- Step 2: Drop project-related FK constraints and columns
-- ============================================================

-- Drop FKs referencing projects
ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_project_id_fkey;
ALTER TABLE chat_sessions DROP CONSTRAINT IF EXISTS chat_sessions_project_id_fkey;
ALTER TABLE integration_sync_config DROP CONSTRAINT IF EXISTS integration_sync_config_project_id_fkey;
ALTER TABLE project_resources DROP CONSTRAINT IF EXISTS project_resources_project_id_fkey;

-- Drop project_id columns
ALTER TABLE agents DROP COLUMN IF EXISTS project_id;
ALTER TABLE chat_sessions DROP COLUMN IF EXISTS project_id;

-- Drop project_slug from chat_sessions (ADR-125, no longer needed)
DROP INDEX IF EXISTS idx_chat_sessions_project_slug;
ALTER TABLE chat_sessions DROP COLUMN IF EXISTS project_slug;

-- Drop thread_agent_id from session_messages (project meeting room threads, no longer needed)
ALTER TABLE session_messages DROP CONSTRAINT IF EXISTS session_messages_thread_agent_id_fkey;
DROP INDEX IF EXISTS idx_session_messages_thread;
ALTER TABLE session_messages DROP COLUMN IF EXISTS thread_agent_id;

-- Drop project-related indexes on chat_sessions
DROP INDEX IF EXISTS idx_chat_sessions_project;

-- ============================================================
-- Step 3: Simplify agents table — remove scheduling (moves to tasks)
-- ============================================================

-- Drop scheduling columns that move to tasks table
ALTER TABLE agents DROP COLUMN IF EXISTS schedule;
ALTER TABLE agents DROP COLUMN IF EXISTS next_pulse_at;
ALTER TABLE agents DROP COLUMN IF EXISTS destination;
ALTER TABLE agents DROP COLUMN IF EXISTS last_run_at;

-- Drop deprecated/unused columns
ALTER TABLE agents DROP COLUMN IF EXISTS duties;
ALTER TABLE agents DROP COLUMN IF EXISTS trigger_type;
ALTER TABLE agents DROP COLUMN IF EXISTS trigger_config;
ALTER TABLE agents DROP COLUMN IF EXISTS last_triggered_at;
ALTER TABLE agents DROP COLUMN IF EXISTS sources;
ALTER TABLE agents DROP COLUMN IF EXISTS recipient_context;
ALTER TABLE agents DROP COLUMN IF EXISTS description;

-- Drop indexes that reference removed columns
DROP INDEX IF EXISTS idx_agents_next_pulse;
DROP INDEX IF EXISTS idx_agents_destination_platform;
DROP INDEX IF EXISTS idx_agents_project;

-- Update role CHECK: remove pm, add archetypes (keep legacy for migration mapping in code)
ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_role_check;
ALTER TABLE agents ADD CONSTRAINT agents_role_check CHECK (
  role IN (
    -- v3 archetypes (ADR-138)
    'monitor', 'researcher', 'producer', 'operator',
    -- legacy v2 (mapped in code via LEGACY_ROLE_MAP)
    'briefer', 'drafter', 'analyst', 'writer', 'planner', 'scout',
    -- legacy v1
    'digest', 'prepare', 'synthesize', 'research', 'act', 'custom'
  )
);

-- Update mode CHECK: simplify (remove proactive/coordinator, keep recurring/goal/reactive)
ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_mode_check;
ALTER TABLE agents ADD CONSTRAINT agents_mode_check CHECK (
  mode IN ('recurring', 'goal', 'reactive')
);

-- ============================================================
-- Step 4: Create tasks table (thin scheduling index)
-- ============================================================

CREATE TABLE IF NOT EXISTS tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  slug TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  schedule TEXT,             -- cron expression or human-readable cadence
  next_run_at TIMESTAMPTZ,
  last_run_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT tasks_status_check CHECK (status IN ('active', 'paused', 'completed', 'archived')),
  CONSTRAINT tasks_user_slug_unique UNIQUE (user_id, slug)
);

-- Indexes for scheduler queries
CREATE INDEX idx_tasks_next_run ON tasks (next_run_at) WHERE status = 'active';
CREATE INDEX idx_tasks_user ON tasks (user_id);

-- Updated_at trigger (reuse existing function)
CREATE TRIGGER update_tasks_updated_at
  BEFORE UPDATE ON tasks
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- Step 5: Update chat_sessions indexes for simplified session model
-- ============================================================

-- Recreate indexes without project references
DROP INDEX IF EXISTS idx_chat_sessions_active;
DROP INDEX IF EXISTS idx_chat_sessions_daily_simple;
DROP INDEX IF EXISTS idx_chat_sessions_inactivity;

CREATE INDEX idx_chat_sessions_active
  ON chat_sessions (user_id, session_type, status)
  WHERE status = 'active';

CREATE INDEX idx_chat_sessions_inactivity
  ON chat_sessions (user_id, session_type, status, updated_at DESC)
  WHERE status = 'active';

-- ============================================================
-- Step 6: Clean up — drop project_resources and projects tables
-- ============================================================

DROP TABLE IF EXISTS project_resources CASCADE;
DROP TABLE IF EXISTS projects CASCADE;

-- ============================================================
-- Step 7: Update RPC function get_due_pulse_agents if it references removed columns
-- ============================================================

-- Drop the old function (it queries next_pulse_at which no longer exists on agents)
DROP FUNCTION IF EXISTS get_due_pulse_agents();

-- Note: The scheduler will now query tasks.next_run_at instead.
-- New RPC function for task-based scheduling will be created in Phase 3.
