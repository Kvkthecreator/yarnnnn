-- Migration: 059_drop_dead_columns.sql
-- ADR-059: Remove dead columns from session_messages
--
-- knowledge_extracted and knowledge_extracted_at were added in migration 043
-- as placeholders for background knowledge extraction from conversations.
-- That pipeline was removed in ADR-059 (no background inference).
-- These columns have zero reads or writes in application code.

ALTER TABLE session_messages
    DROP COLUMN IF EXISTS knowledge_extracted,
    DROP COLUMN IF EXISTS knowledge_extracted_at;
