-- ADR-117 Phase 3: Agent Duties & Role Portfolios
-- duties: JSONB array of {duty, trigger, status, added_at} — null = single-duty (seed role)
-- duty_name: which duty produced this run (null = seed role, backwards-compat)

ALTER TABLE agents ADD COLUMN IF NOT EXISTS duties JSONB DEFAULT NULL;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS duty_name TEXT DEFAULT NULL;
