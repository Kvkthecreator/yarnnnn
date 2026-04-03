-- Migration 139: Drop integration_import_jobs table
-- ADR-153 + ADR-156: Import jobs sunset
--
-- Platform data flows through task execution (Monitor Slack, Monitor Notion),
-- not background import jobs. The import_jobs.py processing module was deleted.
-- No code writes to this table. All readers have been stubbed out.
--
-- This table was created in migration 024, extended in 029, and restored in 046.

DROP TABLE IF EXISTS integration_import_jobs CASCADE;
