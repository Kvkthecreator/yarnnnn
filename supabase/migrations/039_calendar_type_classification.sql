-- Migration 039: ADR-046 Calendar Type Classification
-- Adds type_classification for Google Calendar deliverable types

-- =============================================================================
-- UPDATE CALENDAR TYPES WITH PROPER CLASSIFICATION
-- =============================================================================

-- meeting_prep: Platform-bound to calendar, reactive (before meetings)
UPDATE deliverables
SET type_classification = jsonb_build_object(
    'binding', 'platform_bound',
    'temporal_pattern', 'reactive',
    'primary_platform', 'calendar',
    'freshness_requirement_hours', 1
)
WHERE deliverable_type = 'meeting_prep'
  AND (type_classification IS NULL
       OR type_classification = '{}'::jsonb
       OR type_classification->>'binding' = 'cross_platform');

-- weekly_calendar_preview: Platform-bound to calendar, scheduled
UPDATE deliverables
SET type_classification = jsonb_build_object(
    'binding', 'platform_bound',
    'temporal_pattern', 'scheduled',
    'primary_platform', 'calendar',
    'freshness_requirement_hours', 4
)
WHERE deliverable_type = 'weekly_calendar_preview'
  AND (type_classification IS NULL
       OR type_classification = '{}'::jsonb
       OR type_classification->>'binding' = 'cross_platform');

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON COLUMN deliverables.type_classification IS 'ADR-044/046: Two-dimensional type classification (binding + temporal_pattern). Calendar types use platform_bound with primary_platform=calendar.';
