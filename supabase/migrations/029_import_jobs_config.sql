-- Migration: 029_import_jobs_config
-- Description: Add config and scope columns to integration_import_jobs
-- See ADR-030: Context Extraction Methodology

-- Add config column for import configuration (learn_style, etc.)
ALTER TABLE integration_import_jobs
ADD COLUMN IF NOT EXISTS config JSONB;

-- Add scope column for extraction scope (recency_days, max_items, etc.)
ALTER TABLE integration_import_jobs
ADD COLUMN IF NOT EXISTS scope JSONB;

-- Update provider constraint to include gmail
ALTER TABLE integration_import_jobs
DROP CONSTRAINT IF EXISTS valid_provider;

ALTER TABLE integration_import_jobs
ADD CONSTRAINT valid_provider CHECK (provider IN ('slack', 'notion', 'gmail'));

-- Add comment for documentation
COMMENT ON COLUMN integration_import_jobs.config IS 'Import configuration: {learn_style: boolean}';
COMMENT ON COLUMN integration_import_jobs.scope IS 'Extraction scope: {recency_days: int, max_items: int, include_threads: boolean}';
