"use client";

/**
 * ADR-396: Type-B subscription over the metered balance.
 *
 * The plan tier (free / starter / pro) grants a monthly INCLUDED ALLOWANCE; a
 * dynamic top-up (any dollar amount) is the overage pool beneath it. Two purchase
 * paths: `subscribe(tier)` (plan) + `topup(amountUsd)` (overage). Draw order is
 * server-side: allowance → balance → hard-stop at zero.
 */

import { useState, useEffect, useCallback } from "react";
import { api, APIError } from "@/lib/api/client";
import type { BalanceEntry, SubscriptionStatus, SubscriptionTier } from "@/types";

export function useSubscription() {
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  // ADR-652 — the balance history. Fetched alongside status, kept SEPARATE from
  // `isLoading`: the history is supplementary, and a slow or failed ledger read
  // must never hold up or break the plan/balance the pane exists to show.
  // `null` = not yet loaded (or unavailable); `[]` = loaded and genuinely empty.
  const [history, setHistory] = useState<BalanceEntry[] | null>(null);
  const [historyHasMore, setHistoryHasMore] = useState(false);

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

  // The ledger read is best-effort and independent of the status fetch (see the
  // `history` state note). A 403 here is the same member gate as /status, and
  // the pane already renders that state from `isForbidden`.
  const fetchHistory = useCallback(async () => {
    try {
      const data = await api.subscription.getTransactions();
      setHistory(data.entries);
      setHistoryHasMore(data.has_more);
    } catch {
      setHistory(null);
      setHistoryHasMore(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchHistory();
  }, [fetchStatus, fetchHistory]);

  const tier: SubscriptionTier = status?.tier ?? "free";
  const isPaid = tier === "starter" || tier === "pro";
  // ADR-491 D2 — the member gate keys on the SERVER's grant decision, never a
  // role enum: /subscription/status 403s a caller without billing authority
  // (ADR-416 D1), and the Billing pane renders a calm "managed by the owner"
  // state instead of dead verbs.
  const isForbidden = error instanceof APIError && error.status === 403;

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

  const topup = async (amountUsd: number) => {
    try {
      setIsLoading(true);
      setError(null);
      const { checkout_url } = await api.subscription.createTopup(amountUsd);
      window.location.href = checkout_url;
    } catch (err) {
      setError(toUserError(err, "Failed to start top-up"));
      setIsLoading(false);
    }
  };

  const subscribe = async (nextTier: "starter" | "pro") => {
    try {
      setIsLoading(true);
      setError(null);
      const { checkout_url } = await api.subscription.createSubscription(nextTier);
      window.location.href = checkout_url;
    } catch (err) {
      setError(toUserError(err, "Failed to start subscription"));
      setIsLoading(false);
    }
  };

  // RENAMED 2026-07-22 from `manageSubscription`. The old name promised generic
  // plan management and delivered a bounce to the Lemon Squeezy customer portal
  // — a differently-branded page listing our product under a store name. The
  // portal's honest scope is the payment INSTRUMENT (card on file, invoices,
  // receipts), which is genuinely the processor's; the PLAN (which tier this
  // workspace runs on) is ours to model, and now has in-app verbs.
  const openPaymentMethods = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const { portal_url } = await api.subscription.getPortal();
      window.location.href = portal_url;
    } catch (err) {
      setError(toUserError(err, "Failed to open payment methods"));
      setIsLoading(false);
    }
  };

  // Cancel at period end. Returns `ends_at` so the caller can say WHEN access
  // stops — the tier flips on the `subscription_expired` webhook at that
  // boundary, never optimistically here (cancelling must not strip an allowance
  // the workspace already paid for). Refreshes status so the card re-reads.
  const cancel = async (): Promise<{ ends_at: string | null } | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await api.subscription.cancel();
      await fetchStatus();
      return { ends_at: res.ends_at ?? null };
    } catch (err) {
      setError(toUserError(err, "Failed to cancel the plan"));
      setIsLoading(false);
      return null;
    }
  };

  return {
    status,
    tier,
    isPaid,
    isLoading,
    error,
    isForbidden,
    topup,
    subscribe,
    openPaymentMethods,
    cancel,
    history,
    historyHasMore,
    refresh: fetchStatus,
  };
}
