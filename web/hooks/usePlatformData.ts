'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api/client';
import type {
  PlatformProvider,
  IntegrationData,
  LandscapeResource,
  SelectedSource,
  TierLimits,
  PlatformContentItem,
} from '@/types';
import { getApiProvider } from '@/types';

interface UsePlatformDataReturn {
  integration: IntegrationData | null;
  resources: LandscapeResource[];
  selectedIds: Set<string>;
  originalIds: Set<string>;
  tierLimits: TierLimits | null;
  platformContext: PlatformContentItem[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  setSelectedIds: React.Dispatch<React.SetStateAction<Set<string>>>;
  setOriginalIds: React.Dispatch<React.SetStateAction<Set<string>>>;
}

interface UsePlatformDataOptions {
  /** Skip landscape/sources fetch */
  skipResources?: boolean;
  /** Skip platform context fetch */
  skipContext?: boolean;
}

export function usePlatformData(
  platform: PlatformProvider,
  options?: UsePlatformDataOptions
): UsePlatformDataReturn {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [integration, setIntegration] = useState<IntegrationData | null>(null);
  const [resources, setResources] = useState<LandscapeResource[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [originalIds, setOriginalIds] = useState<Set<string>>(new Set());
  const [tierLimits, setTierLimits] = useState<TierLimits | null>(null);
  const [platformContext, setPlatformContext] = useState<PlatformContentItem[]>([]);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const apiProvider = getApiProvider(platform);

      const [
        integrationResult,
        landscapeResult,
        sourcesResult,
        limitsResult,
        platformContextResult,
      ] = await Promise.all([
        api.integrations.get(apiProvider).catch(() => null),
        options?.skipResources
          ? Promise.resolve({ resources: [] })
          : api.integrations.getLandscape(apiProvider).catch(() => ({ resources: [] })),
        options?.skipResources
          ? Promise.resolve({ sources: [] })
          : api.integrations.getSources(apiProvider).catch(() => ({ sources: [] })),
        api.integrations.getLimits().catch(() => null),
        options?.skipContext
          ? Promise.resolve({ items: [], total_count: 0, freshest_at: null, platform })
          : api.integrations.getPlatformContext(apiProvider, { limit: 10 })
              .catch(() => ({ items: [], total_count: 0, freshest_at: null, platform })),
      ]);

      setIntegration(integrationResult as IntegrationData | null);
      setResources((landscapeResult as { resources: LandscapeResource[] }).resources || []);

      setTierLimits(limitsResult as TierLimits | null);

      // Set selected IDs from sources endpoint
      const currentIds = new Set(
        ((sourcesResult as { sources: SelectedSource[] }).sources || []).map(
          (s: SelectedSource) => s.id
        )
      );
      setSelectedIds(currentIds);
      setOriginalIds(currentIds);

      // Set platform context
      setPlatformContext(
        (platformContextResult as { items: PlatformContentItem[] })?.items || []
      );
    } catch (err) {
      console.error('Failed to load platform data:', err);
      setError('Failed to load platform data');
    } finally {
      setLoading(false);
    }
  }, [platform, options?.skipResources, options?.skipContext]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return {
    integration,
    resources,
    selectedIds,
    originalIds,
    tierLimits,
    platformContext,
    loading,
    error,
    reload: loadData,
    setSelectedIds,
    setOriginalIds,
  };
}
