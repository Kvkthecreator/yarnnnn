/**
 * Usage-meter model — ADR-396 (Type-B subscription over the metered balance).
 *
 * The single source of truth for turning the `/api/user/limits` payload into the
 * customer-facing ACTIVITY meter (allowance consumed this cycle), shared by every
 * surface that renders it: SubscriptionCard (billing pane), BudgetStatusItem
 * (menu-bar glance), and the Settings → Usage tab. Singular Implementation — the
 * three surfaces previously hand-rolled `spend / raw_balance` and MISLABELED it as
 * "allowance used" (raw_balance is the whole pool = allowance + top-ups, so the
 * number under-reported allowance consumption whenever a user held top-ups).
 *
 * The honest model (ADR-396 §3 draw order: allowance → balance → hard-stop):
 *   - allowanceConsumed = min(spend, allowance)         — allowance is spent first
 *   - overageConsumed   = max(0, spend − allowance)     — then top-ups
 *   - allowancePct      = allowanceConsumed / allowance — the "% of included usage"
 *
 * Free tier has NO allowance (allowance_usd = 0), so the allowance meter is
 * undefined there; the meter falls back to a top-up BALANCE bar. `mode` names which
 * meter a surface should render so the LABEL always matches the MATH.
 *
 * Transparency contract (ADR-396 §1): surfaces render the returned percentages +
 * labels, never the raw dollar fields — dollars stay internal to the ledger.
 */

import type { SubscriptionTier } from "@/types";

/** The `/api/user/limits` fields this model consumes. */
export interface UsageLimits {
  spend_usd: number;
  raw_balance_usd: number;
  allowance_usd: number;
  topup_balance_usd: number;
  tier: SubscriptionTier;
}

export type UsageMeterMode =
  /** Paid tier with allowance remaining — bar shows allowance consumed. */
  | "allowance"
  /** Allowance spent; now drawing top-up balance — bar shows top-up balance consumed. */
  | "overage"
  /** No allowance (free tier or unset) — bar shows top-up balance consumed. */
  | "balance";

export interface UsageMeter {
  mode: UsageMeterMode;
  /** 0–100, the primary bar. Meaning depends on `mode` (see `primaryLabel`). */
  percent: number;
  /** A short, honest label for the percentage — matches the math for `mode`. */
  primaryLabel: string;
  /** Longer sentence for popover/help copy. */
  detail: string;
  /** True once ≥90% consumed (bar goes destructive). */
  isCritical: boolean;
  /** True once ≥70% consumed (bar goes amber). */
  isWarn: boolean;
  /** Whether the operator is currently drawing top-up balance (allowance gone). */
  onOverage: boolean;
}

function clampPct(n: number): number {
  if (!Number.isFinite(n) || n <= 0) return 0;
  return Math.min(100, Math.round(n));
}

/**
 * Derive the usage meter from a `/api/user/limits` payload.
 *
 * Returns null only when the payload is absent (caller shows a loader). A
 * present-but-empty workspace (zero allowance, zero balance, zero spend) returns a
 * well-formed `balance` meter at 0%.
 */
export function deriveUsageMeter(limits: UsageLimits | null | undefined): UsageMeter | null {
  if (!limits) return null;

  const allowance = Math.max(0, limits.allowance_usd || 0);
  const topups = Math.max(0, limits.topup_balance_usd || 0);
  const spend = Math.max(0, limits.spend_usd || 0);

  const allowanceConsumed = Math.min(spend, allowance);
  const overageConsumed = Math.max(0, spend - allowance);
  const onOverage = allowance > 0 && spend >= allowance;

  // Paid tier, allowance not yet exhausted → the honest "% of included usage".
  if (allowance > 0 && !onOverage) {
    const percent = clampPct((allowanceConsumed / allowance) * 100);
    return {
      mode: "allowance",
      percent,
      primaryLabel: `${percent}% of included usage used`,
      detail: "Your plan's monthly allowance funds the work your workspace runs; it renews each cycle.",
      isCritical: percent >= 90,
      isWarn: percent >= 70,
      onOverage: false,
    };
  }

  // Allowance spent — now drawing the top-up balance beneath it.
  if (allowance > 0 && onOverage) {
    // Denominator is the top-up pool the overage draws from; 100% when no top-ups.
    const percent = topups > 0 ? clampPct((overageConsumed / topups) * 100) : 100;
    return {
      mode: "overage",
      percent,
      primaryLabel:
        topups > 0 ? `${percent}% of top-up balance used` : "Allowance used up",
      detail:
        topups > 0
          ? "Your monthly allowance is spent; the workspace is now drawing your top-up balance. Top up or upgrade for more headroom."
          : "Your monthly allowance is spent and you have no top-up balance. The workspace pauses until you top up or upgrade.",
      isCritical: percent >= 90,
      isWarn: true,
      onOverage: true,
    };
  }

  // No allowance (free tier / unset) → a top-up balance meter.
  const percent = topups > 0 ? clampPct((spend / (spend + topups)) * 100) : 0;
  return {
    mode: "balance",
    percent,
    primaryLabel: `${percent}% of balance used`,
    detail:
      topups > 0
        ? "You're on the free plan — usage draws from your top-up balance. Upgrade for a monthly included allowance."
        : "You're on the free plan with no balance yet. Top up or upgrade to start running work.",
    isCritical: percent >= 90,
    isWarn: percent >= 70,
    onOverage: false,
  };
}

/** Shared top-up presets + floor (must match TOPUP_MIN_USD/MAX in the API). */
export const TOPUP_MIN_USD = 5;
export const TOPUP_MAX_USD = 500;
export const TOPUP_PRESETS = [5, 10, 25, 50] as const;
export const TOPUP_DEFAULT = 25;

/**
 * Monthly plan price per tier (USD) — the CATALOG price shown on upgrade CTAs.
 * This is a plan price, NOT a usage bill, so it's shown to the operator (the
 * hide-$ contract governs ACTIVITY surfaces, not the price of a plan).
 *
 * Mirror of api/services/billing_tiers.py::TIER_CONFIG.price_usd — the backend is
 * the source of truth for what LS charges; this is the display copy. Keep in sync
 * (both are launch-test numbers per ADR-396 §7, relaxed).
 */
export const TIER_PRICE_USD: Record<SubscriptionTier, number> = {
  free: 0,
  starter: 20, // ADR-429 §12.2 — the single paid plan, repriced $19→$20 (mirror TIER_CONFIG)
  pro: 49,     // ADR-429 §12.1 — dormant (hidden); not offered until capture ships
};

/** "$19" / "$49" / "Free" — the price label for an upgrade CTA. */
export function tierPriceLabel(tier: SubscriptionTier): string {
  const price = TIER_PRICE_USD[tier];
  return price > 0 ? `$${price}/mo` : "Free";
}

/**
 * One-line descriptor of what a tier gives you — shown under the plan name on the
 * billing header so the operator sees WHAT they're on, not just the label.
 * Mirrors billing_tiers.py TIER_CONFIG (allowance + connector ceilings).
 */
export function tierDescriptor(tier: SubscriptionTier): string {
  // ADR-429 §13.2 — connector-history dropped from the pitch (it gates the DORMANT
  // capture lane, §12.1). The paid plan's honest differentiator today is the
  // included monthly allowance + a shared workspace everyone draws.
  switch (tier) {
    case "pro":
      return "$45 monthly usage included"; // dormant tier (not offered); descriptor kept for a legacy row
    case "starter":
      return "$15 monthly usage included · your whole workspace draws one shared allowance";
    default:
      return "Workspace + memory, free forever · usage drawn from your balance";
  }
}
