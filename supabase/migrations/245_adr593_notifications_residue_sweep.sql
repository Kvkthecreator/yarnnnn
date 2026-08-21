-- Migration 245 — ADR-593 D6: the notifications residue sweep.
--
-- Production measured 2026-08-21 before writing this file:
--   notifications: 0 rows (the outbound seam never sent — ADR-593 §2 F1)
--   email_delivery_log: 0 rows (write-only by construction; RLS joins through
--     the dead scheduled_messages parent; zero readers)
--   scheduled_messages: 0 rows (zero code references since migration 093)
--   workspaces WHERE digest_enabled: 0
--   member_state WHERE key='notification_prefs': 0 rows
--
-- Everything dropped here is measured-empty AND reference-free in code
-- (verified by grep 2026-08-21; the one near-miss — workspaces.owner_email,
-- read by routes/admin.py — is deliberately KEPT).
--
-- No BEGIN/COMMIT: the runner supplies the transaction (--single-transaction).

-- ---------------------------------------------------------------------------
-- 1. notifications — transport-only CHECKs (ADR-410 D3 / ADR-593 D3).
--    Email is the only channel code can write ('in_app' died with ADR-410 D3;
--    zero historical rows exist, so the tightened CHECK validates instantly).
--    The source_type enum was decorative (a code-controlled label whose list
--    already drifted out-of-band from the 041 file) — dropped, not re-pinned.
-- ---------------------------------------------------------------------------
ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_channel_check;
ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_source_type_check;
ALTER TABLE notifications ADD CONSTRAINT notifications_channel_check CHECK (channel = 'email');

-- ---------------------------------------------------------------------------
-- 2. The ADR-040-era weekly-digest machinery, dead since migration 093
--    dropped its walker. Children first (email_delivery_log FKs the parent).
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS email_delivery_log;
DROP TABLE IF EXISTS scheduled_messages;

ALTER TABLE workspaces
  DROP COLUMN IF EXISTS digest_enabled,
  DROP COLUMN IF EXISTS digest_day,
  DROP COLUMN IF EXISTS digest_hour,
  DROP COLUMN IF EXISTS digest_timezone;

-- Orphaned since migration 098 dropped event_trigger_log itself.
DROP FUNCTION IF EXISTS cleanup_old_trigger_logs();

-- ---------------------------------------------------------------------------
-- 3. member_state notification_prefs — the ADR-593 D2 shape re-cut.
--    Zero rows exist in production; this clears any legacy-shaped stragglers
--    (the old {delivery_email, failure_email, witness_email} keys) so the
--    schema-checked v2 writer starts from a clean slate. Losing a legacy row
--    means losing nothing: the seam those prefs gated never sent (F1).
-- ---------------------------------------------------------------------------
DELETE FROM member_state
WHERE key = 'notification_prefs'
  AND (value ? 'delivery_email' OR value ? 'failure_email' OR value ? 'witness_email');
