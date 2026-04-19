-- ADR-195: Outcome Attribution Substrate — Phase 1
-- Ledger of reconciled capital outcomes. One row per reconciled action.
-- Scoped by user_id to match action_proposals (its sibling substrate) —
-- ADR-195 draft said workspace_id; reconciled to user_id for consistency
-- with the rest of the action/outcome pair and with the single-tenant
-- runtime pattern.
--
-- See: docs/adr/ADR-195-outcome-attribution-substrate.md
--
-- Populated by OutcomeProvider implementations in api/services/outcomes/.
-- Consumed by:
--   - AI reviewer (ADR-194 Phase 4) via _performance.md track-record
--   - daily-update briefing (ADR-195 Phase 4) for "Your book this week"
--   - feedback actuation (ADR-181) via high-impact outcome entries
--   - context domain pruning signal (future)

CREATE TABLE IF NOT EXISTS action_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Linkage: either to a proposal (approved → executed path) or standalone
    -- (direct platform tool calls from headless agent runs or YARNNN)
    proposal_id UUID REFERENCES action_proposals(id) ON DELETE SET NULL,
    action_type TEXT NOT NULL,
        -- e.g., "trading.submit_bracket_order", "commerce.create_discount"
    action_inputs JSONB NOT NULL DEFAULT '{}',
        -- the inputs that produced this outcome (for attribution + audit)
    executed_at TIMESTAMPTZ NOT NULL,
        -- when the action was taken (not when we reconciled it)

    -- Outcome (reconciled)
    outcome_value_cents BIGINT,
        -- signed: positive=gain, negative=loss, NULL=not-applicable
    outcome_currency TEXT NOT NULL DEFAULT 'USD',
    outcome_label TEXT NOT NULL,
        -- e.g., "closed_profit", "closed_loss", "refund_issued",
        --       "campaign_revenue", "no_effect"
    outcome_metadata JSONB NOT NULL DEFAULT '{}',
        -- domain-specific: fill_price, share_count, attribution_window,
        -- alpaca_order_id (idempotency key), etc.

    -- Reconciliation metadata
    reconciled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reconciled_by TEXT NOT NULL,
        -- "trading-reconciler-v1", "commerce-reconciler-v1", "manual"
    reconciliation_confidence TEXT NOT NULL,
        -- "high" | "medium" | "low" — attribution certainty
    reconciliation_notes TEXT,

    -- Context domain this outcome belongs to
    -- Enables _performance.md regeneration and AI reviewer lookups scoped
    -- to the domain (e.g., "trading", "customers", "campaigns").
    context_domain TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT action_outcomes_confidence_check
        CHECK (reconciliation_confidence IN ('high', 'medium', 'low'))
);

-- Workspace-wide outcome stream for a user, newest first
CREATE INDEX IF NOT EXISTS action_outcomes_user_executed_idx
    ON action_outcomes (user_id, executed_at DESC);

-- Per-domain outcome stream (feeds _performance.md regeneration)
CREATE INDEX IF NOT EXISTS action_outcomes_user_domain_idx
    ON action_outcomes (user_id, context_domain, executed_at DESC);

-- Per-action-type queries (AI reviewer track record by action pattern)
CREATE INDEX IF NOT EXISTS action_outcomes_user_action_type_idx
    ON action_outcomes (user_id, action_type, executed_at DESC);

-- Proposal→outcome lookup (when a proposal went through and we want to
-- see its resolved outcome)
CREATE INDEX IF NOT EXISTS action_outcomes_proposal_idx
    ON action_outcomes (proposal_id)
    WHERE proposal_id IS NOT NULL;

-- RLS: users can only read + mutate their own outcomes
ALTER TABLE action_outcomes ENABLE ROW LEVEL SECURITY;

CREATE POLICY action_outcomes_user_select
    ON action_outcomes FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY action_outcomes_user_insert
    ON action_outcomes FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY action_outcomes_user_update
    ON action_outcomes FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Service role bypasses RLS (reconciliation back-office task uses service client)

COMMENT ON TABLE action_outcomes IS
    'ADR-195: Reconciled capital outcomes ledger. One row per reconciled action. Populated by OutcomeProvider implementations in api/services/outcomes/. Feeds AI reviewer (ADR-194), daily-update briefing, and ADR-181 feedback actuation. Ratifies FOUNDATIONS Axiom 7 (Money-Truth).';

COMMENT ON COLUMN action_outcomes.action_type IS
    'Namespaced action string matching action_proposals.action_type (e.g., "trading.submit_bracket_order"). Enables action-type-scoped track-record queries.';

COMMENT ON COLUMN action_outcomes.outcome_value_cents IS
    'Signed P&L in cents. Positive = gain, negative = loss. NULL = not-applicable (e.g., a discount code that we cannot yet attribute revenue to).';

COMMENT ON COLUMN action_outcomes.outcome_metadata IS
    'Domain-specific attribution + idempotency data. Providers use this for de-duplication — e.g., trading stores alpaca_order_id, commerce stores ls_order_id.';

COMMENT ON COLUMN action_outcomes.reconciliation_confidence IS
    'high = authoritative (e.g., proposal_id linkage or provider-confirmed); medium = attribution via timestamp + entity match; low = best-effort, outcome_value_cents may be NULL.';

COMMENT ON COLUMN action_outcomes.context_domain IS
    'Canonical context domain this outcome belongs to. Drives _performance.md regeneration at /workspace/context/{context_domain}/_performance.md.';
