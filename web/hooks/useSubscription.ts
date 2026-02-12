"use client";

/**
 * ADR-053: Subscription hook with 3-tier support (Free/Starter/Pro)
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api/client";
import type { SubscriptionStatus } from "@/types";

export type SubscriptionTier = "free" | "starter" | "pro";

export function useSubscription() {
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await api.subscription.getStatus();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to fetch subscription status"));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // ADR-053: Tier detection
  const tier: SubscriptionTier = (status?.status as SubscriptionTier) || "free";
  const isPro = tier === "pro";
  const isStarter = tier === "starter";
  const isPaid = tier === "pro" || tier === "starter";

  /**
   * Upgrade to a specific tier and billing period.
   * ADR-053: Supports both Starter ($9/mo) and Pro ($19/mo) tiers.
   */
  const upgrade = async (
    tier: "starter" | "pro" = "starter",
    billingPeriod: "monthly" | "yearly" = "monthly"
  ) => {
    try {
      setIsLoading(true);
      setError(null);
      const { checkout_url } = await api.subscription.createCheckout(tier, billingPeriod);
      // Redirect to Lemon Squeezy checkout
      window.location.href = checkout_url;
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to create checkout"));
      setIsLoading(false);
    }
  };

  const manageSubscription = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const { portal_url } = await api.subscription.getPortal();
      // Open portal in new tab
      window.open(portal_url, "_blank");
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to open subscription portal"));
    } finally {
      setIsLoading(false);
    }
  };

  return {
    status,
    tier,
    isPro,
    isStarter,
    isPaid,
    isLoading,
    error,
    upgrade,
    manageSubscription,
    refresh: fetchStatus,
  };
}
