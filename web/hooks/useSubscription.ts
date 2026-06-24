"use client";

/**
 * ADR-171/172: Billing hook — pure pay-as-you-go.
 * Balance is the single gate. The only purchase is a one-time top-up
 * ($10 / $25 / $50). The recurring Pro subscription was retired from the
 * billing surface (2026-06-24): `upgrade`/`manageSubscription` removed,
 * replaced by `topup`. `status`/`isPaid` are retained as harmless reads for
 * any legacy consumer but the billing pane no longer branches on them.
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

  const topup = async (amount: 10 | 25 | 50) => {
    try {
      setIsLoading(true);
      setError(null);
      const { checkout_url } = await api.subscription.createTopup(amount);
      window.location.href = checkout_url;
    } catch (err) {
      setError(toUserError(err, "Failed to start top-up"));
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
    topup,
    refresh: fetchStatus,
  };
}
