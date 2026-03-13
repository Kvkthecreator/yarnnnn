-- ADR-110: Add system_bootstrap to agents origin check constraint
-- Bootstrap service creates digest agents on platform connection

ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_origin_check;
ALTER TABLE agents ADD CONSTRAINT agents_origin_check
  CHECK (origin IN ('user_configured', 'analyst_suggested', 'signal_emergent', 'coordinator_created', 'system_bootstrap'));
