-- Migration: 091_deliverable_type_taxonomy.sql
-- ADR-093: Replace 8 legacy deliverable types with 7 purpose-first types.
-- All existing data is test data — full backfill, no compat shims.

BEGIN;

-- Step 1: Drop existing CHECK constraint
ALTER TABLE deliverables
    DROP CONSTRAINT IF EXISTS deliverables_deliverable_type_check;

-- Step 2: Backfill all existing rows to new type names
UPDATE deliverables SET deliverable_type = 'digest'
WHERE deliverable_type IN (
    'slack_channel_digest', 'gmail_inbox_brief', 'notion_page_summary',
    'weekly_calendar_preview', 'inbox_summary', 'reply_draft',
    'follow_up_tracker', 'thread_summary', 'slack_standup'
);

UPDATE deliverables SET deliverable_type = 'status'
WHERE deliverable_type IN (
    'status_report', 'stakeholder_update', 'board_update', 'weekly_status',
    'project_brief', 'cross_platform_digest', 'activity_summary'
);

UPDATE deliverables SET deliverable_type = 'brief'
WHERE deliverable_type IN (
    'meeting_prep', 'meeting_summary', 'one_on_one_prep'
);

UPDATE deliverables SET deliverable_type = 'deep_research'
WHERE deliverable_type IN (
    'research_brief', 'deep_research'
);

UPDATE deliverables SET deliverable_type = 'watch'
WHERE deliverable_type IN (
    'intelligence_brief', 'daily_strategy_reflection'
);

UPDATE deliverables SET deliverable_type = 'custom'
WHERE deliverable_type IN (
    'client_proposal', 'performance_self_assessment',
    'newsletter_section', 'changelog'
);

-- Step 3: Add new CHECK constraint with 7 types only
ALTER TABLE deliverables
    ADD CONSTRAINT deliverables_deliverable_type_check
    CHECK (deliverable_type IN (
        'digest',
        'brief',
        'status',
        'watch',
        'deep_research',
        'coordinator',
        'custom'
    ));

COMMIT;
