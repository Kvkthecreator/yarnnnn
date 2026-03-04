-- Restore event trigger columns on deliverables
-- These were defined in migration 031 but are absent from the live schema.
-- Required for reactive deliverables (ADR-092) and existing event trigger logic.

ALTER TABLE deliverables ADD COLUMN IF NOT EXISTS trigger_type text NOT NULL DEFAULT 'schedule'
  CONSTRAINT deliverables_trigger_type_check CHECK (trigger_type = ANY (ARRAY['schedule'::text, 'event'::text, 'manual'::text]));

ALTER TABLE deliverables ADD COLUMN IF NOT EXISTS trigger_config JSONB NULL;

ALTER TABLE deliverables ADD COLUMN IF NOT EXISTS last_triggered_at timestamptz NULL;
