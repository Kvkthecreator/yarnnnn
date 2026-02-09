"use client";

import { useMemo } from "react";
import { useSubscription } from "./useSubscription";
import {
  SUBSCRIPTION_LIMITS,
  checkLimit,
  type SubscriptionTier,
  type LimitStatus,
} from "@/lib/subscription/limits";

export interface SubscriptionGate {
  // Tier info
  tier: SubscriptionTier;
  isPro: boolean;
  isLoading: boolean;

  // Actions
  upgrade: (billingPeriod?: "monthly" | "yearly") => Promise<void>;

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
  const { isPro, isLoading, upgrade } = useSubscription();

  const tier: SubscriptionTier = isPro ? "pro" : "free";

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
    isLoading,
    upgrade,
    checkFeatureLimit,
  };
}

/**
 * Hook for checking memory limits.
 */
export function useMemoryGate(memoryCount: number) {
  const { tier, isPro, checkFeatureLimit } = useSubscriptionGate();

  const memoriesLimit = useMemo(
    () => checkFeatureLimit("memoriesPerProject", memoryCount),
    [checkFeatureLimit, memoryCount]
  );

  return {
    tier,
    isPro,
    limit: memoriesLimit,
    canCreateMemory: !memoriesLimit.isAtLimit,
    isNearLimit: memoriesLimit.isNearLimit,
  };
}

/**
 * Hook for checking chat session limits.
 */
export function useChatGate(sessionsThisMonth: number) {
  const { tier, isPro, checkFeatureLimit } = useSubscriptionGate();

  const sessionsLimit = useMemo(
    () => checkFeatureLimit("chatSessionsPerMonth", sessionsThisMonth),
    [checkFeatureLimit, sessionsThisMonth]
  );

  return {
    tier,
    isPro,
    limit: sessionsLimit,
    canStartSession: !sessionsLimit.isAtLimit,
    isNearLimit: sessionsLimit.isNearLimit,
    sessionsRemaining: sessionsLimit.limit === -1
      ? Infinity
      : Math.max(0, sessionsLimit.limit - sessionsThisMonth),
  };
}
