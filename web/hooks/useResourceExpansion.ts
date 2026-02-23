'use client';

import { useState, useCallback } from 'react';
import { api } from '@/lib/api/client';
import type { PlatformProvider, PlatformContentItem } from '@/types';

interface UseResourceExpansionReturn {
  expandedResourceIds: Set<string>;
  resourceContextCache: Record<string, PlatformContentItem[]>;
  loadingResourceContext: Record<string, boolean>;
  resourceContextTotalCount: Record<string, number>;
  loadingMoreContext: Record<string, boolean>;
  handleToggleExpand: (resourceId: string) => Promise<void>;
  handleLoadMore: (resourceId: string) => Promise<void>;
}

export function useResourceExpansion(
  platform: PlatformProvider
): UseResourceExpansionReturn {
  const [expandedResourceIds, setExpandedResourceIds] = useState<Set<string>>(new Set());
  const [resourceContextCache, setResourceContextCache] = useState<
    Record<string, PlatformContentItem[]>
  >({});
  const [loadingResourceContext, setLoadingResourceContext] = useState<
    Record<string, boolean>
  >({});
  const [resourceContextTotalCount, setResourceContextTotalCount] = useState<
    Record<string, number>
  >({});
  const [loadingMoreContext, setLoadingMoreContext] = useState<Record<string, boolean>>({});

  const handleToggleExpand = useCallback(
    async (resourceId: string) => {
      const isCurrentlyExpanded = expandedResourceIds.has(resourceId);

      if (isCurrentlyExpanded) {
        setExpandedResourceIds((prev) => {
          const next = new Set(prev);
          next.delete(resourceId);
          return next;
        });
      } else {
        setExpandedResourceIds((prev) => new Set(prev).add(resourceId));

        if (!resourceContextCache[resourceId]) {
          setLoadingResourceContext((prev) => ({ ...prev, [resourceId]: true }));
          try {
            // Gmail uses label: prefix for resource_id query
            const queryResourceId =
              platform === 'gmail' ? `label:${resourceId}` : resourceId;
            const result = await api.integrations.getPlatformContext(
              platform as 'slack' | 'notion' | 'gmail' | 'calendar',
              { limit: 10, resourceId: queryResourceId }
            );
            setResourceContextCache((prev) => ({
              ...prev,
              [resourceId]: result.items || [],
            }));
            setResourceContextTotalCount((prev) => ({
              ...prev,
              [resourceId]: result.total_count || 0,
            }));
          } catch (err) {
            console.error('Failed to load resource context:', err);
            setResourceContextCache((prev) => ({ ...prev, [resourceId]: [] }));
            setResourceContextTotalCount((prev) => ({ ...prev, [resourceId]: 0 }));
          } finally {
            setLoadingResourceContext((prev) => ({ ...prev, [resourceId]: false }));
          }
        }
      }
    },
    [platform, expandedResourceIds, resourceContextCache]
  );

  const handleLoadMore = useCallback(
    async (resourceId: string) => {
      const currentItems = resourceContextCache[resourceId] || [];
      setLoadingMoreContext((prev) => ({ ...prev, [resourceId]: true }));

      try {
        const queryResourceId =
          platform === 'gmail' ? `label:${resourceId}` : resourceId;
        const result = await api.integrations.getPlatformContext(
          platform as 'slack' | 'notion' | 'gmail' | 'calendar',
          { limit: 10, resourceId: queryResourceId, offset: currentItems.length }
        );

        setResourceContextCache((prev) => ({
          ...prev,
          [resourceId]: [...currentItems, ...(result.items || [])],
        }));
      } catch (err) {
        console.error('Failed to load more context:', err);
      } finally {
        setLoadingMoreContext((prev) => ({ ...prev, [resourceId]: false }));
      }
    },
    [platform, resourceContextCache]
  );

  return {
    expandedResourceIds,
    resourceContextCache,
    loadingResourceContext,
    resourceContextTotalCount,
    loadingMoreContext,
    handleToggleExpand,
    handleLoadMore,
  };
}
