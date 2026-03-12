-- Migration 103: ADR-109 Agent Framework — Scope × Skill × Trigger
--
-- Replaces the 7-type system (agent_type + type_classification) with
-- orthogonal scope + skill columns. Trigger is already captured by the
-- existing `mode` column (ADR-092).
--
-- This is a singular migration — no dual-read period. Backend code ships
-- simultaneously with this schema change.

-- 1. Add new columns
ALTER TABLE agents ADD COLUMN IF NOT EXISTS scope TEXT;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS skill TEXT;

-- 2. Backfill scope from type_classification.binding
UPDATE agents SET scope = CASE
  WHEN type_classification->>'binding' = 'platform_bound' THEN 'platform'
  WHEN type_classification->>'binding' = 'cross_platform' THEN 'cross_platform'
  WHEN type_classification->>'binding' = 'research' THEN 'research'
  WHEN type_classification->>'binding' = 'hybrid' THEN 'research'
  WHEN agent_type = 'deep_research' THEN 'autonomous'
  WHEN agent_type = 'coordinator' THEN 'autonomous'
  WHEN agent_type = 'watch' THEN 'cross_platform'
  WHEN agent_type = 'custom' THEN 'cross_platform'
  ELSE 'cross_platform'
END
WHERE scope IS NULL;

-- 3. Backfill skill from agent_type
UPDATE agents SET skill = CASE
  WHEN agent_type = 'digest' THEN 'digest'
  WHEN agent_type = 'brief' THEN 'prepare'
  WHEN agent_type = 'status' THEN 'synthesize'
  WHEN agent_type = 'watch' THEN 'monitor'
  WHEN agent_type = 'deep_research' THEN 'synthesize'
  WHEN agent_type = 'coordinator' THEN 'orchestrate'
  WHEN agent_type = 'custom' THEN 'custom'
  ELSE 'custom'
END
WHERE skill IS NULL;

-- 4. Set NOT NULL after backfill
ALTER TABLE agents ALTER COLUMN scope SET NOT NULL;
ALTER TABLE agents ALTER COLUMN skill SET NOT NULL;

-- 5. Add constraints
ALTER TABLE agents ADD CONSTRAINT agents_scope_check
  CHECK (scope IN ('platform', 'cross_platform', 'knowledge', 'research', 'autonomous'));

ALTER TABLE agents ADD CONSTRAINT agents_skill_check
  CHECK (skill IN ('digest', 'prepare', 'monitor', 'research', 'synthesize', 'orchestrate', 'act', 'custom'));

-- 6. Drop legacy view that depends on agent_type + type_tier
DROP VIEW IF EXISTS agent_type_metrics;

-- 7. Drop legacy columns
ALTER TABLE agents DROP COLUMN IF EXISTS agent_type;
ALTER TABLE agents DROP COLUMN IF EXISTS type_tier;
ALTER TABLE agents DROP COLUMN IF EXISTS type_classification;

-- 8. Recreate analytics view with new columns
CREATE OR REPLACE VIEW agent_skill_metrics AS
SELECT
  a.user_id,
  a.scope,
  a.skill,
  count(DISTINCT a.id) AS agent_count,
  count(ar.id) AS total_runs,
  count(ar.id) FILTER (WHERE ar.status = 'approved') AS approved_runs,
  count(ar.id) FILTER (WHERE ar.status = 'rejected') AS rejected_runs,
  avg(ar.edit_distance_score) FILTER (WHERE ar.status = 'approved') AS avg_edit_distance,
  count(ar.id) FILTER (WHERE ar.edit_distance_score < 0.3 AND ar.status = 'approved') AS low_edit_count,
  count(ar.id) FILTER (WHERE ar.edit_distance_score >= 0.3 AND ar.status = 'approved') AS high_edit_count
FROM agents a
LEFT JOIN agent_runs ar ON a.id = ar.agent_id
GROUP BY a.user_id, a.scope, a.skill;
