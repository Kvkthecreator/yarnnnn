-- ADR-138 revision: Move mode from agents to tasks
-- Mode (recurring/goal/reactive) is temporal behavior of WORK, not identity of WORKER.
-- A Research Agent can simultaneously have a recurring task and a goal task.

-- 1. Add mode column to tasks table
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS mode TEXT NOT NULL DEFAULT 'recurring';
ALTER TABLE tasks ADD CONSTRAINT tasks_mode_check CHECK (mode IN ('recurring', 'goal', 'reactive'));

-- 2. Drop dependent view that references agents.mode
DROP VIEW IF EXISTS agent_role_metrics;

-- 3. Drop mode from agents table
ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_mode_check;
ALTER TABLE agents DROP COLUMN IF EXISTS mode;

-- 4. Recreate view without mode column
CREATE VIEW agent_role_metrics AS
SELECT
    a.id AS agent_id,
    a.title,
    a.scope,
    a.role,
    a.status,
    count(ar.id) AS total_runs,
    count(CASE WHEN ar.status = 'delivered' THEN 1 ELSE NULL END) AS delivered_runs,
    count(CASE WHEN ar.status = 'failed' THEN 1 ELSE NULL END) AS failed_runs,
    max(ar.created_at) AS last_run_at,
    a.created_at AS agent_created_at
FROM agents a
LEFT JOIN agent_runs ar ON ar.agent_id = a.id
GROUP BY a.id, a.title, a.scope, a.role, a.status, a.created_at;
