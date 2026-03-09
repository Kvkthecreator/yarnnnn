"use client";

/**
 * ADR-100: Subscription gate hook with 2-tier support.
 */

import { useMemo } from "react";
import { useSubscription, type SubscriptionTier } from "./useSubscription";
import {
  SUBSCRIPTION_LIMITS,
  checkLimit,
  type LimitStatus,
} from "@/lib/subscription/limits";

export interface SubscriptionGate {
  // Tier info
  tier: SubscriptionTier;
  isPro: boolean;
  isPaid: boolean;
  isLoading: boolean;

  // Actions — ADR-100: Always upgrades to Pro
  upgrade: (billingPeriod?: "monthly" | "yearly", earlyBird?: boolean) => Promise<void>;

  // Helper to check any feature
  checkFeatureLimit: (
    feature: keyof typeof SUBSCRIPTION_LIMITS.free,
    currentUsage: number
  ) => LimitStatus;
}

/**
 * Hook for checking subscription limits and gating features.
 * Combines subscription status with current usage data.
 */
export function useSubscriptionGate(): SubscriptionGate {
  const { tier, isPro, isPaid, isLoading, upgrade } = useSubscription();

  // Generic limit checker
  const checkFeatureLimit = useMemo(
    () =>
      (
        feature: keyof typeof SUBSCRIPTION_LIMITS.free,
        currentUsage: number
      ): LimitStatus => {
        return checkLimit(tier, feature, currentUsage);
      },
    [tier]
  );

  return {
    tier,
    isPro,
    isPaid,
    isLoading,
    upgrade,
    checkFeatureLimit,
  };
}

/**
 * Hook for checking monthly message limit (ADR-100).
 */
export function useMessageLimitGate(monthlyMessagesUsed: number) {
  const { tier, isPro, checkFeatureLimit } = useSubscriptionGate();

  const messageLimit = useMemo(
    () => checkFeatureLimit("monthlyMessages", monthlyMessagesUsed),
    [checkFeatureLimit, monthlyMessagesUsed]
  );

  return {
    tier,
    isPro,
    limit: messageLimit,
    canChat: !messageLimit.isAtLimit,
    isNearLimit: messageLimit.isNearLimit,
    messagesRemaining: messageLimit.limit === -1
      ? Infinity
      : Math.max(0, messageLimit.limit - monthlyMessagesUsed),
  };
}
