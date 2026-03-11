/**
 * Subscription tier limits and feature flags
 *
 * ADR-100: Simplified 2-tier monetization (Free + Pro).
 * Platform resource limits (Slack channels, Gmail labels, etc.) are defined in
 * api/services/platform_limits.py and fetched via API.
 *
 * Tier structure (ADR-100, 2026-03-09):
 * - Free: 5/5/10 sources, 1x/day sync, 50 messages/month, 2 agents
 * - Pro ($19/mo, Early Bird $9/mo): unlimited sources, hourly sync, unlimited messages, 10 agents
 */

export const SUBSCRIPTION_LIMITS = {
  free: {
    monthlyMessages: 50,          // ADR-100: Monthly message limit
    activeAgents: 2,        // ADR-100: Active agent limit
    documents: 10,
  },
  pro: {
    monthlyMessages: Infinity,    // Unlimited
    activeAgents: Infinity,
    documents: Infinity,
  },
} as const;

export type SubscriptionTier = keyof typeof SUBSCRIPTION_LIMITS;

export interface UsageData {
  monthlyMessagesUsed: number;
  documentCount: number;
  activeAgents: number;
}

export interface LimitStatus {
  feature: string;
  current: number;
  limit: number;
  isAtLimit: boolean;
  isNearLimit: boolean; // 80% threshold
  percentUsed: number;
}

export function checkLimit(
  tier: SubscriptionTier,
  feature: keyof typeof SUBSCRIPTION_LIMITS.free,
  currentUsage: number
): LimitStatus {
  const limit = SUBSCRIPTION_LIMITS[tier][feature];
  const isUnlimited = limit === Infinity;
  const percentUsed = isUnlimited ? 0 : (currentUsage / limit) * 100;

  return {
    feature,
    current: currentUsage,
    limit: isUnlimited ? -1 : limit, // -1 indicates unlimited
    isAtLimit: !isUnlimited && currentUsage >= limit,
    isNearLimit: !isUnlimited && percentUsed >= 80,
    percentUsed: Math.min(percentUsed, 100),
  };
}

export function formatLimit(limit: number): string {
  return limit === -1 || limit === Infinity ? "Unlimited" : limit.toString();
}

export function formatMessages(count: number): string {
  return count.toString();
}

// Feature flags for Pro-only features
export const PRO_FEATURES = {
  bulkImport: false,             // available on free
  documentUpload: false,         // available on free with limits
  advancedAnalytics: true,
  prioritySupport: true,
  apiAccess: true,
} as const;

export function isProFeature(feature: keyof typeof PRO_FEATURES): boolean {
  return PRO_FEATURES[feature];
}
