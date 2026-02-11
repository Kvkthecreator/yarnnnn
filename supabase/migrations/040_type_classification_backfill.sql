-- Migration 040: ADR-045 Type Classification Backfill
-- Re-applies type_classification for deliverables that may have been created
-- with empty classification after migration 037 but before code fix.

-- =============================================================================
-- BACKFILL TYPE CLASSIFICATION (same logic as 037, ensures no gaps)
-- =============================================================================

UPDATE deliverables
SET type_classification = CASE
    -- Platform-bound: Slack
    WHEN deliverable_type IN ('slack_channel_digest', 'slack_standup') THEN
        jsonb_build_object(
            'binding', 'platform_bound',
            'temporal_pattern', 'scheduled',
            'primary_platform', 'slack',
            'freshness_requirement_hours', 1
        )
    -- Platform-bound: Gmail
    WHEN deliverable_type IN ('gmail_inbox_brief', 'inbox_summary', 'reply_draft', 'follow_up_tracker', 'thread_summary') THEN
        jsonb_build_object(
            'binding', 'platform_bound',
            'temporal_pattern', 'scheduled',
            'primary_platform', 'gmail',
            'freshness_requirement_hours', 1
        )
    -- Platform-bound: Notion
    WHEN deliverable_type = 'notion_page_summary' THEN
        jsonb_build_object(
            'binding', 'platform_bound',
            'temporal_pattern', 'scheduled',
            'primary_platform', 'notion',
            'freshness_requirement_hours', 4
        )
    -- Platform-bound: Calendar (ADR-046)
    WHEN deliverable_type = 'meeting_prep' THEN
        jsonb_build_object(
            'binding', 'platform_bound',
            'temporal_pattern', 'reactive',
            'primary_platform', 'calendar',
            'freshness_requirement_hours', 1
        )
    WHEN deliverable_type = 'weekly_calendar_preview' THEN
        jsonb_build_object(
            'binding', 'platform_bound',
            'temporal_pattern', 'scheduled',
            'primary_platform', 'calendar',
            'freshness_requirement_hours', 4
        )
    -- Research: Web research deliverables (ADR-045)
    WHEN deliverable_type = 'research_brief' THEN
        jsonb_build_object(
            'binding', 'research',
            'temporal_pattern', 'on_demand',
            'freshness_requirement_hours', 24
        )
    -- Cross-platform: Multi-source synthesis
    WHEN deliverable_type IN ('status_report', 'weekly_status', 'cross_platform_digest', 'activity_summary', 'project_brief') THEN
        jsonb_build_object(
            'binding', 'cross_platform',
            'temporal_pattern', 'scheduled',
            'freshness_requirement_hours', 4
        )
    -- Cross-platform: Meeting-related
    WHEN deliverable_type IN ('meeting_summary', 'one_on_one_prep') THEN
        jsonb_build_object(
            'binding', 'cross_platform',
            'temporal_pattern', 'scheduled',
            'freshness_requirement_hours', 1
        )
    -- Cross-platform: Stakeholder communication
    WHEN deliverable_type IN ('stakeholder_update', 'client_proposal', 'board_update', 'newsletter_section') THEN
        jsonb_build_object(
            'binding', 'cross_platform',
            'temporal_pattern', 'scheduled',
            'freshness_requirement_hours', 4
        )
    -- Cross-platform: Beta/other types
    WHEN deliverable_type IN ('changelog', 'performance_self_assessment') THEN
        jsonb_build_object(
            'binding', 'cross_platform',
            'temporal_pattern', 'scheduled',
            'freshness_requirement_hours', 24
        )
    -- Default for custom and unknown
    ELSE
        jsonb_build_object(
            'binding', 'cross_platform',
            'temporal_pattern', 'scheduled',
            'freshness_requirement_hours', 4
        )
END
WHERE type_classification IS NULL
   OR type_classification = '{}'::jsonb
   OR type_classification->>'binding' IS NULL;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON COLUMN deliverables.type_classification IS 'ADR-044/045/046: Two-dimensional type classification (binding + temporal_pattern). Determines execution strategy: platform_bound, cross_platform, research, or hybrid.';
