"use client";

/**
 * ADR-172: Balance-first gate hook.
 * Balance > 0 is the only gate — no tier limits.
 */

import { useMemo } from "react";
import { useSubscription, type SubscriptionTier } from "./useSubscription";
import {
  checkBalanceLimit,
  type LimitStatus,
} from "@/lib/subscription/limits";

export interface SubscriptionGate {
  tier: SubscriptionTier;
  isPro: boolean;
  isPaid: boolean;
  isLoading: boolean;
  upgrade: (billingPeriod?: "monthly" | "yearly") => Promise<void>;
  /** @deprecated Balance is the single gate in ADR-172 */
  checkFeatureLimit: (feature: string, currentUsage: number) => LimitStatus;
}

export function useSubscriptionGate(): SubscriptionGate {
  const { tier, isPro, isPaid, isLoading, upgrade } = useSubscription();

  const checkFeatureLimit = useMemo(
    () => (_feature: string, _currentUsage: number): LimitStatus => ({
      feature: String(_feature),
      current: _currentUsage,
      limit: Infinity,
      isAtLimit: false,
      isNearLimit: false,
      percentUsed: 0,
    }),
    []
  );

  return { tier, isPro, isPaid, isLoading, upgrade, checkFeatureLimit };
}

/**
 * Hook for checking whether user can chat (balance > 0).
 * @deprecated monthly message counting removed in ADR-172
 */
export function useMessageLimitGate(_monthlyMessagesUsed: number) {
  const { tier, isPro } = useSubscriptionGate();

  return {
    tier,
    isPro,
    limit: { feature: "messages", current: 0, limit: Infinity, isAtLimit: false, isNearLimit: false, percentUsed: 0 },
    canChat: true,
    isNearLimit: false,
    messagesRemaining: Infinity,
  };
}
