/**
 * Token spend metering — ADR-171
 *
 * Single meter: cost_usd across all LLM surfaces (chat, tasks, web search,
 * inference). User-facing rates are 2x Anthropic API rates.
 *
 * Free:  $3.00/mo token spend included
 * Pro:   $20.00/mo token spend included ($19/mo subscription)
 *
 * Users see one number: "$X.XX of $Y.YY used this month"
 */

// User-facing billing rates (2x Anthropic API rates, April 2026)
// Matches BILLING_RATES in api/services/platform_limits.py
export const BILLING_RATES = {
  sonnet: { inputPerMtok: 6.00, outputPerMtok: 30.00 },
  // Opus rates shown if/when model selection is exposed to users
  opus:   { inputPerMtok: 30.00, outputPerMtok: 150.00 },
} as const;

export const TIER_LIMITS = {
  free: {
    monthlyMessages: 150,
    monthlySpendUsd: 3.00,
    activeTasks: 2,
  },
  pro: {
    monthlyMessages: Infinity,   // Unlimited chat
    monthlySpendUsd: 20.00,
    activeTasks: 10,
  },
} as const;

export type SubscriptionTier = keyof typeof TIER_LIMITS;

export interface LimitStatus {
  feature: string;
  current: number;
  limit: number;
  isAtLimit: boolean;
  isNearLimit: boolean;
  percentUsed: number;
}

export function checkLimit(
  tier: SubscriptionTier,
  feature: keyof typeof TIER_LIMITS.free,
  currentUsage: number,
): LimitStatus {
  const limit = TIER_LIMITS[tier][feature] as number;
  const isUnlimited = limit === -1 || limit === Infinity;
  const percentUsed = isUnlimited ? 0 : Math.min((currentUsage / limit) * 100, 100);

  return {
    feature: String(feature),
    current: currentUsage,
    limit,
    isAtLimit: !isUnlimited && currentUsage >= limit,
    isNearLimit: !isUnlimited && percentUsed >= 80,
    percentUsed,
  };
}

export function checkSpendLimit(
  tier: SubscriptionTier,
  spendUsd: number,
): LimitStatus {
  const limit = TIER_LIMITS[tier].monthlySpendUsd;
  const percentUsed = Math.min((spendUsd / limit) * 100, 100);

  return {
    feature: 'spend',
    current: spendUsd,
    limit,
    isAtLimit: spendUsd >= limit,
    isNearLimit: percentUsed >= 80,
    percentUsed,
  };
}

export function formatSpend(usd: number): string {
  return `$${usd.toFixed(2)}`;
}

export function formatLimit(limit: number): string {
  return limit === -1 || limit === Infinity ? 'Unlimited' : limit.toString();
}

export function isProFeature(feature: string): boolean {
  return false; // All features available on both tiers, just with different limits
}
