-- ADR-193: ProposeAction Primitive + Approval Loop
-- Adds action_proposals table for persisting proposed writes awaiting
-- user approval. Integrates with ADR-192 risk-gate rejections and
-- ADR-195 autonomous decision loop (forward-looking).

CREATE TABLE IF NOT EXISTS action_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- What would execute
    action_type TEXT NOT NULL,
        -- e.g., "trading.submit_bracket_order", "commerce.issue_refund",
        --       "email.send", "email.send_bulk"
    inputs JSONB NOT NULL,
        -- kwargs that would be passed to execute_primitive

    -- Why it was proposed
    rationale TEXT,
    expected_effect TEXT,
        -- human-readable preview of what would happen on approval
    reversibility TEXT NOT NULL,
        -- 'reversible' | 'soft-reversible' | 'irreversible'

    -- Status + lifecycle
    status TEXT NOT NULL DEFAULT 'pending',
        -- 'pending' | 'approved' | 'rejected' | 'executed'
        -- | 'expired' | 'rejected_at_execution'
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    execution_result JSONB,
    rejection_reason TEXT,
    approved_by TEXT,
        -- 'user' | 'auto_reversible' (ADR-195)

    -- Origin context (optional)
    task_slug TEXT,
        -- task that originated the proposal, if any
    agent_slug TEXT,
        -- agent that originated the proposal, if any
    risk_warnings JSONB,
        -- from risk_gate output; empty array or [] when none

    CONSTRAINT action_proposals_reversibility_check
        CHECK (reversibility IN ('reversible', 'soft-reversible', 'irreversible')),
    CONSTRAINT action_proposals_status_check
        CHECK (status IN (
            'pending', 'approved', 'rejected', 'executed',
            'expired', 'rejected_at_execution'
        ))
);

-- Partial index: fast lookup of pending proposals for a user
CREATE INDEX IF NOT EXISTS action_proposals_user_status_idx
    ON action_proposals (user_id, status)
    WHERE status = 'pending';

-- Partial index: expiration sweep finds only proposals that can still expire
CREATE INDEX IF NOT EXISTS action_proposals_expires_idx
    ON action_proposals (expires_at)
    WHERE status = 'pending';

-- Partial index: lookup by task for task-originated proposals
CREATE INDEX IF NOT EXISTS action_proposals_task_idx
    ON action_proposals (task_slug)
    WHERE task_slug IS NOT NULL;

-- RLS: users can only see + mutate their own proposals
ALTER TABLE action_proposals ENABLE ROW LEVEL SECURITY;

CREATE POLICY action_proposals_user_select
    ON action_proposals FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY action_proposals_user_insert
    ON action_proposals FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY action_proposals_user_update
    ON action_proposals FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Service role bypasses RLS (background cleanup job, execution handler)
-- No explicit policy needed — service_role is always permitted.

COMMENT ON TABLE action_proposals IS
    'ADR-193: Proposed write actions awaiting user approval. YARNNN creates via ProposeAction primitive; user approves via ExecuteProposal or rejects via RejectProposal. Expired proposals cleaned by back-office-proposal-cleanup task.';

COMMENT ON COLUMN action_proposals.action_type IS
    'Namespaced action string (e.g., "trading.submit_bracket_order"). Maps to platform tool name via ACTION_DISPATCH_MAP in primitives/propose_action.py.';

COMMENT ON COLUMN action_proposals.reversibility IS
    'Determines default TTL: reversible=24h, soft-reversible=6h, irreversible=1h. Override via expires_in_hours parameter on ProposeAction.';

COMMENT ON COLUMN action_proposals.approved_by IS
    'Who approved: "user" today. ADR-195 will add "auto_reversible" for policy-based auto-approval.';
