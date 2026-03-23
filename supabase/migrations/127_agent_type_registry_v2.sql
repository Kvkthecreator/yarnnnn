-- Migration 127: ADR-130 v2 — expand agents role check for new type names
--
-- New types: briefer, researcher, drafter, analyst, writer, planner, scout
-- Legacy types preserved for backward compat: digest, prepare, synthesize, research, act, custom
-- resolve_role() in agent_framework.py maps legacy → new at read time

ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_role_check;

ALTER TABLE agents ADD CONSTRAINT agents_role_check CHECK (
  role = ANY (ARRAY[
    -- v2 product types (ADR-130)
    'briefer', 'monitor', 'researcher', 'drafter', 'analyst', 'writer', 'planner', 'scout', 'pm',
    -- Legacy types (backward compat — resolve_role() maps these at read time)
    'digest', 'prepare', 'synthesize', 'research', 'act', 'custom'
  ])
);

-- Migrate existing agents to new role names where safe
-- Only migrate roles with 1:1 mappings; leave ambiguous ones for resolve_role()
UPDATE agents SET role = 'briefer' WHERE role = 'digest' AND role != 'briefer';
UPDATE agents SET role = 'researcher' WHERE role = 'research' AND role != 'researcher';
UPDATE agents SET role = 'planner' WHERE role = 'prepare' AND role != 'planner';
UPDATE agents SET role = 'analyst' WHERE role = 'synthesize' AND role != 'analyst';
