/**
 * Subscription + Work Credits model
 *
 * Subscription buys access + unlimited chat (Pro). Work credits meter autonomous work.
 *
 * Free: 150 messages/mo, 20 credits/mo, 2 active tasks
 * Pro ($19/mo): unlimited chat, 500 credits/mo, 10 active tasks
 *
 * Credit costs: task execution = 3, render = 1
 */

export const TIER_LIMITS = {
  free: {
    monthlyMessages: 150,
    monthlyCredits: 20,
    activeTasks: 2,
  },
  pro: {
    monthlyMessages: Infinity,    // Unlimited chat
    monthlyCredits: 500,
    activeTasks: 10,
  },
} as const;

export const CREDIT_COSTS = {
  task_execution: 3,
  render: 1,
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
  currentUsage: number
): LimitStatus {
  const limit = TIER_LIMITS[tier][feature];
  const isUnlimited = limit === Infinity;
  const percentUsed = isUnlimited ? 0 : (currentUsage / limit) * 100;

  return {
    feature,
    current: currentUsage,
    limit: isUnlimited ? -1 : limit,
    isAtLimit: !isUnlimited && currentUsage >= limit,
    isNearLimit: !isUnlimited && percentUsed >= 80,
    percentUsed: Math.min(percentUsed, 100),
  };
}

export function formatLimit(limit: number): string {
  return limit === -1 || limit === Infinity ? "Unlimited" : limit.toString();
}

export function isProFeature(feature: string): boolean {
  return false; // All features available on both tiers, just with different limits
}
