-- Migration: 084_rename_user_context_to_user_memory.sql
-- ADR-087: Deliverable Scoped Context — naming debt resolution
-- Date: 2026-03-03
--
-- Renames user_context → user_memory to align with canonical naming
-- conventions (naming-conventions.md). "Memory" is the Tier 1 user-facing
-- term; the table stores accumulated user knowledge, not assembled context.

-- =============================================================================
-- 1. RENAME TABLE
-- =============================================================================

ALTER TABLE user_context RENAME TO user_memory;

-- =============================================================================
-- 2. RENAME INDEXES
-- =============================================================================

ALTER INDEX user_context_user_id_idx RENAME TO user_memory_user_id_idx;
ALTER INDEX idx_user_context_source_ref RENAME TO idx_user_memory_source_ref;

-- =============================================================================
-- 3. RENAME RLS POLICY
-- =============================================================================

ALTER POLICY "Users can manage their own context" ON user_memory
  RENAME TO "Users can manage their own memory";

-- =============================================================================
-- 4. RENAME UNIQUE CONSTRAINT
-- =============================================================================

ALTER TABLE user_memory RENAME CONSTRAINT user_context_user_key_unique
  TO user_memory_user_key_unique;

-- =============================================================================
-- 5. COMMENTS
-- =============================================================================

COMMENT ON TABLE user_memory IS
'ADR-059 + ADR-087: Single flat key-value Memory store. Renamed from user_context to align with naming conventions. Stores user preferences, profile info, and extracted knowledge.';
