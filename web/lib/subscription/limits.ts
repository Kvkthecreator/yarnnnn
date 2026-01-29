/**
 * Subscription tier limits and feature flags
 */

export const SUBSCRIPTION_LIMITS = {
  free: {
    projects: 1,
    memoriesPerProject: 50,
    chatSessionsPerMonth: 5,
    scheduledAgents: 0,
    documents: 10,
  },
  pro: {
    projects: Infinity,
    memoriesPerProject: Infinity,
    chatSessionsPerMonth: Infinity,
    scheduledAgents: Infinity,
    documents: Infinity,
  },
} as const;

export type SubscriptionTier = keyof typeof SUBSCRIPTION_LIMITS;

export interface UsageData {
  projectCount: number;
  memoryCount: number; // for current project
  totalMemories: number;
  chatSessionsThisMonth: number;
  documentCount: number;
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

// Feature flags for Pro-only features
export const PRO_FEATURES = {
  scheduledAgents: true,
  bulkImport: false, // available on free
  documentUpload: false, // available on free with limits
  advancedAnalytics: true,
  prioritySupport: true,
  apiAccess: true,
} as const;

export function isProFeature(feature: keyof typeof PRO_FEATURES): boolean {
  return PRO_FEATURES[feature];
}
