/**
 * Balance model — ADR-490 (two free seats + pay-as-you-go over one shared balance).
 *
 * The single source of truth for turning the `/api/user/limits` payload into the
 * customer-facing balance readout, shared by every surface that renders it:
 * SubscriptionCard (billing pane), UserMenu (menu-bar glance), UsagePaneBody
 * (Workspace Settings → Usage).
 *
 * ── THE MODEL (ADR-490 §1③ — the allowance layer is RETIRED) ──────────────────
 * Every tier grants `monthly_allowance_usd: 0`. Usage is pure pay-as-you-go from
 * one shared prepaid balance: signup grant + top-ups, drawn at billed rate, hard
 * stop at zero. There is no monthly bucket, no included-usage tranche, and no
 * "overage" state — those were the Type-B shape ADR-396 built and ADR-490 retired.
 *
 * Accordingly this model has ONE mode. The pre-ADR-490 three-mode meter
 * (`allowance` | `overage` | `balance`) was deleted 2026-07-29: two of its three
 * branches were structurally unreachable (both required `allowance > 0`, which no
 * tier grants), and the surviving branch's copy hardcoded "You're on the free
 * plan" — which a live `starter` workspace was being shown. Dead branches whose
 * copy contradicts the model are worse than no branches.
 *
 * ── WHY REMAINING DOLLARS, NOT A PERCENTAGE ──────────────────────────────────
 * The old meter drew `spend / (spend + topups)` as "% of balance used". That
 * denominator is meaningless for a prepaid pool: `spend` is anchored to
 * `allowance_granted_at`, which the banking cycle re-stamps monthly, so the
 * percentage rebases on its own and never means anything stable. A workspace
 * holding $37 with a fresh anchor read "0% used" — arithmetically true, and it
 * told the operator nothing about what they hold.
 *
 * A prepaid balance's honest figure is WHAT'S LEFT. ADR-396's hide-dollars
 * contract governs the *consumption meter* (no running cost ticker) and permits
 * dollars "at the moment of purchase" — and a balance you top up in dollars, from
 * a chooser denominated in dollars, IS the purchase quantity. You cannot ask
 * someone to pick between $5 and $50 while refusing to say what they hold. See
 * the ADR-396 amendment note (§10, 2026-07-29).
 *
 * Consumption stays activity-shaped everywhere else: per-member attribution is a
 * %-share, the trend is relative, the runway is days. The one dollar figure is
 * the balance itself.
 */

import type { SubscriptionTier } from "@/types";

/** The `/api/user/limits` fields this model consumes. */
export interface UsageLimits {
  /**
   * The server's already-netted effective balance (pool − spend-since-anchor) —
   * the same number `get_effective_balance` feeds the hard-stop gate. This is the
   * figure we render, so what the operator sees is what `check_draw` enforces.
   *
   * PER-ROLE (2026-07-29): null when the caller lacks billing authority in the
   * acting workspace — the wallet is the owner's fact, the same one the Billing
   * pane 403s a member on. `deriveBalance` returns null then; surfaces fall
   * back to the boolean states below for warnings.
   */
  balance_usd: number | null;
  spend_usd: number;
  raw_balance_usd: number | null;
  /**
   * RETIRED by ADR-490 §1③ — every tier grants 0. The field stays on the wire
   * (the banking/anchor engine still writes it; grandfathered grants bank down
   * through it) and is folded into the remaining balance below, never rendered
   * as its own tranche.
   */
  allowance_usd: number | null;
  topup_balance_usd: number | null;
  tier: SubscriptionTier;
  /** The caller's billing authority in the acting workspace (server-derived —
   *  owner OR the `billing` grant scope, the /subscription/status verdict). */
  billing_authority?: boolean;
  /** Dollar-free balance states, member-visible: the pool being empty stops
   *  everyone's work even when the number is the owner's. */
  balance_exhausted?: boolean;
  balance_low?: boolean;
}

export interface BalanceReadout {
  /** Dollars left to spend — the pool the next draw comes out of. */
  remainingUsd: number;
  /** `remainingUsd` formatted for display ("$36.93"). */
  remainingLabel: string;
  /** Spend since the current anchor, in dollars. Drives the "used" sub-line. */
  spentUsd: number;
  /** True when the pool is empty — work is hard-stopped until a top-up. */
  isExhausted: boolean;
  /** True under $5 (the top-up floor): one more session may not complete. */
  isLow: boolean;
  /** One honest sentence about where the money comes from and what it does. */
  detail: string;
}

/** Money for display. Whole dollars stay whole; cents show two places. */
export function formatUsd(n: number): string {
  const v = Math.max(0, n);
  return v % 1 === 0 ? `$${v}` : `$${v.toFixed(2)}`;
}

/**
 * Derive the balance readout from a `/api/user/limits` payload.
 *
 * Returns null only when the payload is absent (caller shows a loader). A
 * present-but-empty workspace (zero balance, zero spend) returns a well-formed
 * exhausted readout.
 *
 * `remaining` prefers the server's netted `balance_usd` (the effective-balance
 * RPC: pool − spend-since-anchor, the same number the hard-stop gate reads) and
 * falls back to reconstructing it from the pool composition, so the figure the
 * operator sees is the figure `check_draw` will enforce.
 */
export function deriveBalance(limits: UsageLimits | null | undefined): BalanceReadout | null {
  if (!limits) return null;
  // Per-role wallet split: no billing authority → no dollar readout. The
  // caller renders its member state (the pane's pointer, the menu's plan-only
  // line) and warns from `balance_low`/`balance_exhausted` instead.
  if (limits.billing_authority === false || limits.balance_usd == null) return null;

  const spend = Math.max(0, limits.spend_usd || 0);
  // Prefer the server's netted `balance_usd` (the effective-balance RPC — the
  // gate's own number). Fall back to reconstructing it from the pool composition
  // (allowance, grandfathered + banking down, plus top-ups) only if that field is
  // missing, so an older payload still renders something true.
  const pool = Math.max(0, (limits.allowance_usd || 0) + (limits.topup_balance_usd || 0));
  const netted = Number.isFinite(limits.balance_usd)
    ? Math.max(0, limits.balance_usd)
    : Math.max(0, pool - spend);
  const remaining = Math.round(netted * 100) / 100;

  const isExhausted = remaining <= 0;
  const isLow = !isExhausted && remaining < TOPUP_MIN_USD;

  return {
    remainingUsd: remaining,
    remainingLabel: formatUsd(remaining),
    spentUsd: Math.round(spend * 100) / 100,
    isExhausted,
    isLow,
    detail: isExhausted
      ? "This workspace's balance is spent, so work is paused — nothing is lost. Top up to resume."
      : isLow
        ? "This workspace's balance is running low. Top up to keep work running without interruption."
        : "Usage draws from this workspace's shared balance. Everyone here — teammates and connected AI — draws the same pool.",
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
 * Mirrors billing_tiers.py TIER_CONFIG (seat price + pay-as-you-go usage).
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
