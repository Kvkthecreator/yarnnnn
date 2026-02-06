-- Migration: 025_destination_first.sql
-- ADR-028: Destination-First Deliverables & Governance Model
-- Date: 2026-02-06
--
-- Elevates destination from an afterthought to a first-class part of the deliverable model.
-- Key insight: "The deliverable isn't the content. It's the commitment to deliver
-- something to a destination at the right time."

-- =============================================================================
-- 1. ADD DESTINATION AND GOVERNANCE TO DELIVERABLES
-- =============================================================================

-- Destination: Where this deliverable is delivered
-- Schema: { platform, target, format?, options? }
-- Examples:
--   { "platform": "slack", "target": "#team-updates", "format": "message" }
--   { "platform": "notion", "target": "page-id", "format": "page" }
--   { "platform": "email", "target": "sarah@company.com", "format": "html" }
--   { "platform": "download", "target": null, "format": "markdown" }
ALTER TABLE deliverables
ADD COLUMN IF NOT EXISTS destination JSONB;

-- Governance: How much supervision is required
-- manual = user must click export after approval
-- semi_auto = export triggers automatically on approval
-- full_auto = skip staging entirely, deliver on generation (future)
ALTER TABLE deliverables
ADD COLUMN IF NOT EXISTS governance TEXT DEFAULT 'manual'
    CHECK (governance IN ('manual', 'semi_auto', 'full_auto'));

-- Index for querying by platform (common for analytics and batch operations)
CREATE INDEX IF NOT EXISTS idx_deliverables_destination_platform
ON deliverables ((destination->>'platform'))
WHERE destination IS NOT NULL;

-- Index for governance-based queries
CREATE INDEX IF NOT EXISTS idx_deliverables_governance
ON deliverables (governance)
WHERE governance != 'manual';


-- =============================================================================
-- 2. ADD DELIVERY TRACKING TO VERSIONS
-- =============================================================================

-- Track delivery status per version
ALTER TABLE deliverable_versions
ADD COLUMN IF NOT EXISTS delivery_status TEXT DEFAULT NULL
    CHECK (delivery_status IN ('pending', 'delivering', 'delivered', 'failed', NULL));

-- External reference from delivery (e.g., Slack message ID, Notion page ID)
ALTER TABLE deliverable_versions
ADD COLUMN IF NOT EXISTS delivery_external_id TEXT;

-- External URL to the delivered content
ALTER TABLE deliverable_versions
ADD COLUMN IF NOT EXISTS delivery_external_url TEXT;

-- When delivery was completed
ALTER TABLE deliverable_versions
ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ;

-- Delivery error if failed
ALTER TABLE deliverable_versions
ADD COLUMN IF NOT EXISTS delivery_error TEXT;


-- =============================================================================
-- 3. COMMENTS
-- =============================================================================

COMMENT ON COLUMN deliverables.destination IS
'ADR-028: First-class destination where deliverable is sent. Schema: {platform, target, format?, options?}';

COMMENT ON COLUMN deliverables.governance IS
'ADR-028: Supervision level - manual (click export), semi_auto (auto on approve), full_auto (skip staging)';

COMMENT ON COLUMN deliverable_versions.delivery_status IS
'ADR-028: Status of delivery to destination - pending/delivering/delivered/failed';

COMMENT ON COLUMN deliverable_versions.delivery_external_id IS
'ADR-028: External ID from platform (e.g., Slack message ts, Notion page id)';

COMMENT ON COLUMN deliverable_versions.delivery_external_url IS
'ADR-028: URL to view the delivered content on the platform';


-- =============================================================================
-- 4. NOTE ON MIGRATION
-- =============================================================================

-- Existing deliverables will have:
--   destination = NULL (means manual export with destination picker)
--   governance = 'manual' (current behavior preserved)
--
-- This is intentionally non-breaking:
-- - destination NULL = show destination picker on export
-- - governance 'manual' = require explicit export click
--
-- No data migration needed for existing deliverables.
