-- Migration: 051_suggested_deliverable_status.sql
-- ADR-060: Background Conversation Analyst
-- Date: 2026-02-16
--
-- Adds 'suggested' status for deliverable versions created by the
-- Background Conversation Analyst. These are auto-detected patterns
-- that users can enable, edit, or dismiss.

-- =============================================================================
-- 1. UPDATE VERSION STATUS CONSTRAINT
-- =============================================================================

-- Drop the existing constraint
ALTER TABLE deliverable_versions
DROP CONSTRAINT IF EXISTS deliverable_versions_status_check;

-- Add new constraint including 'suggested'
ALTER TABLE deliverable_versions
ADD CONSTRAINT deliverable_versions_status_check
CHECK (status IN ('generating', 'staged', 'reviewing', 'approved', 'rejected', 'suggested'));

-- =============================================================================
-- 2. ADD ANALYST METADATA COLUMN
-- =============================================================================

-- Analyst metadata for suggested versions
-- Stores: confidence, detected_pattern, source_sessions, detection_reason
ALTER TABLE deliverable_versions
ADD COLUMN IF NOT EXISTS analyst_metadata JSONB DEFAULT NULL;

COMMENT ON COLUMN deliverable_versions.analyst_metadata IS
'ADR-060: Metadata from Conversation Analyst for suggested versions. Contains confidence score, detected pattern type, source session IDs, and detection reason.';

-- =============================================================================
-- 3. INDEXES FOR SUGGESTED STATUS
-- =============================================================================

-- Fast filtering for suggested versions
CREATE INDEX IF NOT EXISTS idx_versions_suggested
ON deliverable_versions(deliverable_id, status)
WHERE status = 'suggested';

-- For analyst queries: find all suggested versions for a user
-- (via join to deliverables)
CREATE INDEX IF NOT EXISTS idx_versions_analyst
ON deliverable_versions(created_at DESC)
WHERE status = 'suggested' AND analyst_metadata IS NOT NULL;

-- =============================================================================
-- 4. HELPER FUNCTION: GET USER'S SUGGESTED DELIVERABLES
-- =============================================================================

CREATE OR REPLACE FUNCTION get_suggested_deliverable_versions(p_user_id UUID)
RETURNS TABLE (
    version_id UUID,
    deliverable_id UUID,
    deliverable_title TEXT,
    deliverable_type TEXT,
    analyst_metadata JSONB,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dv.id as version_id,
        dv.deliverable_id,
        d.title as deliverable_title,
        d.deliverable_type,
        dv.analyst_metadata,
        dv.created_at
    FROM deliverable_versions dv
    JOIN deliverables d ON d.id = dv.deliverable_id
    WHERE d.user_id = p_user_id
      AND dv.status = 'suggested'
    ORDER BY dv.created_at DESC;
END;
$$;

-- =============================================================================
-- 5. COMMENTS
-- =============================================================================

COMMENT ON FUNCTION get_suggested_deliverable_versions IS
'ADR-060: Returns all suggested deliverable versions for a user, ordered by creation date.';
