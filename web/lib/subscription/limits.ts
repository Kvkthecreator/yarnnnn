/**
 * Subscription tier limits and feature flags
 *
 * ADR-053: Primary monetization gates are daily token budget + active deliverables.
 * Platform resource limits (Slack channels, Gmail labels, etc.) are defined in
 * api/services/platform_limits.py and fetched via API.
 *
 * For platform sync monetization, see:
 * - docs/adr/ADR-053-platform-sync-monetization.md
 */

export const SUBSCRIPTION_LIMITS = {
  free: {
    projects: 1,
    memoriesPerProject: 50,
    dailyTokenBudget: 50_000,    // ADR-053: Daily token budget
    activeDeliverables: 2,       // ADR-053: Active deliverable limit
    documents: 10,
  },
  starter: {
    projects: 3,
    memoriesPerProject: 200,
    dailyTokenBudget: 250_000,
    activeDeliverables: 5,
    documents: 50,
  },
  pro: {
    projects: Infinity,
    memoriesPerProject: Infinity,
    dailyTokenBudget: Infinity,  // Unlimited
    activeDeliverables: Infinity,
    documents: Infinity,
  },
} as const;

export type SubscriptionTier = keyof typeof SUBSCRIPTION_LIMITS;

export interface UsageData {
  projectCount: number;
  memoryCount: number; // for current project
  totalMemories: number;
  dailyTokensUsed: number;
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

export function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(0)}k`;
  return tokens.toString();
}

// Feature flags for Pro-only features
export const PRO_FEATURES = {
  signalProcessing: true,        // ADR-053: Signal processing requires Starter+
  bulkImport: false,             // available on free
  documentUpload: false,         // available on free with limits
  advancedAnalytics: true,
  prioritySupport: true,
  apiAccess: true,
} as const;

export function isProFeature(feature: keyof typeof PRO_FEATURES): boolean {
  return PRO_FEATURES[feature];
}
