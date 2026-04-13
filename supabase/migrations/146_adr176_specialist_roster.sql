-- Migration 146: ADR-176 Universal Specialist Roster
--
-- Adds 'tracker' and 'designer' to agents_role_check constraint.
-- These two v5 universal specialist roles were missing from the prior constraint,
-- which only included roles up through ADR-140 (ICP domain-stewards) and ADR-164 (TP).
--
-- Run alongside Phase 5 clean-slate migration (delete ICP agents, scaffold specialists).

-- Step 1: Drop the old constraint
ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_role_check;

-- Step 2: Add updated constraint with v5 specialist roles
ALTER TABLE agents ADD CONSTRAINT agents_role_check CHECK (role = ANY (ARRAY[
    -- v5 universal specialist roles (ADR-176)
    'researcher'::text, 'analyst'::text, 'writer'::text, 'tracker'::text, 'designer'::text,
    -- synthesizer
    'executive'::text,
    -- platform bots
    'slack_bot'::text, 'notion_bot'::text, 'github_bot'::text,
    -- meta-cognitive (ADR-164)
    'thinking_partner'::text,
    -- legacy v4 ICP roles (kept for backward compat — no new agents created with these)
    'competitive_intel'::text, 'market_research'::text, 'business_dev'::text,
    'operations'::text, 'marketing'::text,
    -- legacy ADR-130 / ADR-109 roles
    'research'::text, 'content'::text, 'crm'::text, 'monitor'::text,
    'producer'::text, 'operator'::text, 'briefer'::text, 'drafter'::text,
    'planner'::text, 'scout'::text, 'digest'::text, 'prepare'::text,
    'synthesize'::text, 'act'::text, 'custom'::text
]));
