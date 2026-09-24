-- Migration 263 (ADR-666 D2): what a run cost, stored on the run.
--
-- The run collects the ids of the `execution_events` rows it wrote (the ledger
-- writer returns each id) and sums their cost_usd when it finishes — an exact
-- join by id. Before this the cockpit read cost off ledger rows it had matched
-- to a run by a time window; that join is deleted with ADR-666.
ALTER TABLE public.runs ADD COLUMN IF NOT EXISTS cost_usd numeric;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'runs' AND column_name = 'cost_usd'
  ) THEN
    RAISE EXCEPTION 'runs.cost_usd is missing';
  END IF;
END $$;
