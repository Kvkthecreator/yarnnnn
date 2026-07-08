-- Migration 207: Drop render_usage tracking (ADR-417)
--
-- The in-house render service (yarnnn-render) is retired — generation is
-- rented, not owned. `render_usage` was a per-user render-call tracking table
-- (ADR-118 D.2) used to enforce tier render limits on RuntimeDispatch. It was
-- already a fossil: billing collapsed to `balance_usd` + the one
-- `execution_events` meter (ADR-172 / ADR-396), and no live billing path reads
-- it. RuntimeDispatch is deleted (ADR-417), so nothing writes it either.
--
-- Drop the RPC first (depends on the table), then the table.

DROP FUNCTION IF EXISTS get_monthly_render_count(UUID);

DROP TABLE IF EXISTS render_usage;
