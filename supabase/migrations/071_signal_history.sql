-- Migration: 071_signal_history.sql
-- ADR-068 Phase 4: Per-signal deduplication tracking
--
-- Prevents re-creating signal-emergent deliverables for the same signal within
-- the deduplication window. For example, don't create multiple meeting_prep
-- deliverables for the same calendar event even if signal processing runs
-- multiple times before the event.
--
-- Deduplication windows (enforced in signal_processing.py logic):
-- - meeting_prep: 24 hours (same event)
-- - silence_alert: 7 days (same Gmail thread)
-- - contact_drift: 14 days (same contact)

CREATE TABLE IF NOT EXISTS signal_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    signal_type TEXT NOT NULL,
    signal_ref TEXT NOT NULL,
    last_triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deliverable_id UUID REFERENCES deliverables(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, signal_type, signal_ref)
);

CREATE INDEX idx_signal_history_user_type ON signal_history(user_id, signal_type);
CREATE INDEX idx_signal_history_triggered ON signal_history(last_triggered_at);

COMMENT ON TABLE signal_history IS 'ADR-068: Tracks when signals were last triggered to prevent duplicate deliverable creation within deduplication windows';
COMMENT ON COLUMN signal_history.signal_type IS 'meeting_prep, silence_alert, contact_drift, etc.';
COMMENT ON COLUMN signal_history.signal_ref IS 'Platform-native identifier: event_id for calendar, thread_id for Gmail, contact email for drift';
COMMENT ON COLUMN signal_history.last_triggered_at IS 'When this signal last created a deliverable. Used to enforce deduplication windows.';
COMMENT ON COLUMN signal_history.deliverable_id IS 'The signal-emergent deliverable created for this signal (NULL if deleted)';
