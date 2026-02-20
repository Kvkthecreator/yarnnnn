-- Migration: 078_user_context_source_ref.sql
-- ADR-072: Unified Content Layer and TP Execution Pipeline
-- Date: 2026-02-20
--
-- Adds provenance tracking to user_context (Memory layer).
-- Every memory entry becomes traceable to its origin.

-- =============================================================================
-- ADD SOURCE REFERENCE COLUMNS
-- =============================================================================

ALTER TABLE user_context
    ADD COLUMN source_ref UUID,
    ADD COLUMN source_type TEXT;

COMMENT ON COLUMN user_context.source_ref IS
'ADR-072: FK to the record that generated this memory entry (session_id, deliverable_version_id, platform_content_id, activity_log_id).';

COMMENT ON COLUMN user_context.source_type IS
'ADR-072: Type of the source record: session_message, deliverable_version, platform_content, activity_log.';

-- =============================================================================
-- INDEX FOR SOURCE LOOKUPS
-- =============================================================================

CREATE INDEX idx_user_context_source_ref
    ON user_context(source_ref)
    WHERE source_ref IS NOT NULL;

-- =============================================================================
-- COMPLETION LOG
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'ADR-072: user_context now has source_ref/source_type for provenance tracking.';
END $$;
