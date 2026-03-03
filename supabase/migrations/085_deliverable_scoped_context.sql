-- Migration: 085_deliverable_scoped_context.sql
-- ADR-087: Deliverable Scoped Context — Phase 1 (Schema + Read Paths)
-- Date: 2026-03-03
--
-- Adds per-deliverable instructions and memory, plus session routing.
-- This enables TP chat and headless generation to share context per deliverable.

-- =============================================================================
-- 1. NEW COLUMNS ON deliverables
-- =============================================================================

-- User-authored behavioral directives (like CLAUDE.md or AGENTS.md)
ALTER TABLE deliverables
ADD COLUMN IF NOT EXISTS deliverable_instructions TEXT NOT NULL DEFAULT '';

COMMENT ON COLUMN deliverables.deliverable_instructions IS
'ADR-087: User-authored behavioral directives for this deliverable. Plain text or markdown. Examples: "Use formal tone", "Focus on trends". Separate from template_structure (format) and type_config (type settings).';

-- System-accumulated knowledge (session summaries, feedback, observations)
ALTER TABLE deliverables
ADD COLUMN IF NOT EXISTS deliverable_memory JSONB NOT NULL DEFAULT '{}';

COMMENT ON COLUMN deliverables.deliverable_memory IS
'ADR-087: System-accumulated knowledge about this deliverable. Structure: {session_summaries: [], feedback_patterns: [], observations: [], goal: {}}. Grows over time, compacted periodically.';

-- Deliverable mode: recurring (default) or goal (finite completion)
ALTER TABLE deliverables
ADD COLUMN IF NOT EXISTS mode TEXT NOT NULL DEFAULT 'recurring';

ALTER TABLE deliverables
ADD CONSTRAINT deliverables_mode_check
CHECK (mode IN ('recurring', 'goal'));

COMMENT ON COLUMN deliverables.mode IS
'ADR-087: Deliverable mode. "recurring" = ongoing scheduled work. "goal" = finite objective with completion criteria.';

-- =============================================================================
-- 2. NEW COLUMN ON chat_sessions
-- =============================================================================

-- Routing key for memory accumulation
ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS deliverable_id UUID REFERENCES deliverables(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_chat_sessions_deliverable
ON chat_sessions(deliverable_id)
WHERE deliverable_id IS NOT NULL;

COMMENT ON COLUMN chat_sessions.deliverable_id IS
'ADR-087: Routes this TP session to a specific deliverable for memory accumulation. NULL = global chat (no deliverable scope). Set at session creation from surface_context.deliverableId.';

-- =============================================================================
-- 3. COMMENTS
-- =============================================================================

COMMENT ON TABLE deliverables IS
'ADR-087: Each deliverable is a self-contained unit of work with its own instructions, memory, sources, schedule, and output history. deliverable_instructions (user-authored) + deliverable_memory (system-accumulated) complete the scoped context model.';
