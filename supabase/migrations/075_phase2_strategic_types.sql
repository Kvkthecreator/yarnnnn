-- Migration: 075_phase2_strategic_types.sql
-- Adds Phase 2 strategic intelligence deliverable types to database constraint
-- Types: deep_research, daily_strategy_reflection, intelligence_brief
-- These were added to code in Phase 2 but not yet in database schema

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
        -- Phase 2: Strategic Intelligence Types
        'deep_research',
        'daily_strategy_reflection',
        'intelligence_brief',
        -- Catch-all
        'custom'
    ));
