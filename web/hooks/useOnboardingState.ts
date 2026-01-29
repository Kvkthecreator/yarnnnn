"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api/client";
import type { OnboardingState, OnboardingStateResponse } from "@/types";

interface UseOnboardingStateReturn {
  state: OnboardingState | null;
  isLoading: boolean;
  error: Error | null;
  memoryCount: number;
  documentCount: number;
  hasRecentChat: boolean;
  reload: () => Promise<void>;
  /** Dismiss the welcome prompt for this session */
  dismiss: () => void;
  isDismissed: boolean;
}

const DISMISS_KEY = "yarnnn_welcome_dismissed";

/**
 * Hook to detect user's onboarding state for welcome UX.
 *
 * States:
 * - cold_start: No memories, no documents, no recent chat → Full welcome
 * - minimal_context: <3 memories, no recent chat → Subtle banner
 * - active: Has context → Normal chat
 */
export function useOnboardingState(): UseOnboardingStateReturn {
  const [data, setData] = useState<OnboardingStateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [isDismissed, setIsDismissed] = useState(false);

  // Check if welcome was dismissed this session
  useEffect(() => {
    if (typeof window !== "undefined") {
      const dismissed = sessionStorage.getItem(DISMISS_KEY) === "true";
      setIsDismissed(dismissed);
    }
  }, []);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.onboarding.getState();
      setData(response);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const dismiss = useCallback(() => {
    setIsDismissed(true);
    if (typeof window !== "undefined") {
      sessionStorage.setItem(DISMISS_KEY, "true");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return {
    state: data?.state ?? null,
    isLoading,
    error,
    memoryCount: data?.memory_count ?? 0,
    documentCount: data?.document_count ?? 0,
    hasRecentChat: data?.has_recent_chat ?? false,
    reload: load,
    dismiss,
    isDismissed,
  };
}
