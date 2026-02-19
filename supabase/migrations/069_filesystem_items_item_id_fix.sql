-- Migration: 069_filesystem_items_item_id_fix.sql
-- Fixes filesystem_items deduplication: item_id was being stored as uuid4() (same as id)
-- instead of the platform-native identifier (message_ts, message_id, event_id, page_id).
-- All existing rows have incorrect item_id values and cannot be corrected in place.
-- filesystem_items is a TTL cache — truncating and letting the next sync repopulate is correct.

-- Clear stale data with incorrect item_ids.
-- The next platform sync will repopulate with correct platform-native item_ids.
TRUNCATE TABLE filesystem_items;

-- The UNIQUE constraint on (user_id, platform, resource_id, item_id) is already correct.
-- The platform_worker now passes item_id explicitly and uses on_conflict on all four columns.
-- No constraint change needed — confirming it exists:
-- "filesystem_items_user_id_platform_resource_id_item_id_key"
