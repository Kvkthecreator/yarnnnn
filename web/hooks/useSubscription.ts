"use client";

/**
 * ADR-172: Subscription hook — Pro as auto-refill subscription.
 * Early Bird removed. Tiers: free (pay-as-you-go) | pro (auto-refill $20/month).
 */

import { useState, useEffect, useCallback } from "react";
import { api, APIError } from "@/lib/api/client";
import type { SubscriptionStatus } from "@/types";

export type SubscriptionTier = "free" | "pro";

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

  const rawTier = (status?.status as string) || "free";
  const tier: SubscriptionTier = rawTier === "pro" || rawTier === "starter" ? "pro" : "free";
  const isPro = tier === "pro";
  const isPaid = tier === "pro";

  const toUserError = (err: unknown, fallback: string) => {
    if (err instanceof APIError) {
      const detail = (err.data as { detail?: unknown } | undefined)?.detail;
      if (typeof detail === "string" && detail.trim().length > 0) {
        return new Error(detail);
      }
      return new Error(fallback);
    }
    return err instanceof Error ? err : new Error(fallback);
  };

  const upgrade = async (billingPeriod: "monthly" | "yearly" = "monthly") => {
    try {
      setIsLoading(true);
      setError(null);
      const { checkout_url } = await api.subscription.createCheckout(billingPeriod);
      window.location.href = checkout_url;
    } catch (err) {
      setError(toUserError(err, "Failed to create checkout"));
      setIsLoading(false);
    }
  };

  const manageSubscription = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const { portal_url } = await api.subscription.getPortal();
      window.location.assign(portal_url);
    } catch (err) {
      setError(toUserError(err, "Failed to open subscription portal"));
    } finally {
      setIsLoading(false);
    }
  };

  return {
    status,
    tier,
    isPro,
    isPaid,
    isLoading,
    error,
    upgrade,
    manageSubscription,
    refresh: fetchStatus,
  };
}
