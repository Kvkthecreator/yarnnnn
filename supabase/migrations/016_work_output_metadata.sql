-- Migration 016: Add metadata column to work_outputs (ADR-016)
--
-- ADR-016 introduces agent-specific metadata for work outputs:
-- - Research: sources, confidence, scope, depth
-- - Content: format, platform, tone, word_count
-- - Reporting: style, audience, period
--
-- Also adds 'status' column to track output lifecycle and
-- removes output_type (agent type is stored on ticket, not output)

-- Add metadata column
ALTER TABLE work_outputs
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Add status column for output lifecycle
ALTER TABLE work_outputs
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'delivered';

-- Note: We keep output_type for backward compatibility but it's deprecated
-- New code should use agent_type from work_tickets

COMMENT ON COLUMN work_outputs.metadata IS 'Agent-specific metadata (ADR-016): sources, confidence, format, etc.';
COMMENT ON COLUMN work_outputs.status IS 'Output status: pending, delivered, archived';
