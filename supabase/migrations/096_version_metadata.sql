-- Migration 096: Add metadata JSONB column to deliverable_versions
-- ADR-101: Per-deliverable token tracking and execution metadata
--
-- Stores: {input_tokens, output_tokens, model} per version generation.
-- Enables cost visibility without a separate analytics table.

ALTER TABLE deliverable_versions
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT NULL;

COMMENT ON COLUMN deliverable_versions.metadata IS
  'Execution metadata: model, tokens, tool rounds (ADR-101)';
