-- ADR-092: Deliverable Intelligence & Mode Taxonomy
-- Phase 1: Schema changes only — extend constraints, add proactive column
-- No behavioral changes. Signal processing code untouched.

-- 1. Extend mode CHECK constraint to include reactive, proactive, coordinator
ALTER TABLE deliverables DROP CONSTRAINT IF EXISTS deliverables_mode_check;
ALTER TABLE deliverables ADD CONSTRAINT deliverables_mode_check
  CHECK (mode = ANY (ARRAY['recurring'::text, 'goal'::text, 'reactive'::text, 'proactive'::text, 'coordinator'::text]));

-- 2. Extend origin CHECK constraint to include coordinator_created
ALTER TABLE deliverables DROP CONSTRAINT IF EXISTS deliverables_origin_check;
ALTER TABLE deliverables ADD CONSTRAINT deliverables_origin_check
  CHECK (origin = ANY (ARRAY['user_configured'::text, 'analyst_suggested'::text, 'signal_emergent'::text, 'coordinator_created'::text]));

-- 3. Add proactive_next_review_at for proactive/coordinator mode scheduling
ALTER TABLE deliverables ADD COLUMN IF NOT EXISTS proactive_next_review_at timestamptz NULL;
