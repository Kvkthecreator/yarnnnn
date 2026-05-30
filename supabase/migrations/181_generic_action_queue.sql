-- ADR-307 Phase 2: Generalize action_proposals into a generic gated-action queue.
--
-- The queue was a capital-action queue wearing a "generic" costume:
--   action_type → ACTION_DISPATCH_MAP → platform tool (the platform-write map)
--   rationale/expected_effect/reversibility/risk_warnings as REQUIRED columns
--     (capital framing — a trade needs a human "why" + risk profile)
--
-- First-principles shape (ADR-307 D4 revised): a queued action is
--   (primitive, inputs) + family-shaped decision_context + stable id.
--
--   action_type → primitive   (store the call directly; ExecuteProposal replays
--                               execute_primitive(primitive, inputs); map DELETED)
--   {rationale, expected_effect, reversibility, risk_warnings}
--                            → decision_context jsonb (family-shaped)
--   + family text            (discriminator: cockpit renders by family)
--
-- The id PK round-trip (action_proposals.id → Alpaca client_order_id → P&L
-- attribution → _money_truth.md → high_impact feedback) is SACRED and unchanged.
-- signal_id stays in `inputs` (NOT migrated). This migration is additive on the
-- reconciler's read path.

-- 1. Add the new columns.
ALTER TABLE action_proposals
    ADD COLUMN IF NOT EXISTS primitive TEXT,
    ADD COLUMN IF NOT EXISTS family TEXT,
    ADD COLUMN IF NOT EXISTS decision_context JSONB;

-- 2. Backfill existing rows (all 8 live rows are trading.submit_order, capital
--    family). Map action_type → primitive via the (now-deleted in code)
--    ACTION_DISPATCH_MAP equivalents; fold the 4 capital columns into
--    decision_context; stamp family='capital'.
--
--    The verb.noun action_types all mapped to platform_* tools. We preserve
--    the platform tool name as the primitive (that IS the call ExecuteProposal
--    replays). The map's entries at code-deletion time:
--      trading.submit_order            → platform_trading_submit_order
--      trading.submit_bracket_order    → platform_trading_submit_bracket_order
--      trading.submit_trailing_stop    → platform_trading_submit_trailing_stop
--      trading.update_order            → platform_trading_update_order
--      trading.cancel_order            → platform_trading_cancel_order
--      trading.cancel_all_orders       → platform_trading_cancel_all_orders
--      trading.close_position          → platform_trading_close_position
--      trading.partial_close           → platform_trading_partial_close
--      trading.add_to_watchlist        → platform_trading_add_to_watchlist
--      trading.remove_from_watchlist   → platform_trading_remove_from_watchlist
--      commerce.create_product         → platform_commerce_create_product
--      commerce.update_product         → platform_commerce_update_product
--      commerce.create_discount        → platform_commerce_create_discount
--      commerce.issue_refund           → platform_commerce_issue_refund
--      commerce.update_variant         → platform_commerce_update_variant
--      commerce.bulk_update_variant_prices → platform_commerce_bulk_update_variant_prices
--      commerce.create_variant         → platform_commerce_create_variant
--      commerce.update_customer        → platform_commerce_update_customer
--      email.send                      → platform_email_send
--      email.send_bulk                 → platform_email_send_bulk
--      task.create                     → ManageTask  (DEAD — ManageTask deleted
--                                                      ADR-231; no live rows)
UPDATE action_proposals
SET
    primitive = CASE
        WHEN action_type = 'trading.submit_order'            THEN 'platform_trading_submit_order'
        WHEN action_type = 'trading.submit_bracket_order'    THEN 'platform_trading_submit_bracket_order'
        WHEN action_type = 'trading.submit_trailing_stop'    THEN 'platform_trading_submit_trailing_stop'
        WHEN action_type = 'trading.update_order'            THEN 'platform_trading_update_order'
        WHEN action_type = 'trading.cancel_order'            THEN 'platform_trading_cancel_order'
        WHEN action_type = 'trading.cancel_all_orders'       THEN 'platform_trading_cancel_all_orders'
        WHEN action_type = 'trading.close_position'          THEN 'platform_trading_close_position'
        WHEN action_type = 'trading.partial_close'           THEN 'platform_trading_partial_close'
        WHEN action_type = 'trading.add_to_watchlist'        THEN 'platform_trading_add_to_watchlist'
        WHEN action_type = 'trading.remove_from_watchlist'   THEN 'platform_trading_remove_from_watchlist'
        WHEN action_type = 'commerce.create_product'         THEN 'platform_commerce_create_product'
        WHEN action_type = 'commerce.update_product'         THEN 'platform_commerce_update_product'
        WHEN action_type = 'commerce.create_discount'        THEN 'platform_commerce_create_discount'
        WHEN action_type = 'commerce.issue_refund'           THEN 'platform_commerce_issue_refund'
        WHEN action_type = 'commerce.update_variant'         THEN 'platform_commerce_update_variant'
        WHEN action_type = 'commerce.bulk_update_variant_prices' THEN 'platform_commerce_bulk_update_variant_prices'
        WHEN action_type = 'commerce.create_variant'         THEN 'platform_commerce_create_variant'
        WHEN action_type = 'commerce.update_customer'        THEN 'platform_commerce_update_customer'
        WHEN action_type = 'email.send'                      THEN 'platform_email_send'
        WHEN action_type = 'email.send_bulk'                 THEN 'platform_email_send_bulk'
        ELSE action_type  -- unknown / future; preserve verbatim
    END,
    family = 'capital',
    decision_context = jsonb_strip_nulls(jsonb_build_object(
        'rationale',       rationale,
        'expected_effect', expected_effect,
        'reversibility',   reversibility,
        'risk_warnings',   risk_warnings
    ))
WHERE primitive IS NULL;

-- 3. Enforce the new shape going forward.
ALTER TABLE action_proposals
    ALTER COLUMN primitive SET NOT NULL,
    ALTER COLUMN family SET DEFAULT 'capital',
    ALTER COLUMN family SET NOT NULL;

-- 4. Drop the capital-framing constraints + columns.
--    reversibility was NOT NULL + CHECK-constrained — both removed (it now lives
--    in decision_context, family-shaped). The 4 capital columns are dropped;
--    their content is preserved in decision_context (backfilled above).
ALTER TABLE action_proposals
    DROP CONSTRAINT IF EXISTS action_proposals_reversibility_check;

ALTER TABLE action_proposals
    DROP COLUMN IF EXISTS action_type,
    DROP COLUMN IF EXISTS rationale,
    DROP COLUMN IF EXISTS expected_effect,
    DROP COLUMN IF EXISTS reversibility,
    DROP COLUMN IF EXISTS risk_warnings;

-- 5. family CHECK (extensible — capital + substrate today; future families add here).
ALTER TABLE action_proposals
    ADD CONSTRAINT action_proposals_family_check
        CHECK (family IN ('capital', 'substrate'));

-- 6. Index for family-scoped queue reads (cockpit renders by family).
CREATE INDEX IF NOT EXISTS action_proposals_family_idx
    ON action_proposals (user_id, family, status)
    WHERE status = 'pending';

-- 7. Comments.
COMMENT ON COLUMN action_proposals.primitive IS
    'ADR-307: the primitive to replay on approve via execute_primitive(primitive, inputs). Replaces action_type + ACTION_DISPATCH_MAP (deleted). e.g. "WriteFile", "platform_trading_submit_order".';
COMMENT ON COLUMN action_proposals.family IS
    'ADR-307: queue family discriminator (capital | substrate). The cockpit renderer dispatches on it (capital → order-ticket card; substrate → diff card). decision_context is family-shaped.';
COMMENT ON COLUMN action_proposals.decision_context IS
    'ADR-307: family-shaped operator decision context. capital: {rationale, expected_effect, reversibility, risk_warnings}. substrate: {diff, message}.';
COMMENT ON TABLE action_proposals IS
    'ADR-193 + ADR-307: generic gated-action queue. A queued primitive call (primitive, inputs) awaiting operator approval, with family-shaped decision_context. ExecuteProposal replays execute_primitive(primitive, inputs) on approve. id is the sacred intent↔outcome correlation key (→ platform client_order_id → P&L).';
