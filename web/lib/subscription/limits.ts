/**
 * Usage-first billing helpers — ADR-172
 *
 * Balance is the single gate. No tier limits, no feature gating.
 * Free: $3 one-time at signup. Pro subscription: $20/month auto-refill.
 *
 * Billing rates match BILLING_RATES in api/services/platform_limits.py
 */

// User-facing billing rates (2x Anthropic API rates, April 2026)
export const BILLING_RATES = {
  sonnet: { inputPerMtok: 6.00, outputPerMtok: 30.00 },
  opus:   { inputPerMtok: 30.00, outputPerMtok: 150.00 },
} as const;

export type SubscriptionTier = 'free' | 'pro';

export interface LimitStatus {
  feature: string;
  current: number;
  limit: number;
  isAtLimit: boolean;
  isNearLimit: boolean;
  percentUsed: number;
}

/** Check balance exhaustion as a limit status (for legacy consumers) */
export function checkBalanceLimit(
  balanceUsd: number,
  spendUsd: number,
): LimitStatus {
  const percentUsed = balanceUsd > 0 ? Math.min((spendUsd / balanceUsd) * 100, 100) : 100;
  return {
    feature: 'balance',
    current: spendUsd,
    limit: balanceUsd,
    isAtLimit: balanceUsd <= 0,
    isNearLimit: percentUsed >= 80,
    percentUsed,
  };
}

/** @deprecated Use checkBalanceLimit (ADR-172) */
export const checkLimit = checkBalanceLimit as unknown as (
  tier: SubscriptionTier,
  feature: string,
  currentUsage: number,
) => LimitStatus;

/** @deprecated Not used in ADR-172 balance model */
export const TIER_LIMITS = {
  free: { monthlyMessages: Infinity, monthlySpendUsd: 3.00, activeTasks: Infinity },
  pro:  { monthlyMessages: Infinity, monthlySpendUsd: 20.00, activeTasks: Infinity },
} as const;

export function formatSpend(usd: number): string {
  return `$${usd.toFixed(2)}`;
}

export function formatLimit(limit: number): string {
  return limit === -1 || limit === Infinity ? 'Unlimited' : limit.toString();
}

export function isProFeature(_feature: string): boolean {
  return false; // All features available on both tiers
}
