'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api/client';
import type {
  PlatformProvider,
  IntegrationData,
  LandscapeResource,
  SelectedSource,
} from '@/types';
import { getApiProvider } from '@/types';

interface UsePlatformDataReturn {
  integration: IntegrationData | null;
  resources: LandscapeResource[];
  selectedIds: Set<string>;
  originalIds: Set<string>;
  /** @deprecated ADR-172: source limits dissolved */
  tierLimits: null;
  platformContext: unknown[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  setSelectedIds: React.Dispatch<React.SetStateAction<Set<string>>>;
  setOriginalIds: React.Dispatch<React.SetStateAction<Set<string>>>;
}

interface UsePlatformDataOptions {
  /** Skip landscape/sources fetch */
  skipResources?: boolean;
  /** ADR-153: platform context fetch removed */
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
  const [tierLimits] = useState<null>(null); // ADR-172: source limits dissolved
  const [platformContext] = useState<unknown[]>([]);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const apiProvider = getApiProvider(platform);

      const [
        integrationResult,
        landscapeResult,
        sourcesResult,
      ] = await Promise.all([
        api.integrations.get(apiProvider).catch(() => null),
        options?.skipResources
          ? Promise.resolve({ resources: [] })
          : api.integrations.getLandscape(apiProvider).catch(() => ({ resources: [] })),
        options?.skipResources
          ? Promise.resolve({ sources: [] })
          : api.integrations.getSources(apiProvider).catch(() => ({ sources: [] })),
      ]);

      setIntegration(integrationResult as IntegrationData | null);
      setResources((landscapeResult as { resources: LandscapeResource[] }).resources || []);

      // Set selected IDs from sources endpoint
      const currentIds = new Set(
        ((sourcesResult as { sources: SelectedSource[] }).sources || []).map(
          (s: SelectedSource) => s.id
        )
      );
      setSelectedIds(currentIds);
      setOriginalIds(currentIds);

      // ADR-153: platform context fetch removed
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
