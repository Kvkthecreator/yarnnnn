-- ADR-140: Agent Workforce Model — update role CHECK for new types
-- New types: research, content, marketing, crm, slack_bot, notion_bot
-- Keep all legacy values for backward compat (resolve_role() maps them)

ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_role_check;
ALTER TABLE agents ADD CONSTRAINT agents_role_check CHECK (
  role IN (
    -- v3 workforce roster (ADR-140)
    'research', 'content', 'marketing', 'crm', 'slack_bot', 'notion_bot',
    -- v2 legacy (ADR-130) — mapped via LEGACY_ROLE_MAP in code
    'monitor', 'researcher', 'producer', 'operator',
    'briefer', 'drafter', 'analyst', 'writer', 'planner', 'scout',
    -- v1 legacy
    'digest', 'prepare', 'synthesize', 'act', 'custom'
  )
);
