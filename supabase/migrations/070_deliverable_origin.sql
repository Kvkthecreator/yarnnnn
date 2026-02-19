-- Migration: 070_deliverable_origin.sql
-- ADR-068: Signal-Emergent Deliverables
-- Adds origin column to deliverables to distinguish how a deliverable came to exist.
--
-- Origins:
--   user_configured   -- Created by user via UI or TP (current default, all existing rows)
--   analyst_suggested -- Created by Conversation Analyst (ADR-060) from TP session patterns
--   signal_emergent   -- Created by Signal Processing phase from platform activity signal

ALTER TABLE deliverables
    ADD COLUMN IF NOT EXISTS origin TEXT NOT NULL DEFAULT 'user_configured'
    CHECK (origin IN ('user_configured', 'analyst_suggested', 'signal_emergent'));

-- Index for scheduler queries: "give me all signal_emergent deliverables for this user"
CREATE INDEX IF NOT EXISTS idx_deliverables_origin
    ON deliverables(user_id, origin)
    WHERE origin != 'user_configured';
