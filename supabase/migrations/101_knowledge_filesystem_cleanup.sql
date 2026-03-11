-- Migration 101: ADR-107 Knowledge Filesystem — cleanup platform="yarnnn" rows
--
-- Agent-produced outputs now write to workspace_files under /knowledge/
-- instead of platform_content with platform="yarnnn" (ADR-102, now superseded).
--
-- This migration deletes all legacy yarnnn rows from platform_content.
-- Pre-launch data wipe — no backwards compatibility needed.

-- Delete all platform_content rows where platform='yarnnn'
DELETE FROM platform_content WHERE platform = 'yarnnn';
