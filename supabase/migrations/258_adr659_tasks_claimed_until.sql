-- ADR-659 D1 — the run's claim is its own column, and it is a lock.
--
-- Until now a run claimed its index row by bumping `next_run_at` to a sentinel
-- two hours out. That is the column `materialize_standing_index` OWNS, so the
-- next tick's materializer could rewrite it mid-run (driven 2026-09-20: a
-- never-run `fire_on_activation` declaration came due again while its first
-- run was in flight, and a second claim succeeded). It also made the claim a
-- compare-and-swap against a value the CALLER read — so a caller reading after
-- a claim read the sentinel, which equals itself (ADR-658 A1.8, two charges).
--
-- `claimed_until` is written only by `scheduling.claim_run` (hold) and
-- `scheduling.record_run` (release). NOT NULL DEFAULT 'epoch' on purpose: the
-- claim is then ONE filter — `claimed_until < now()` — the same `lt` shape the
-- due scan already uses, instead of an `or(is.null, lt)` expression.
--
-- Additive: code that does not know the column ignores it.

ALTER TABLE public.tasks
  ADD COLUMN IF NOT EXISTS claimed_until timestamptz NOT NULL DEFAULT 'epoch';

COMMENT ON COLUMN public.tasks.claimed_until IS
  'ADR-659 D1: a run holds this index row until this instant. epoch = unheld. '
  'Written only by scheduling.claim_run / record_run; never by a materializer.';
