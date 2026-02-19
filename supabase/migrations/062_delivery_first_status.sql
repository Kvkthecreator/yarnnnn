-- Migration: 062_delivery_first_status.sql
-- ADR-066: Delivery-First, No Governance
-- Date: 2026-02-19
--
-- Adds 'delivered' and 'failed' status for deliverable versions.
-- These replace the governance workflow (staged → approved/rejected)
-- with immediate delivery (generating → delivered/failed).

-- =============================================================================
-- 1. UPDATE VERSION STATUS CONSTRAINT
-- =============================================================================

-- Drop the existing constraint
ALTER TABLE deliverable_versions
DROP CONSTRAINT IF EXISTS deliverable_versions_status_check;

-- Add new constraint including 'delivered' and 'failed'
-- Legacy statuses (staged, reviewing, approved, rejected, suggested) kept for backwards compatibility
ALTER TABLE deliverable_versions
ADD CONSTRAINT deliverable_versions_status_check
CHECK (status IN (
    'generating',   -- Currently being created
    'staged',       -- LEGACY: Awaiting review (kept for backwards compat)
    'reviewing',    -- LEGACY: Under review
    'approved',     -- LEGACY: Approved for delivery
    'rejected',     -- LEGACY: Rejected by user
    'suggested',    -- ADR-060: Auto-detected by analyst
    'delivered',    -- ADR-066: Successfully delivered
    'failed'        -- ADR-066: Generation or delivery failed
));

-- =============================================================================
-- 2. INDEXES FOR NEW STATUSES
-- =============================================================================

-- Fast filtering for delivered versions
CREATE INDEX IF NOT EXISTS idx_versions_delivered
ON deliverable_versions(deliverable_id, delivered_at DESC)
WHERE status = 'delivered';

-- Fast filtering for failed versions (for retry logic)
CREATE INDEX IF NOT EXISTS idx_versions_failed
ON deliverable_versions(deliverable_id, created_at DESC)
WHERE status = 'failed';

-- =============================================================================
-- 3. COMMENTS
-- =============================================================================

COMMENT ON COLUMN deliverable_versions.status IS
'ADR-066: Version status. New delivery-first model uses generating→delivered|failed. Legacy governance statuses (staged, reviewing, approved, rejected) kept for backwards compatibility.';
