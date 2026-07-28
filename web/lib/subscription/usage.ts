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
 * The per-SEAT unit price per tier (USD) — the CATALOG price. A plan price, NOT a
 * usage bill, so it is shown to the operator (the hide-$ contract governs ACTIVITY
 * surfaces, not the price of a plan).
 *
 * Mirror of api/services/billing_tiers.py::TIER_CONFIG.additional_seat_usd — the
 * backend is the source of truth for what LS charges; this is display copy. Keep in
 * sync (both are launch-test numbers per ADR-396 §7, relaxed).
 *
 * ADR-490: the paid subscription IS the seat fee; there is no separate base and
 * no included allowance. The first TWO humans are free; the checkout is offered
 * only at the seat boundary (inviting the 3rd human), with quantity floored at 1
 * (the incoming seat — LS rejects quantity 0).
 */
export const TIER_SEAT_PRICE_USD: Record<SubscriptionTier, number> = {
  free: 0,
  starter: 20, // $20/additional human/mo (mirror TIER_CONFIG.additional_seat_usd)
  pro: 20,     // dormant (hidden); returns as a 2nd seat-priced plan with richer gates
  enterprise: 20, // seat-priced like every paid tier; the custody bundle is the sell
};

/**
 * The pooled monthly allowance a plan grants — RETIRED by ADR-490 §1③: every
 * tier grants $0 (usage is pure pay-as-you-go from the shared balance). Kept as
 * a constant so the meter math + descriptors degrade gracefully; mirror of
 * api/services/billing_tiers.py::TIER_CONFIG.monthly_allowance_usd.
 */
export const TIER_ALLOWANCE_USD: Record<SubscriptionTier, number> = {
  free: 0,
  starter: 0,    // ADR-490 — the allowance layer is retired
  pro: 0,        // dormant (hidden); returns differentiating on gates, not allowance
  enterprise: 0, // sales-led — sized per contract
};

/**
 * The one-time balance a new workspace starts with, so the loop can be felt
 * before spending anything. Marketing copy quotes it; it lives here, not inline.
 */
export const SIGNUP_GRANT_USD = 3;

/**
 * Marketing/price-copy fragments, derived from the constants above so a price
 * tune changes ONE place. ADR-445 §6 says the numbers "live in one place
 * (billing_tiers.py::TIER_CONFIG)" — the FE mirrors that single source here
 * rather than in nine independent string literals across pricing/landing/FAQ/
 * llms.txt/metadata, which is what the 2026-07-21 audit found.
 *
 * These are LAUNCH-TEST values (ADR-396 §7 discipline) and are expected to move.
 */
export const PRICE_COPY = {
  /** "$20" — the per-additional-human seat price. */
  seat: `$${TIER_SEAT_PRICE_USD.starter}`,
  /** "$20/mo per teammate you add" (from the 3rd person — ADR-490) */
  seatPerTeammate: `$${TIER_SEAT_PRICE_USD.starter}/mo per teammate you add`,
  /** Usage is pay-as-you-go from one shared balance (ADR-490 — no allowance). */
  pooledAllowance: `usage pay-as-you-go from one shared balance`,
  /** "$0" — the allowance layer is retired (ADR-490 §1③). */
  allowance: `$${TIER_ALLOWANCE_USD.starter}`,
  /** "$3" — the signup balance. */
  signupGrant: `$${SIGNUP_GRANT_USD}`,
  /** "$5" — the top-up floor. */
  topUpMin: `$${TOPUP_MIN_USD}`,
} as const;

/**
 * The UPGRADE CTA label. ADR-490: the paid plan exists to add seats beyond the
 * two free humans, so the CTA is honestly per-seat — it is shown only at the
 * seat boundary (inviting the 3rd person), never as a generic solo upsell (the
 * subscription buys nothing else — the allowance is retired).
 */
export function tierUpgradeLabel(tier: SubscriptionTier): string {
  const price = TIER_SEAT_PRICE_USD[tier];
  return price > 0 ? `$${price}/seat/mo` : "Free";
}

/**
 * One-line descriptor of what a tier gives you — shown under the plan name on the
 * billing header so the operator sees WHAT they're on, not just the label.
 * Mirrors billing_tiers.py TIER_CONFIG (seat price + pooled allowance).
 */
export function tierDescriptor(tier: SubscriptionTier): string {
  // ADR-490 — two axes: seats (two humans free, each additional priced) +
  // pay-as-you-go usage from one shared balance. Connector-history is dropped
  // from the pitch (it gates the dormant capture lane).
  switch (tier) {
    case "enterprise":
      return "Your team, your keys (BYOK) · custody, on-prem, and support"; // ADR-439
    case "pro":
      return "$20/seat beyond two · usage pay-as-you-go"; // dormant tier (not offered); descriptor kept for a legacy row
    case "starter":
      return "$20/seat for each teammate beyond two · usage pay-as-you-go from a shared balance";
    default:
      return "Workspace + memory, free for two people · usage pay-as-you-go from your balance";
  }
}
