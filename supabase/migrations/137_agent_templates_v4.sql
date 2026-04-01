-- ADR-152: Agent Templates v4 — Domain-Steward Model
-- Adds new v4 role values for domain-steward agents.
-- Old values preserved for data compatibility (agents created before this migration).

ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_role_check;
ALTER TABLE agents ADD CONSTRAINT agents_role_check CHECK (
  role IN (
    -- v4 domain-steward model (ADR-152)
    'competitive_intel', 'market_research', 'business_dev', 'operations', 'marketing',
    'executive',  -- synthesizer (cross-domain)
    'slack_bot', 'notion_bot',  -- platform bots
    -- v3 legacy (ADR-140) — mapped via LEGACY_ROLE_MAP in code
    'research', 'content', 'crm',
    -- v2 legacy (ADR-130)
    'monitor', 'researcher', 'producer', 'operator',
    'briefer', 'drafter', 'analyst', 'writer', 'planner', 'scout',
    -- v1 legacy
    'digest', 'prepare', 'synthesize', 'act', 'custom'
  )
);
