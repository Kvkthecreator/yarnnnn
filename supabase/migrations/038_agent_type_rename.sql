-- Migration 038: Agent Type Rename
-- ADR-045: Deliverable Orchestration Redesign
--
-- Renames agent_type values to reflect actual function:
-- - research → synthesizer (synthesizes pre-fetched context)
-- - content → deliverable (generates deliverables)
-- - reporting → report (generates standalone reports)
--
-- The factory.py handles backwards compatibility for old values,
-- but we want new records to use the new names.

-- Update existing work_tickets agent_type values
UPDATE work_tickets SET agent_type = 'synthesizer' WHERE agent_type = 'research';
UPDATE work_tickets SET agent_type = 'deliverable' WHERE agent_type = 'content';
UPDATE work_tickets SET agent_type = 'report' WHERE agent_type = 'reporting';

-- Update existing agent_sessions agent_type values
UPDATE agent_sessions SET agent_type = 'synthesizer' WHERE agent_type = 'research';
UPDATE agent_sessions SET agent_type = 'deliverable' WHERE agent_type = 'content';
UPDATE agent_sessions SET agent_type = 'report' WHERE agent_type = 'reporting';

-- Add comment to work_tickets.agent_type column documenting the new values
COMMENT ON COLUMN work_tickets.agent_type IS 'Agent type: synthesizer (context synthesis), deliverable (deliverable generation), report (standalone reports), chat (thinking partner). Legacy values (research, content, reporting) mapped in code.';

-- Add comment to agent_sessions.agent_type column
COMMENT ON COLUMN agent_sessions.agent_type IS 'Agent type: synthesizer, deliverable, report, chat. See work_tickets.agent_type comment for details.';
