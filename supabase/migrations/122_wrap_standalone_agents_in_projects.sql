-- ADR-122 Phase 4: Wrap standalone agents in projects
-- Creates PROJECT.md workspace_files entries for agents not already in a project.
--
-- Strategy:
--   1. Bootstrap platform digests → platform project type (slack_digest, notion_digest)
--   2. All other standalone agents → custom project type (one project per agent)
--   3. Seeds memory/projects.json for each wrapped agent
--   4. Adds type_key to existing projects that lack one

-- Step 1: Identify standalone agents (no projects.json in their workspace)
-- We use a CTE to find agents whose slug doesn't appear in any /agents/{slug}/memory/projects.json

-- Helper: derive slug from agent title (lowercase, spaces→hyphens, strip non-alphanumeric)
-- Note: Postgres doesn't have a slugify function, so we use lower + regexp_replace

BEGIN;

-- ============================================================================
-- 1. Wrap bootstrap platform digest agents in platform projects
-- ============================================================================

-- Slack Recap agents (system_bootstrap, role=digest, title='Slack Recap')
-- For each user with a Slack Recap agent that has no projects.json:
INSERT INTO workspace_files (user_id, path, content, summary, tags, lifecycle, created_at, updated_at)
SELECT
    a.user_id,
    '/projects/slack-recap/PROJECT.md',
    E'# Slack Recap\n\n**Type**: slack_digest\n\n## Intent\n- **Deliverable**: Daily Slack recap\n- **Audience**: You\n- **Format**: email\n- **Purpose**: Stay informed on team activity without reading every message\n\n## Contributors\n- ' || lower(regexp_replace(a.title, '[^a-zA-Z0-9 ]', '', 'g')) || ': Daily platform digest',
    'Project identity: Slack Recap',
    ARRAY['project', 'identity'],
    'active',
    NOW(),
    NOW()
FROM agents a
WHERE a.title = 'Slack Recap'
  AND a.origin = 'system_bootstrap'
  AND a.status != 'archived'
  AND NOT EXISTS (
    SELECT 1 FROM workspace_files wf
    WHERE wf.user_id = a.user_id
      AND wf.path LIKE '/agents/' || lower(regexp_replace(a.title, ' ', '-', 'g')) || '/memory/projects.json'
  )
  AND NOT EXISTS (
    SELECT 1 FROM workspace_files wf
    WHERE wf.user_id = a.user_id
      AND wf.path = '/projects/slack-recap/PROJECT.md'
  )
ON CONFLICT (user_id, path) DO NOTHING;

-- Seed projects.json for Slack Recap agents
INSERT INTO workspace_files (user_id, path, content, summary, tags, lifecycle, content_type, created_at, updated_at)
SELECT
    a.user_id,
    '/agents/' || lower(regexp_replace(a.title, ' ', '-', 'g')) || '/memory/projects.json',
    '[{"project_slug": "slack-recap", "title": "Slack Recap", "expected_contribution": "digest output"}]',
    'Project memberships (1 projects)',
    ARRAY['memory'],
    'active',
    'application/json',
    NOW(),
    NOW()
FROM agents a
WHERE a.title = 'Slack Recap'
  AND a.origin = 'system_bootstrap'
  AND a.status != 'archived'
  AND NOT EXISTS (
    SELECT 1 FROM workspace_files wf
    WHERE wf.user_id = a.user_id
      AND wf.path = '/agents/' || lower(regexp_replace(a.title, ' ', '-', 'g')) || '/memory/projects.json'
  )
ON CONFLICT (user_id, path) DO NOTHING;

-- Notion Summary agents
INSERT INTO workspace_files (user_id, path, content, summary, tags, lifecycle, created_at, updated_at)
SELECT
    a.user_id,
    '/projects/notion-summary/PROJECT.md',
    E'# Notion Summary\n\n**Type**: notion_digest\n\n## Intent\n- **Deliverable**: Daily Notion summary\n- **Audience**: You\n- **Format**: email\n- **Purpose**: Track workspace changes without visiting every page\n\n## Contributors\n- notion-summary: Daily platform digest',
    'Project identity: Notion Summary',
    ARRAY['project', 'identity'],
    'active',
    NOW(),
    NOW()
FROM agents a
WHERE a.title = 'Notion Summary'
  AND a.origin = 'system_bootstrap'
  AND a.status != 'archived'
  AND NOT EXISTS (
    SELECT 1 FROM workspace_files wf
    WHERE wf.user_id = a.user_id
      AND wf.path = '/projects/notion-summary/PROJECT.md'
  )
ON CONFLICT (user_id, path) DO NOTHING;

-- Seed projects.json for Notion Summary agents
INSERT INTO workspace_files (user_id, path, content, summary, tags, lifecycle, content_type, created_at, updated_at)
SELECT
    a.user_id,
    '/agents/notion-summary/memory/projects.json',
    '[{"project_slug": "notion-summary", "title": "Notion Summary", "expected_contribution": "digest output"}]',
    'Project memberships (1 projects)',
    ARRAY['memory'],
    'active',
    'application/json',
    NOW(),
    NOW()
FROM agents a
WHERE a.title = 'Notion Summary'
  AND a.origin = 'system_bootstrap'
  AND a.status != 'archived'
  AND NOT EXISTS (
    SELECT 1 FROM workspace_files wf
    WHERE wf.user_id = a.user_id
      AND wf.path = '/agents/notion-summary/memory/projects.json'
  )
ON CONFLICT (user_id, path) DO NOTHING;

-- ============================================================================
-- 2. Add type_key to existing projects that lack one
-- ============================================================================

-- The 3 existing projects (weekly-intelligence-report, weekly-intelligence-briefing,
-- weekly-intelligence-assembly) were created pre-ADR-122 and have no **Type** field.
-- Add type_key=custom to them.

UPDATE workspace_files
SET content = regexp_replace(
    content,
    E'^(# [^\n]+)\n',
    E'\\1\n\n**Type**: custom\n',
    ''
),
    updated_at = NOW()
WHERE path LIKE '/projects/%/PROJECT.md'
  AND content NOT LIKE '%**Type**:%';

COMMIT;
