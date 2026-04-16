-- Migration 148: ADR-187 Trading Integration — add trading_bot role
--
-- Adds 'trading_bot' to agents_role_check constraint.
-- Trading Bot is scaffolded at signup (paused) and activated when
-- the user connects a trading provider (Alpaca).

-- Step 1: Drop the old constraint
ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_role_check;

-- Step 2: Add updated constraint with trading_bot
ALTER TABLE agents ADD CONSTRAINT agents_role_check CHECK (role = ANY (ARRAY[
    -- v5 universal specialist roles (ADR-176)
    'researcher'::text, 'analyst'::text, 'writer'::text, 'tracker'::text, 'designer'::text,
    -- synthesizer
    'executive'::text,
    -- platform bots (ADR-158 + ADR-183 + ADR-187)
    'slack_bot'::text, 'notion_bot'::text, 'github_bot'::text, 'commerce_bot'::text, 'trading_bot'::text,
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
