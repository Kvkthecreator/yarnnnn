-- Migration 210 — ADR-429 §12.3 — the seat-activation rails
--
-- Two columns on `workspaces` that carry the seat-axis activation architecture.
-- Both are DORMANT-safe: with the seat fee at $0 (ADR-429 §5a) neither changes
-- any billing outcome today; they are the rails the eventual activation runs on.
--
--   • billing_exempt (bool, default false) — the comp/override capability
--     (ADR-429 §12.3a). When true, the workspace pays NOTHING — no base, no
--     seats — regardless of tier or headcount. The operator marks test
--     workspaces exempt (held out of billing deliberately); it is also the
--     permanent "comped account" capability. Checked in base/seat resolution.
--
--   • seat_pricing_effective_at (timestamptz, nullable) — the grandfather rail
--     (ADR-429 §12.3b). When the seat fee is activated, this marks WHEN the fee
--     begins applying to a given workspace. NULL = the seat fee applies whenever
--     the tier's additional_seat_usd is non-zero (the default once activated);
--     a future date = a grandfather grace window (existing teams keep the old
--     price until then). The seat math reads this; dormant-safe (with a $0 fee
--     it is inert).
--
-- No CHECK-constraint change (the 3 tier enum values are KEPT — ADR-429 §12.1 is
-- a product collapse, not a schema change; `pro` is hidden in code, not removed
-- from the enum). No data migration (audit 2026-07-09: 12 free / 1 starter / 0
-- pro — the live starter row stays valid at its new $20/$15 price). Idempotent.

ALTER TABLE public.workspaces
  ADD COLUMN IF NOT EXISTS billing_exempt boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS seat_pricing_effective_at timestamptz;

COMMENT ON COLUMN public.workspaces.billing_exempt IS
  'ADR-429 §12.3a — when true the workspace pays nothing (no base, no seats), '
  'regardless of tier/headcount. The comp/override capability (operator test '
  'workspaces; permanent comped-account support). Checked in base + seat fee '
  'resolution.';

COMMENT ON COLUMN public.workspaces.seat_pricing_effective_at IS
  'ADR-429 §12.3b — when the (dormant) seat fee is activated, marks when it '
  'begins applying to THIS workspace (grandfather-with-notice: existing teams '
  'keep the old price until this date). NULL = applies whenever the tier fee is '
  'non-zero. Dormant-safe (inert while additional_seat_usd = 0).';
