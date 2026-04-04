-- ADR-158 Phase 4: Add github_bot to agents role check constraint.
-- GitHub Bot is the third platform-bot (alongside slack_bot, notion_bot).

ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_role_check;
ALTER TABLE agents ADD CONSTRAINT agents_role_check CHECK (
  role IN (
    -- v4 domain-steward model (ADR-152)
    'competitive_intel', 'market_research', 'business_dev', 'operations', 'marketing',
    'executive',  -- synthesizer (cross-domain)
    'slack_bot', 'notion_bot', 'github_bot',  -- platform bots (ADR-158)
    -- v3 legacy (ADR-140) — mapped via LEGACY_ROLE_MAP in code
    'research', 'content', 'crm',
    -- v2 legacy (ADR-130)
    'monitor', 'researcher', 'producer', 'operator',
    'briefer', 'drafter', 'analyst', 'writer', 'planner', 'scout',
    -- v1 legacy
    'digest', 'prepare', 'synthesize', 'act', 'custom'
  )
);
