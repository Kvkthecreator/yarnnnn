-- Migration 157: ADR-207 P4a — Platform Bots dissolved into capability gates
--
-- Three cohesive changes:
--
-- 1. DELETE all Platform Bot agent rows. slack_bot / notion_bot / github_bot /
--    commerce_bot / trading_bot are no longer agent classes. Platform access
--    runs through CAPABILITIES (read_slack, write_notion, write_trading, ...)
--    gated by `platform_connection_requirement` at task dispatch (ADR-207 P3).
--
-- 2. DELETE any tasks whose TASK.md referenced deleted bot agent slugs so
--    the scheduler doesn't hit broken dispatch. Operators re-author equivalent
--    tasks via YARNNN using a specialist + `**Required Capabilities:**`
--    declaration.
--
-- 3. Update `agents_role_check` — drop the 5 bot role values. Only
--    specialists, synthesizer, YARNNN, and legacy roles remain.
--
-- FK cascade notes: agent_runs, agent_context_log rows tied to bot agents
-- are dropped along with the agent row. Acceptable — bot-specific work
-- history is no longer meaningful under the capability-gate model.

BEGIN;

-- Step 1: Delete bot-dispatched tasks (tasks whose TASK.md resolved to a bot agent)
-- We identify them by task slug convention or by agent lookup. Using the
-- well-known slug set is simpler and safer than parsing TASK.md.

DELETE FROM public.tasks
WHERE slug IN (
  'slack-sync', 'notion-sync', 'github-sync',
  'commerce-sync', 'trading-sync',
  -- external-action bot tasks (if any operator created them)
  'slack-respond', 'notion-update',
  'commerce-create-product', 'commerce-update-product',
  'commerce-create-discount',
  'trading-execute'
);

-- Step 2: Delete all bot agent rows
DELETE FROM public.agents
WHERE role IN ('slack_bot', 'notion_bot', 'github_bot', 'commerce_bot', 'trading_bot');

-- Step 3: Rebuild agents_role_check without bot roles
ALTER TABLE public.agents DROP CONSTRAINT IF EXISTS agents_role_check;

ALTER TABLE public.agents ADD CONSTRAINT agents_role_check CHECK (role = ANY (ARRAY[
    -- v5 universal specialist roles (ADR-176)
    'researcher'::text, 'analyst'::text, 'writer'::text, 'tracker'::text, 'designer'::text,
    -- synthesizer
    'executive'::text,
    -- meta-cognitive (ADR-164)
    'thinking_partner'::text,
    -- ADR-207 P4a: Platform Bot role values (slack_bot / notion_bot /
    -- github_bot / commerce_bot / trading_bot) REMOVED. Platform access
    -- flows through CAPABILITIES, not through a dedicated agent class.
    -- legacy v4 ICP roles (kept for backward compat — no new agents created with these)
    'competitive_intel'::text, 'market_research'::text, 'business_dev'::text,
    'operations'::text, 'marketing'::text,
    -- legacy ADR-130 / ADR-109 roles
    'research'::text, 'content'::text, 'crm'::text, 'monitor'::text,
    'producer'::text, 'operator'::text, 'briefer'::text, 'drafter'::text,
    'planner'::text, 'scout'::text, 'digest'::text, 'prepare'::text,
    'synthesize'::text, 'act'::text, 'custom'::text
]));

COMMIT;

-- Sanity checks
DO $$
DECLARE
  remaining_bot_agents INT;
  remaining_bot_tasks INT;
BEGIN
  SELECT COUNT(*) INTO remaining_bot_agents
    FROM public.agents
    WHERE role IN ('slack_bot', 'notion_bot', 'github_bot', 'commerce_bot', 'trading_bot');
  SELECT COUNT(*) INTO remaining_bot_tasks
    FROM public.tasks
    WHERE slug IN ('slack-sync','notion-sync','github-sync','commerce-sync','trading-sync',
                   'slack-respond','notion-update',
                   'commerce-create-product','commerce-update-product','commerce-create-discount',
                   'trading-execute');
  RAISE NOTICE '[ADR-207 P4a] Remaining bot agents: % (expected 0)', remaining_bot_agents;
  RAISE NOTICE '[ADR-207 P4a] Remaining bot tasks: % (expected 0)', remaining_bot_tasks;
END $$;
