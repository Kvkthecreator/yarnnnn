"use client";

/**
 * ADR-033: Platform-First Onboarding State Hook
 *
 * Platform-centric onboarding replaces the legacy memory/document counting approach.
 * Users are guided to connect platforms (Slack, Gmail, Notion) as the primary way
 * to build context, rather than manual upload/paste.
 *
 * States:
 * - no_platforms: No integrations connected → Full platform onboarding
 * - platforms_syncing: Platforms connected but still importing → Show progress
 * - active: At least one platform has context → Normal dashboard
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api/client";

export type PlatformOnboardingState =
  | "no_platforms"
  | "platforms_syncing"
  | "active";

interface PlatformInfo {
  provider: string;
  status: string;
  workspace_name: string | null;
  resource_count: number;
  resource_type: string;
  deliverable_count: number;
  activity_7d: number;
}

interface UsePlatformOnboardingStateReturn {
  /** Current onboarding state */
  state: PlatformOnboardingState | null;
  /** Whether state is loading */
  isLoading: boolean;
  /** Any error that occurred */
  error: Error | null;
  /** Number of connected platforms */
  platformCount: number;
  /** Connected platforms summary */
  platforms: PlatformInfo[];
  /** Whether any platforms are currently syncing */
  hasSyncingPlatforms: boolean;
  /** Total deliverables across all platforms */
  totalDeliverables: number;
  /** Reload the onboarding state */
  reload: () => Promise<void>;
  /** Dismiss the onboarding prompt for this session */
  dismiss: () => void;
  /** Whether prompt has been dismissed */
  isDismissed: boolean;
}

const DISMISS_KEY = "yarnnn_platform_onboarding_dismissed";

export function usePlatformOnboardingState(): UsePlatformOnboardingStateReturn {
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [totalDeliverables, setTotalDeliverables] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [isDismissed, setIsDismissed] = useState(false);
  const [hasSyncingPlatforms, setHasSyncingPlatforms] = useState(false);

  // Check if onboarding was dismissed this session
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
      // Get integration summary for platform status
      const summary = await api.integrations.getSummary();
      setPlatforms(summary.platforms);
      setTotalDeliverables(summary.total_deliverables);

      // Check if any import jobs are in progress
      const jobs = await api.integrations.listImportJobs({ status: "running" });
      setHasSyncingPlatforms((jobs.jobs || []).length > 0);
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

  // Calculate current state
  const calculateState = (): PlatformOnboardingState | null => {
    if (isLoading) return null;

    const connectedPlatforms = platforms.filter(
      (p) => p.status === "connected"
    );

    if (connectedPlatforms.length === 0) {
      return "no_platforms";
    }

    if (hasSyncingPlatforms) {
      return "platforms_syncing";
    }

    // Check if any platform has resources (coverage)
    const hasResources = connectedPlatforms.some((p) => p.resource_count > 0);
    if (!hasResources && connectedPlatforms.length > 0) {
      // Connected but no resources yet - might be syncing
      return "platforms_syncing";
    }

    return "active";
  };

  return {
    state: calculateState(),
    isLoading,
    error,
    platformCount: platforms.filter((p) => p.status === "connected").length,
    platforms,
    hasSyncingPlatforms,
    totalDeliverables,
    reload: load,
    dismiss,
    isDismissed,
  };
}
