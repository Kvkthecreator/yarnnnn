-- Migration 124: Agent Pulse (ADR-126)
--
-- Renames next_run_at → next_pulse_at (semantics: "when to sense" not "when to generate")
-- Absorbs proactive_next_review_at into next_pulse_at (single pulse cadence for all agents)
-- Updates get_due_agents RPC → get_due_pulse_agents (queries all active agents, not mode-filtered)

-- 1. Rename next_run_at → next_pulse_at
ALTER TABLE agents RENAME COLUMN next_run_at TO next_pulse_at;

-- 2. Migrate proactive_next_review_at into next_pulse_at where applicable
-- For proactive/coordinator agents that have a proactive_next_review_at but no next_pulse_at,
-- copy the review schedule to pulse schedule
UPDATE agents
SET next_pulse_at = proactive_next_review_at
WHERE next_pulse_at IS NULL
  AND proactive_next_review_at IS NOT NULL
  AND mode IN ('proactive', 'coordinator');

-- 3. Drop proactive_next_review_at (absorbed into next_pulse_at)
ALTER TABLE agents DROP COLUMN IF EXISTS proactive_next_review_at;

-- 4. Update index (rename to match new column)
DROP INDEX IF EXISTS idx_agents_next_run;
CREATE INDEX idx_agents_next_pulse ON agents(next_pulse_at) WHERE status = 'active';

-- 5. Replace get_due_agents RPC with get_due_pulse_agents
-- Old version filtered to recurring/goal modes only.
-- New version returns ALL active agents due for pulse (all modes).
DROP FUNCTION IF EXISTS get_due_agents(timestamptz);

CREATE OR REPLACE FUNCTION get_due_pulse_agents(check_time timestamptz DEFAULT now())
RETURNS SETOF agents
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
  SELECT *
  FROM agents a
  WHERE a.status = 'active'
    AND a.next_pulse_at IS NOT NULL
    AND a.next_pulse_at <= check_time;
$$;
