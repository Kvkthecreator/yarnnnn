'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api/client';
import type {
  PlatformProvider,
  IntegrationData,
  LandscapeResource,
  SelectedSource,
  TierLimits,
  PlatformDeliverable,
  PlatformContentItem,
} from '@/types';
import { getApiProvider, BACKEND_PROVIDER_MAP } from '@/types';

interface UsePlatformDataReturn {
  integration: IntegrationData | null;
  resources: LandscapeResource[];
  selectedIds: Set<string>;
  originalIds: Set<string>;
  tierLimits: TierLimits | null;
  deliverables: PlatformDeliverable[];
  platformContext: PlatformContentItem[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  setSelectedIds: React.Dispatch<React.SetStateAction<Set<string>>>;
  setOriginalIds: React.Dispatch<React.SetStateAction<Set<string>>>;
}

interface UsePlatformDataOptions {
  /** Skip landscape/sources fetch (e.g. for calendar) */
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
  const [deliverables, setDeliverables] = useState<PlatformDeliverable[]>([]);
  const [platformContext, setPlatformContext] = useState<PlatformContentItem[]>([]);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const apiProvider = getApiProvider(platform);
      const backendProviders = BACKEND_PROVIDER_MAP[platform];

      const [
        integrationResult,
        landscapeResult,
        sourcesResult,
        limitsResult,
        deliverablesResult,
        platformContextResult,
        calendarsResult,
      ] = await Promise.all([
        api.integrations.get(apiProvider).catch(() => null),
        options?.skipResources
          ? Promise.resolve({ resources: [] })
          : api.integrations.getLandscape(apiProvider).catch(() => ({ resources: [] })),
        options?.skipResources
          ? Promise.resolve({ sources: [] })
          : api.integrations.getSources(apiProvider).catch(() => ({ sources: [] })),
        api.integrations.getLimits().catch(() => null),
        api.deliverables.list().catch(() => []),
        options?.skipContext
          ? Promise.resolve({ items: [], total_count: 0, freshest_at: null, platform })
          : api.integrations.getPlatformContext(
              platform as "slack" | "notion" | "gmail" | "calendar",
              { limit: 10 }
            ).catch(() => ({ items: [], total_count: 0, freshest_at: null, platform })),
        // Load available calendars for Calendar platform
        platform === 'calendar'
          ? api.integrations.listGoogleCalendars().catch(() => ({ calendars: [] }))
          : Promise.resolve({ calendars: [] }),
      ]);

      setIntegration(integrationResult as IntegrationData | null);

      // For calendar, convert calendars list to resources format
      if (platform === 'calendar' && calendarsResult?.calendars) {
        const calendarResources: LandscapeResource[] = calendarsResult.calendars.map(
          (cal: { id: string; summary: string; primary?: boolean }) => ({
            id: cal.id,
            name: cal.summary,
            resource_type: 'calendar',
            coverage_state: 'uncovered' as const,
            last_extracted_at: null,
            items_extracted: 0,
            metadata: { primary: cal.primary },
            last_error: null,
            last_error_at: null,
            recommended: false,
          })
        );
        setResources(calendarResources);
      } else {
        setResources((landscapeResult as { resources: LandscapeResource[] }).resources || []);
      }

      setTierLimits(limitsResult as TierLimits | null);

      // Set selected IDs from sources endpoint
      const currentIds = new Set(
        ((sourcesResult as { sources: SelectedSource[] }).sources || []).map(
          (s: SelectedSource) => s.id
        )
      );
      setSelectedIds(currentIds);
      setOriginalIds(currentIds);

      // Filter deliverables targeting this platform
      const platformDeliverables = ((deliverablesResult || []) as PlatformDeliverable[]).filter(
        (d: PlatformDeliverable) =>
          backendProviders.includes(d.destination?.platform || '')
      );
      setDeliverables(platformDeliverables);

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
    deliverables,
    platformContext,
    loading,
    error,
    reload: loadData,
    setSelectedIds,
    setOriginalIds,
  };
}
