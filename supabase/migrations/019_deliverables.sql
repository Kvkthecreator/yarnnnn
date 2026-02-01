-- Migration: 019_deliverables.sql
-- ADR-018: Recurring Deliverables Product Pivot
-- Date: 2026-02-01
--
-- Adds core entities for recurring deliverables:
-- - deliverables: the recurring commitment
-- - deliverable_versions: each execution with draft/final/feedback
-- Extends work_tickets with chaining support

-- =============================================================================
-- 1. DELIVERABLES TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS deliverables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

    -- Core fields
    title TEXT NOT NULL,
    description TEXT,

    -- Recipient context (who receives this, what they care about)
    recipient_context JSONB DEFAULT '{}',
    -- Example: {"name": "Client X", "role": "VP Marketing", "priorities": ["ROI metrics", "competitive updates"]}

    -- Template structure (extracted from examples or defined)
    template_structure JSONB DEFAULT '{}',
    -- Example: {"sections": ["Executive Summary", "Key Metrics", "Next Steps"], "typical_length": "500-800 words", "tone": "professional"}

    -- Schedule
    schedule JSONB NOT NULL DEFAULT '{}',
    -- Example: {"frequency": "weekly", "day": "monday", "time": "09:00", "timezone": "America/Los_Angeles"}
    -- Or cron-style: {"cron": "0 9 * * 1", "timezone": "America/Los_Angeles"}

    -- Data sources
    sources JSONB DEFAULT '[]',
    -- Example: [{"type": "url", "value": "https://..."}, {"type": "document", "document_id": "..."}, {"type": "description", "value": "Weekly sales numbers from CRM"}]

    -- Status
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'archived')),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_deliverables_user ON deliverables(user_id);
CREATE INDEX IF NOT EXISTS idx_deliverables_project ON deliverables(project_id);
CREATE INDEX IF NOT EXISTS idx_deliverables_status ON deliverables(status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_deliverables_next_run ON deliverables(next_run_at) WHERE status = 'active';

-- RLS
ALTER TABLE deliverables ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own deliverables"
    ON deliverables FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());


-- =============================================================================
-- 2. DELIVERABLE VERSIONS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS deliverable_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deliverable_id UUID NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,

    -- Version tracking
    version_number INTEGER NOT NULL,

    -- Status lifecycle: generating → staged → reviewing → approved/rejected
    status TEXT NOT NULL DEFAULT 'generating' CHECK (status IN ('generating', 'staged', 'reviewing', 'approved', 'rejected')),

    -- Content
    draft_content TEXT, -- What YARNNN produced
    final_content TEXT, -- What the user actually approved/sent (after edits)

    -- Feedback capture
    edit_diff JSONB, -- Structured diff between draft and final
    edit_categories JSONB, -- {"additions": [...], "deletions": [...], "restructures": [...], "rewrites": [...]}
    edit_distance_score FLOAT, -- 0.0 = no edits, 1.0 = complete rewrite
    feedback_notes TEXT, -- Explicit user feedback if rejected or refined via chat

    -- Pipeline tracking
    context_snapshot_id UUID, -- Future: reference to context state used for generation
    pipeline_run_id UUID, -- Reference to the gather work ticket that started this pipeline

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    staged_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,

    -- Unique version per deliverable
    UNIQUE(deliverable_id, version_number)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_versions_deliverable ON deliverable_versions(deliverable_id);
CREATE INDEX IF NOT EXISTS idx_versions_status ON deliverable_versions(status);
CREATE INDEX IF NOT EXISTS idx_versions_staged ON deliverable_versions(deliverable_id, status) WHERE status = 'staged';

-- RLS (via deliverable ownership)
ALTER TABLE deliverable_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage versions of their deliverables"
    ON deliverable_versions FOR ALL
    USING (
        deliverable_id IN (
            SELECT id FROM deliverables WHERE user_id = auth.uid()
        )
    )
    WITH CHECK (
        deliverable_id IN (
            SELECT id FROM deliverables WHERE user_id = auth.uid()
        )
    );


-- =============================================================================
-- 3. WORK TICKETS EXTENSIONS
-- =============================================================================

-- Add dependency chaining
ALTER TABLE work_tickets
    ADD COLUMN IF NOT EXISTS depends_on_work_id UUID REFERENCES work_tickets(id) ON DELETE SET NULL;

-- Add output-to-memory flag
ALTER TABLE work_tickets
    ADD COLUMN IF NOT EXISTS chain_output_as_memory BOOLEAN DEFAULT false;

-- Link to deliverable
ALTER TABLE work_tickets
    ADD COLUMN IF NOT EXISTS deliverable_id UUID REFERENCES deliverables(id) ON DELETE SET NULL;

ALTER TABLE work_tickets
    ADD COLUMN IF NOT EXISTS deliverable_version_id UUID REFERENCES deliverable_versions(id) ON DELETE SET NULL;

-- Pipeline step identifier
ALTER TABLE work_tickets
    ADD COLUMN IF NOT EXISTS pipeline_step TEXT CHECK (pipeline_step IN ('gather', 'synthesize', 'format', NULL));

-- Indexes for dependency queries
CREATE INDEX IF NOT EXISTS idx_work_tickets_depends_on ON work_tickets(depends_on_work_id) WHERE depends_on_work_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_work_tickets_deliverable ON work_tickets(deliverable_id) WHERE deliverable_id IS NOT NULL;


-- =============================================================================
-- 4. HELPER FUNCTIONS
-- =============================================================================

-- Function to get next version number for a deliverable
CREATE OR REPLACE FUNCTION get_next_version_number(p_deliverable_id UUID)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    next_num INTEGER;
BEGIN
    SELECT COALESCE(MAX(version_number), 0) + 1
    INTO next_num
    FROM deliverable_versions
    WHERE deliverable_id = p_deliverable_id;

    RETURN next_num;
END;
$$;

-- Function to get deliverables due for execution
CREATE OR REPLACE FUNCTION get_due_deliverables(check_time TIMESTAMPTZ DEFAULT NOW())
RETURNS TABLE (
    deliverable_id UUID,
    user_id UUID,
    project_id UUID,
    title TEXT,
    template_structure JSONB,
    sources JSONB,
    recipient_context JSONB
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id as deliverable_id,
        d.user_id,
        d.project_id,
        d.title,
        d.template_structure,
        d.sources,
        d.recipient_context
    FROM deliverables d
    WHERE d.status = 'active'
      AND d.next_run_at IS NOT NULL
      AND d.next_run_at <= check_time;
END;
$$;


-- =============================================================================
-- 5. COMMENTS
-- =============================================================================

COMMENT ON TABLE deliverables IS 'ADR-018: Recurring deliverable commitments (weekly reports, client updates, etc.)';
COMMENT ON TABLE deliverable_versions IS 'ADR-018: Each execution of a deliverable, with draft/final content and feedback';
COMMENT ON COLUMN work_tickets.depends_on_work_id IS 'ADR-018: Work chaining - this ticket waits for the referenced ticket to complete';
COMMENT ON COLUMN work_tickets.chain_output_as_memory IS 'ADR-018: When true, output is automatically saved as a memory for context accumulation';
COMMENT ON COLUMN work_tickets.pipeline_step IS 'ADR-018: Pipeline stage identifier (gather/synthesize/format)';
