-- ADR-164: TP becomes a first-class agent entity.
--
-- Add `thinking_partner` as a valid agent role. The `agents_role_check`
-- constraint is replaced with the same list plus the new role. No data
-- migration required — this only allows a new role to be inserted.
--
-- The new role pairs with `agent_class='meta-cognitive'` in the Python
-- AGENT_TEMPLATES registry. Note that `agent_class` is not a DB column —
-- it lives as template metadata in `api/services/agent_framework.py`.
-- Only `role` needs a schema change.
--
-- TP's slug will be `thinking-partner` (derived by get_agent_slug from
-- the agent's title "Thinking Partner"). See ADR-164 section 4.0 audit
-- notes for why slug is title-derived, not DB-stored.
--
-- See: docs/adr/ADR-164-back-office-tasks-tp-as-agent.md

ALTER TABLE agents
DROP CONSTRAINT IF EXISTS agents_role_check;

ALTER TABLE agents
ADD CONSTRAINT agents_role_check CHECK (role = ANY (ARRAY[
  -- ADR-140 current domain-steward + synthesizer + bot roles
  'competitive_intel'::text,
  'market_research'::text,
  'business_dev'::text,
  'operations'::text,
  'marketing'::text,
  'executive'::text,
  'slack_bot'::text,
  'notion_bot'::text,
  'github_bot'::text,
  -- ADR-164: TP as meta-cognitive agent (NEW)
  'thinking_partner'::text,
  -- Legacy aliases kept for pre-ADR-140 rows (LEGACY_ROLE_MAP)
  'research'::text,
  'content'::text,
  'crm'::text,
  'monitor'::text,
  'researcher'::text,
  'producer'::text,
  'operator'::text,
  'briefer'::text,
  'drafter'::text,
  'analyst'::text,
  'writer'::text,
  'planner'::text,
  'scout'::text,
  'digest'::text,
  'prepare'::text,
  'synthesize'::text,
  'act'::text,
  'custom'::text
]));
