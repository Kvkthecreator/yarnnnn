-- Migration: 064_deliverable_type_constraint.sql
-- Extends deliverable_type CHECK constraint to include all types defined in
-- TYPE_TIERS (api/routes/deliverables.py): platform-first Wave 1, calendar,
-- synthesizer, and email-specific types added since migration 021.
--
-- Previously missing types causing INSERT failures:
--   Platform-first (ADR-035): slack_channel_digest, slack_standup,
--                              gmail_inbox_brief, notion_page_summary
--   Calendar (ADR-046):        meeting_prep, weekly_calendar_preview
--   Synthesizers (ADR-031):    weekly_status, project_brief,
--                              cross_platform_digest, activity_summary
--   Email (ADR-029):           inbox_summary, reply_draft,
--                              follow_up_tracker, thread_summary

ALTER TABLE deliverables
    DROP CONSTRAINT IF EXISTS deliverables_deliverable_type_check;

ALTER TABLE deliverables
    ADD CONSTRAINT deliverables_deliverable_type_check
    CHECK (deliverable_type IN (
        -- Stable
        'status_report',
        'stakeholder_update',
        'research_brief',
        'meeting_summary',
        -- Beta
        'client_proposal',
        'performance_self_assessment',
        'newsletter_section',
        'changelog',
        'one_on_one_prep',
        'board_update',
        -- Email (ADR-029)
        'inbox_summary',
        'reply_draft',
        'follow_up_tracker',
        'thread_summary',
        -- Platform-first Wave 1 (ADR-035)
        'slack_channel_digest',
        'slack_standup',
        'gmail_inbox_brief',
        'notion_page_summary',
        -- Calendar (ADR-046)
        'meeting_prep',
        'weekly_calendar_preview',
        -- Synthesizers / cross-platform (ADR-031)
        'weekly_status',
        'project_brief',
        'cross_platform_digest',
        'activity_summary',
        -- Catch-all
        'custom'
    ));
