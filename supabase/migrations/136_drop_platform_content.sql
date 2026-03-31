-- ADR-153: Platform Content Sunset
-- Drop the platform_content table and related RPC functions.
-- Platform data now flows through tasks into workspace context domains.
--
-- Preserved tables: platform_connections (OAuth), sync_registry (observability),
-- integration_import_jobs (context imports)

-- Drop the RPC function first (depends on the table)
DROP FUNCTION IF EXISTS mark_content_retained(uuid, text);

-- Drop the table
DROP TABLE IF EXISTS platform_content;
