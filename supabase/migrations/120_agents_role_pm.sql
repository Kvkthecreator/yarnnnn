-- Migration 120: Add 'pm' to agents role CHECK constraint
--
-- ADR-120 Phase 1 introduced the 'pm' role for Project Manager agents,
-- but the CHECK constraint on agents.role was never updated.
-- Composer's _execute_create_project() creates pm agents, which fail
-- with agents_role_check violation.

ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_role_check;

ALTER TABLE agents ADD CONSTRAINT agents_role_check
    CHECK (role = ANY (ARRAY[
        'digest', 'prepare', 'synthesize', 'monitor',
        'research', 'act', 'custom', 'pm'
    ]));
