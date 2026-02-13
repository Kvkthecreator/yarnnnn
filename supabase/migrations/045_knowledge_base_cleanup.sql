-- Migration: 045_knowledge_base_cleanup.sql
-- ADR-058: Knowledge Base Architecture - Cleanup
-- Date: 2026-02-13
--
-- !!! WARNING: DESTRUCTIVE MIGRATION !!!
-- This migration drops old tables after data has been migrated.
-- Only run AFTER verifying 044_knowledge_base_data_migration.sql succeeded.
--
-- Tables dropped:
--   - user_integrations (→ platform_connections)
--   - ephemeral_context (→ filesystem_items)
--   - documents (→ filesystem_documents)
--   - chunks (→ filesystem_chunks)
--   - context_domains (→ knowledge_domains)
--   - domain_sources (merged into knowledge_domains.sources)
--   - domain_style_profiles (→ knowledge_styles)
--   - deliverable_domains (no longer needed)
--   - memories (user facts → knowledge_entries)
--
-- Columns dropped:
--   - deliverables.domain_id (→ knowledge_domain_id)
--
-- NOTE: Run verification queries from 044 before executing this migration!

-- =============================================================================
-- PHASE 1: VERIFY DATA MIGRATION (Fail-safe)
-- =============================================================================

-- These will raise exceptions if migration didn't happen
DO $$
DECLARE
    old_count INTEGER;
    new_count INTEGER;
BEGIN
    -- Check platform_connections
    SELECT COUNT(*) INTO old_count FROM user_integrations;
    SELECT COUNT(*) INTO new_count FROM platform_connections;
    IF old_count > 0 AND new_count = 0 THEN
        RAISE EXCEPTION 'Migration failed: platform_connections is empty but user_integrations has % rows', old_count;
    END IF;

    -- Check filesystem_items
    SELECT COUNT(*) INTO old_count FROM ephemeral_context;
    SELECT COUNT(*) INTO new_count FROM filesystem_items;
    IF old_count > 0 AND new_count = 0 THEN
        RAISE EXCEPTION 'Migration failed: filesystem_items is empty but ephemeral_context has % rows', old_count;
    END IF;

    -- Check filesystem_documents
    SELECT COUNT(*) INTO old_count FROM documents;
    SELECT COUNT(*) INTO new_count FROM filesystem_documents;
    IF old_count > 0 AND new_count = 0 THEN
        RAISE EXCEPTION 'Migration failed: filesystem_documents is empty but documents has % rows', old_count;
    END IF;

    -- Check knowledge_domains
    SELECT COUNT(*) INTO old_count FROM context_domains;
    SELECT COUNT(*) INTO new_count FROM knowledge_domains;
    IF old_count > 0 AND new_count = 0 THEN
        RAISE EXCEPTION 'Migration failed: knowledge_domains is empty but context_domains has % rows', old_count;
    END IF;

    RAISE NOTICE 'Migration verification passed. Proceeding with cleanup.';
END $$;


-- =============================================================================
-- PHASE 2: DROP FOREIGN KEY CONSTRAINTS (Dependencies)
-- =============================================================================

-- Drop FK from deliverables to context_domains
ALTER TABLE deliverables
    DROP CONSTRAINT IF EXISTS deliverables_domain_id_fkey;

-- Drop FK from memories to context_domains
ALTER TABLE memories
    DROP CONSTRAINT IF EXISTS memories_domain_id_fkey;

-- Drop FK from chat_sessions to context_domains (if exists)
ALTER TABLE chat_sessions
    DROP CONSTRAINT IF EXISTS chat_sessions_domain_id_fkey;

-- Drop FK from deliverable_domains
ALTER TABLE deliverable_domains
    DROP CONSTRAINT IF EXISTS deliverable_domains_deliverable_id_fkey,
    DROP CONSTRAINT IF EXISTS deliverable_domains_domain_id_fkey;

-- Drop FK from domain_sources
ALTER TABLE domain_sources
    DROP CONSTRAINT IF EXISTS domain_sources_domain_id_fkey;

-- Drop FK from domain_style_profiles
ALTER TABLE domain_style_profiles
    DROP CONSTRAINT IF EXISTS domain_style_profiles_domain_id_fkey;


-- =============================================================================
-- PHASE 3: DROP OLD COLUMNS
-- =============================================================================

-- Remove old domain_id from deliverables (replaced by knowledge_domain_id)
ALTER TABLE deliverables
    DROP COLUMN IF EXISTS domain_id;

-- Rename knowledge_domain_id to domain_id for cleaner API
ALTER TABLE deliverables
    RENAME COLUMN knowledge_domain_id TO domain_id;

-- Remove old project_id from memories (if still exists)
ALTER TABLE memories
    DROP COLUMN IF EXISTS project_id;


-- =============================================================================
-- PHASE 4: DROP OLD TABLES
-- =============================================================================

-- Drop junction/helper tables first
DROP TABLE IF EXISTS deliverable_domains CASCADE;
DROP TABLE IF EXISTS domain_sources CASCADE;
DROP TABLE IF EXISTS domain_style_profiles CASCADE;

-- Drop main old tables
DROP TABLE IF EXISTS context_domains CASCADE;
DROP TABLE IF EXISTS memories CASCADE;
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS ephemeral_context CASCADE;
DROP TABLE IF EXISTS user_integrations CASCADE;

-- Drop deprecated tables (if any still exist)
DROP TABLE IF EXISTS integration_coverage CASCADE;
DROP TABLE IF EXISTS integration_import_jobs CASCADE;


-- =============================================================================
-- PHASE 5: CLEANUP OLD FUNCTIONS
-- =============================================================================

DROP FUNCTION IF EXISTS get_or_create_default_domain(UUID);  -- Old version
DROP FUNCTION IF EXISTS find_domain_for_source(UUID, TEXT, TEXT);
DROP FUNCTION IF EXISTS get_deliverable_domain(UUID);
DROP FUNCTION IF EXISTS search_memories(UUID, TEXT, UUID, INTEGER);
DROP FUNCTION IF EXISTS get_memories_by_importance(UUID, UUID, INTEGER);
DROP FUNCTION IF EXISTS compute_coverage_state(TIMESTAMPTZ, INTEGER, TEXT);
DROP FUNCTION IF EXISTS get_coverage_summary(UUID, TEXT);


-- =============================================================================
-- PHASE 6: ADD NEW FOREIGN KEY CONSTRAINTS
-- =============================================================================

-- Ensure deliverables.domain_id points to knowledge_domains
ALTER TABLE deliverables
    ADD CONSTRAINT deliverables_domain_id_fkey
    FOREIGN KEY (domain_id) REFERENCES knowledge_domains(id) ON DELETE SET NULL;

-- Ensure chat_sessions.domain_id points to knowledge_domains
ALTER TABLE chat_sessions
    ADD CONSTRAINT chat_sessions_domain_id_fkey
    FOREIGN KEY (domain_id) REFERENCES knowledge_domains(id) ON DELETE SET NULL;


-- =============================================================================
-- PHASE 7: COMMENTS
-- =============================================================================

COMMENT ON TABLE platform_connections IS
'ADR-058: OAuth connections to external platforms. Canonical table (user_integrations dropped).';

COMMENT ON TABLE filesystem_items IS
'ADR-058: Synced platform content. Canonical table (ephemeral_context dropped).';

COMMENT ON TABLE filesystem_documents IS
'ADR-058: Uploaded documents. Canonical table (documents dropped).';

COMMENT ON TABLE filesystem_chunks IS
'ADR-058: Document chunks. Canonical table (chunks dropped).';

COMMENT ON TABLE knowledge_domains IS
'ADR-058: Work domains. Canonical table (context_domains dropped).';

COMMENT ON TABLE knowledge_entries IS
'ADR-058: Knowledge entries. Canonical table (memories dropped for user facts).';


-- =============================================================================
-- PHASE 8: FINAL VERIFICATION
-- =============================================================================

DO $$
DECLARE
    table_count INTEGER;
BEGIN
    -- Verify old tables are gone
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN (
          'user_integrations',
          'ephemeral_context',
          'documents',
          'chunks',
          'context_domains',
          'domain_sources',
          'domain_style_profiles',
          'deliverable_domains',
          'memories'
      );

    IF table_count > 0 THEN
        RAISE WARNING 'Some old tables still exist: %', table_count;
    ELSE
        RAISE NOTICE 'Cleanup complete. All old tables dropped successfully.';
    END IF;
END $$;
