-- Migration 037: ADR-044 Deliverable Type Classification
-- Adds type_classification JSONB for two-dimensional type model
-- Adds emergent deliverable discovery tracking tables

-- =============================================================================
-- DELIVERABLE TYPE CLASSIFICATION
-- =============================================================================

-- Add type_classification column for ADR-044 two-dimensional model
-- Structure: {
--   "binding": "platform_bound" | "cross_platform" | "research" | "hybrid",
--   "temporal_pattern": "reactive" | "scheduled" | "on_demand" | "emergent",
--   "primary_platform": "slack" | "gmail" | "notion" | null,
--   "platform_grounding": [{"platform": "...", "sources": [...], "instruction": "..."}],
--   "freshness_requirement_hours": 4
-- }
ALTER TABLE deliverables
ADD COLUMN IF NOT EXISTS type_classification JSONB DEFAULT '{}';

-- Index for querying by binding type
CREATE INDEX IF NOT EXISTS idx_deliverables_type_classification
ON deliverables USING GIN (type_classification);

-- =============================================================================
-- EMERGENT DELIVERABLE PROPOSALS
-- =============================================================================

-- Track deliverable suggestions made by TP
CREATE TABLE IF NOT EXISTS deliverable_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- What was proposed
    proposed_type TEXT NOT NULL,
    proposed_config JSONB NOT NULL DEFAULT '{}',
    proposed_classification JSONB NOT NULL DEFAULT '{}',

    -- What triggered the proposal
    trigger_pattern TEXT NOT NULL,  -- e.g., "repeated_platform_summary_request"
    trigger_evidence JSONB,         -- Evidence that triggered it

    -- User response
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'accepted', 'dismissed', 'expired')),

    -- If accepted, link to created deliverable
    created_deliverable_id UUID REFERENCES deliverables(id) ON DELETE SET NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    responded_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ DEFAULT (now() + INTERVAL '7 days')
);

-- Index for finding pending proposals
CREATE INDEX IF NOT EXISTS idx_proposals_user_status
ON deliverable_proposals(user_id, status) WHERE status = 'pending';

-- =============================================================================
-- USER INTERACTION PATTERNS
-- =============================================================================

-- Track patterns that suggest deliverable value
CREATE TABLE IF NOT EXISTS user_interaction_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Pattern identification
    pattern_type TEXT NOT NULL,  -- e.g., "platform_summary_request", "meeting_context_gathering"
    pattern_data JSONB NOT NULL DEFAULT '{}',  -- Pattern-specific data (platform, channels, etc.)

    -- Pattern tracking
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Link to proposal if one was generated
    proposed_deliverable_id UUID REFERENCES deliverable_proposals(id) ON DELETE SET NULL,

    -- Unique constraint: one pattern record per user per pattern+data combination
    UNIQUE(user_id, pattern_type, pattern_data)
);

-- Index for pattern detection queries
CREATE INDEX IF NOT EXISTS idx_patterns_user_type
ON user_interaction_patterns(user_id, pattern_type);

-- =============================================================================
-- BACKFILL TYPE CLASSIFICATION FOR EXISTING DELIVERABLES
-- =============================================================================

-- Infer type_classification from existing deliverable_type
UPDATE deliverables
SET type_classification = CASE
    -- Platform-bound types
    WHEN deliverable_type IN ('slack_channel_digest', 'slack_standup') THEN
        jsonb_build_object(
            'binding', 'platform_bound',
            'temporal_pattern', 'scheduled',
            'primary_platform', 'slack',
            'freshness_requirement_hours', 1
        )
    WHEN deliverable_type IN ('gmail_inbox_brief', 'inbox_summary', 'reply_draft', 'follow_up_tracker', 'thread_summary') THEN
        jsonb_build_object(
            'binding', 'platform_bound',
            'temporal_pattern', 'scheduled',
            'primary_platform', 'gmail',
            'freshness_requirement_hours', 1
        )
    WHEN deliverable_type = 'notion_page_summary' THEN
        jsonb_build_object(
            'binding', 'platform_bound',
            'temporal_pattern', 'scheduled',
            'primary_platform', 'notion',
            'freshness_requirement_hours', 4
        )
    -- Cross-platform types
    WHEN deliverable_type IN ('status_report', 'weekly_status', 'cross_platform_digest', 'activity_summary', 'project_brief') THEN
        jsonb_build_object(
            'binding', 'cross_platform',
            'temporal_pattern', 'scheduled',
            'freshness_requirement_hours', 4
        )
    WHEN deliverable_type IN ('meeting_summary', 'one_on_one_prep') THEN
        jsonb_build_object(
            'binding', 'cross_platform',
            'temporal_pattern', 'scheduled',
            'freshness_requirement_hours', 1
        )
    -- Research types
    WHEN deliverable_type = 'research_brief' THEN
        jsonb_build_object(
            'binding', 'research',
            'temporal_pattern', 'on_demand',
            'freshness_requirement_hours', 24
        )
    -- Communication types (stakeholder-facing)
    WHEN deliverable_type IN ('stakeholder_update', 'client_proposal', 'board_update', 'newsletter_section') THEN
        jsonb_build_object(
            'binding', 'cross_platform',
            'temporal_pattern', 'scheduled',
            'freshness_requirement_hours', 4
        )
    -- Beta/other types
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
WHERE type_classification IS NULL OR type_classification = '{}'::jsonb;

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Function to increment pattern occurrence
CREATE OR REPLACE FUNCTION increment_interaction_pattern(
    p_user_id UUID,
    p_pattern_type TEXT,
    p_pattern_data JSONB
) RETURNS user_interaction_patterns AS $$
DECLARE
    result user_interaction_patterns;
BEGIN
    INSERT INTO user_interaction_patterns (user_id, pattern_type, pattern_data)
    VALUES (p_user_id, p_pattern_type, p_pattern_data)
    ON CONFLICT (user_id, pattern_type, pattern_data) DO UPDATE
    SET
        occurrence_count = user_interaction_patterns.occurrence_count + 1,
        last_seen_at = now()
    RETURNING * INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if pattern should trigger proposal
CREATE OR REPLACE FUNCTION should_propose_deliverable(
    p_user_id UUID,
    p_pattern_type TEXT,
    p_pattern_data JSONB,
    p_threshold INTEGER DEFAULT 3
) RETURNS BOOLEAN AS $$
DECLARE
    pattern_record user_interaction_patterns;
    existing_proposal deliverable_proposals;
BEGIN
    -- Get the pattern record
    SELECT * INTO pattern_record
    FROM user_interaction_patterns
    WHERE user_id = p_user_id
      AND pattern_type = p_pattern_type
      AND pattern_data = p_pattern_data;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    -- Check if threshold met
    IF pattern_record.occurrence_count < p_threshold THEN
        RETURN FALSE;
    END IF;

    -- Check if already proposed (and not dismissed/expired)
    SELECT * INTO existing_proposal
    FROM deliverable_proposals
    WHERE user_id = p_user_id
      AND trigger_pattern = p_pattern_type
      AND trigger_evidence @> p_pattern_data
      AND status IN ('pending', 'accepted');

    IF FOUND THEN
        RETURN FALSE;  -- Already proposed or accepted
    END IF;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================================================
-- RLS POLICIES
-- =============================================================================

ALTER TABLE deliverable_proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_interaction_patterns ENABLE ROW LEVEL SECURITY;

-- Proposals: Users can only see their own
CREATE POLICY deliverable_proposals_select ON deliverable_proposals
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY deliverable_proposals_insert ON deliverable_proposals
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY deliverable_proposals_update ON deliverable_proposals
    FOR UPDATE USING (auth.uid() = user_id);

-- Patterns: Users can only see their own
CREATE POLICY user_interaction_patterns_select ON user_interaction_patterns
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY user_interaction_patterns_insert ON user_interaction_patterns
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY user_interaction_patterns_update ON user_interaction_patterns
    FOR UPDATE USING (auth.uid() = user_id);

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE deliverable_proposals IS 'ADR-044: Tracks deliverable suggestions made by TP for emergent discovery';
COMMENT ON TABLE user_interaction_patterns IS 'ADR-044: Tracks user behavior patterns that suggest deliverable value';
COMMENT ON COLUMN deliverables.type_classification IS 'ADR-044: Two-dimensional type classification (binding + temporal_pattern)';
