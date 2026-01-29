"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api/client";
import type { SubscriptionStatus } from "@/types";

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

  const isPro = status?.status === "pro";

  const upgrade = async (billingPeriod: "monthly" | "yearly" = "monthly") => {
    try {
      setIsLoading(true);
      setError(null);
      const { checkout_url } = await api.subscription.createCheckout(billingPeriod);
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
    isPro,
    isLoading,
    error,
    upgrade,
    manageSubscription,
    refresh: fetchStatus,
  };
}
