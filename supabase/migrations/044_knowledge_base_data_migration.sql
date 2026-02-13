-- Migration: 044_knowledge_base_data_migration.sql
-- ADR-058: Knowledge Base Architecture - Data Migration
-- Date: 2026-02-13
--
-- This migration moves data from old tables to new tables:
--   user_integrations    → platform_connections
--   ephemeral_context    → filesystem_items
--   documents            → filesystem_documents
--   chunks               → filesystem_chunks
--   context_domains      → knowledge_domains
--   memories (user facts)→ knowledge_entries
--
-- Run AFTER 043_knowledge_base_architecture.sql

-- =============================================================================
-- PHASE 1: MIGRATE PLATFORM CONNECTIONS
-- =============================================================================

INSERT INTO platform_connections (
    id,
    user_id,
    platform,
    status,
    credentials_encrypted,
    refresh_token_encrypted,
    metadata,
    settings,
    last_synced_at,
    landscape,
    landscape_discovered_at,
    created_at,
    updated_at
)
SELECT
    id,
    user_id,
    provider as platform,
    status,
    access_token_encrypted as credentials_encrypted,
    refresh_token_encrypted,
    metadata,
    '{}'::JSONB as settings,
    last_used_at as last_synced_at,  -- Use last_used_at as proxy
    landscape,
    landscape_discovered_at,
    created_at,
    updated_at
FROM user_integrations
ON CONFLICT (user_id, platform) DO UPDATE SET
    status = EXCLUDED.status,
    credentials_encrypted = EXCLUDED.credentials_encrypted,
    refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
    metadata = EXCLUDED.metadata,
    settings = EXCLUDED.settings,
    last_synced_at = EXCLUDED.last_synced_at,
    landscape = EXCLUDED.landscape,
    landscape_discovered_at = EXCLUDED.landscape_discovered_at,
    updated_at = now();


-- =============================================================================
-- PHASE 2: MIGRATE FILESYSTEM ITEMS
-- =============================================================================

-- ephemeral_context doesn't have item_id, generate from content hash
INSERT INTO filesystem_items (
    id,
    user_id,
    platform,
    resource_id,
    resource_name,
    item_id,
    content,
    content_type,
    title,
    author,
    author_id,
    is_user_authored,
    source_timestamp,
    synced_at,
    expires_at,
    metadata,
    sync_metadata
)
SELECT
    id,
    user_id,
    platform,
    resource_id,
    resource_name,
    id::text as item_id,  -- Use the row ID as item_id since original doesn't have it
    content,
    content_type,
    platform_metadata->>'subject' as title,
    platform_metadata->>'author' as author,
    platform_metadata->>'author_id' as author_id,
    COALESCE((platform_metadata->>'is_user_authored')::BOOLEAN, false) as is_user_authored,
    source_timestamp,
    created_at as synced_at,
    expires_at,
    platform_metadata as metadata,
    COALESCE(sync_metadata, '{}')::JSONB as sync_metadata
FROM ephemeral_context
ON CONFLICT (user_id, platform, resource_id, item_id) DO UPDATE SET
    content = EXCLUDED.content,
    content_type = EXCLUDED.content_type,
    title = EXCLUDED.title,
    author = EXCLUDED.author,
    source_timestamp = EXCLUDED.source_timestamp,
    synced_at = EXCLUDED.synced_at,
    expires_at = EXCLUDED.expires_at,
    metadata = EXCLUDED.metadata,
    sync_metadata = EXCLUDED.sync_metadata;


-- =============================================================================
-- PHASE 3: MIGRATE DOCUMENTS
-- =============================================================================

INSERT INTO filesystem_documents (
    id,
    user_id,
    filename,
    file_type,
    file_size,
    storage_path,
    processing_status,
    processed_at,
    error_message,
    page_count,
    word_count,
    uploaded_at
)
SELECT
    id,
    user_id,
    filename,
    file_type,
    file_size,
    COALESCE(storage_path, file_url) as storage_path,  -- Use file_url if storage_path is null
    processing_status,
    processed_at,
    error_message,
    page_count,
    word_count,
    created_at as uploaded_at  -- documents uses created_at not uploaded_at
FROM documents
WHERE user_id IS NOT NULL  -- Only migrate documents with user_id
ON CONFLICT (id) DO NOTHING;


-- =============================================================================
-- PHASE 4: MIGRATE CHUNKS
-- =============================================================================

INSERT INTO filesystem_chunks (
    id,
    document_id,
    content,
    chunk_index,
    page_number,
    embedding,
    token_count,
    metadata,
    created_at
)
SELECT
    c.id,
    c.document_id,
    c.content,
    c.chunk_index,
    c.page_number,
    c.embedding,
    c.token_count,
    COALESCE(c.metadata, '{}')::JSONB as metadata,
    c.created_at
FROM chunks c
-- Only migrate chunks where document exists in new table
WHERE EXISTS (
    SELECT 1 FROM filesystem_documents fd WHERE fd.id = c.document_id
)
ON CONFLICT (id) DO NOTHING;


-- =============================================================================
-- PHASE 5: MIGRATE DOMAINS
-- =============================================================================

INSERT INTO knowledge_domains (
    id,
    user_id,
    name,
    name_source,
    summary,
    sources,
    is_default,
    is_active,
    created_at,
    updated_at
)
SELECT
    id,
    user_id,
    name,
    name_source,
    NULL as summary,  -- Will be populated by inference
    COALESCE(
        (SELECT jsonb_agg(jsonb_build_object(
            'platform', ds.provider,
            'resource_id', ds.resource_id,
            'resource_name', ds.resource_name
        ))
        FROM domain_sources ds
        WHERE ds.domain_id = cd.id),
        '[]'::JSONB
    ) as sources,
    is_default,
    true as is_active,
    created_at,
    updated_at
FROM context_domains cd
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    sources = EXCLUDED.sources,
    is_default = EXCLUDED.is_default,
    updated_at = now();


-- =============================================================================
-- PHASE 6: MIGRATE USER-STATED MEMORIES TO KNOWLEDGE ENTRIES
-- =============================================================================

INSERT INTO knowledge_entries (
    id,
    user_id,
    domain_id,
    content,
    entry_type,
    source,
    source_ref,
    confidence,
    tags,
    importance,
    is_active,
    created_at,
    updated_at
)
SELECT
    id,
    user_id,
    domain_id,
    content,
    CASE
        WHEN 'preference' = ANY(tags) THEN 'preference'
        WHEN 'instruction' = ANY(tags) THEN 'instruction'
        WHEN 'decision' = ANY(tags) THEN 'decision'
        ELSE 'fact'
    END as entry_type,
    CASE source_type
        WHEN 'user_stated' THEN 'user_stated'
        WHEN 'chat' THEN 'conversation'
        WHEN 'conversation' THEN 'conversation'
        WHEN 'document' THEN 'document'
        ELSE 'inferred'
    END as source,
    source_ref,
    NULL as confidence,  -- User-stated entries don't need confidence
    tags,
    importance,
    is_active,
    created_at,
    updated_at
FROM memories
WHERE source_type IN ('user_stated', 'chat', 'conversation', 'manual')
ON CONFLICT (id) DO UPDATE SET
    content = EXCLUDED.content,
    entry_type = EXCLUDED.entry_type,
    tags = EXCLUDED.tags,
    importance = EXCLUDED.importance,
    is_active = EXCLUDED.is_active,
    updated_at = now();


-- =============================================================================
-- PHASE 7: CREATE DEFAULT PROFILE FOR EACH USER
-- =============================================================================

INSERT INTO knowledge_profile (user_id)
SELECT DISTINCT user_id
FROM platform_connections
WHERE user_id NOT IN (SELECT user_id FROM knowledge_profile)
ON CONFLICT (user_id) DO NOTHING;

-- Also create for users with knowledge entries but no platform connections
INSERT INTO knowledge_profile (user_id)
SELECT DISTINCT user_id
FROM knowledge_entries
WHERE user_id NOT IN (SELECT user_id FROM knowledge_profile)
ON CONFLICT (user_id) DO NOTHING;


-- =============================================================================
-- PHASE 8: CREATE DEFAULT DOMAIN FOR USERS WITHOUT ONE
-- =============================================================================

INSERT INTO knowledge_domains (user_id, name, name_source, is_default)
SELECT DISTINCT kp.user_id, 'Personal', 'system', true
FROM knowledge_profile kp
WHERE NOT EXISTS (
    SELECT 1 FROM knowledge_domains kd
    WHERE kd.user_id = kp.user_id AND kd.is_default = true
)
ON CONFLICT DO NOTHING;


-- =============================================================================
-- PHASE 9: UPDATE DELIVERABLES TO USE NEW DOMAIN REFERENCES
-- =============================================================================

-- Deliverables don't have domain_id yet, knowledge_domain_id was added by 043
-- We'll link deliverables to domains based on user's default domain
UPDATE deliverables d
SET knowledge_domain_id = (
    SELECT kd.id
    FROM knowledge_domains kd
    WHERE kd.user_id = d.user_id AND kd.is_default = true
    LIMIT 1
)
WHERE d.knowledge_domain_id IS NULL;


-- =============================================================================
-- PHASE 10: UPDATE CHAT SESSIONS TO USE NEW DOMAIN REFERENCES
-- =============================================================================

-- Map old domain_id to new if it exists
UPDATE chat_sessions cs
SET domain_id = (
    SELECT kd.id
    FROM knowledge_domains kd
    WHERE kd.user_id = cs.user_id
      AND kd.is_default = true
    LIMIT 1
)
WHERE cs.domain_id IS NULL;


-- =============================================================================
-- PHASE 11: VERIFICATION QUERIES (Run manually to verify)
-- =============================================================================

-- Uncomment these to verify migration:
/*
-- Count comparison
SELECT 'user_integrations' as old_table, COUNT(*) FROM user_integrations
UNION ALL
SELECT 'platform_connections' as new_table, COUNT(*) FROM platform_connections;

SELECT 'ephemeral_context' as old_table, COUNT(*) FROM ephemeral_context
UNION ALL
SELECT 'filesystem_items' as new_table, COUNT(*) FROM filesystem_items;

SELECT 'documents' as old_table, COUNT(*) FROM documents
UNION ALL
SELECT 'filesystem_documents' as new_table, COUNT(*) FROM filesystem_documents;

SELECT 'chunks' as old_table, COUNT(*) FROM chunks
UNION ALL
SELECT 'filesystem_chunks' as new_table, COUNT(*) FROM filesystem_chunks;

SELECT 'context_domains' as old_table, COUNT(*) FROM context_domains
UNION ALL
SELECT 'knowledge_domains' as new_table, COUNT(*) FROM knowledge_domains;

SELECT 'memories (user facts)' as old_table, COUNT(*) FROM memories
WHERE source_type IN ('user_stated', 'chat', 'conversation', 'manual')
UNION ALL
SELECT 'knowledge_entries' as new_table, COUNT(*) FROM knowledge_entries;

SELECT 'users with profile' as metric, COUNT(*) FROM knowledge_profile;
SELECT 'users with default domain' as metric, COUNT(*) FROM knowledge_domains WHERE is_default = true;
*/


-- =============================================================================
-- PHASE 12: COMMENTS
-- =============================================================================

COMMENT ON COLUMN deliverables.knowledge_domain_id IS
'ADR-058: Reference to knowledge_domains table. Replaces domain_id which referenced context_domains.';
