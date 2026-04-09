'use client';

import { useState, useCallback } from 'react';
import { api } from '@/lib/api/client';
import type {
  PlatformProvider,
  LandscapeResource,
  TierLimits,
  NumericLimitField,
} from '@/types';
import { getApiProvider } from '@/types';

interface UseSourceSelectionProps {
  platform: PlatformProvider;
  resources: LandscapeResource[];
  tierLimits: TierLimits | null;
  limitField: NumericLimitField;
  selectedIds: Set<string>;
  originalIds: Set<string>;
  setSelectedIds: React.Dispatch<React.SetStateAction<Set<string>>>;
  setOriginalIds: React.Dispatch<React.SetStateAction<Set<string>>>;
  reload: () => Promise<void>;
}

interface UseSourceSelectionReturn {
  hasChanges: boolean;
  atLimit: boolean;
  limit: number;
  saving: boolean;
  error: string | null;
  handleToggle: (sourceId: string) => void;
  handleSave: () => Promise<void>;
  handleDiscard: () => void;
}

/**
 * Source selection hook — manages platform source (channel/page) selection.
 * ADR-153/156: Import jobs removed. Platform data flows through task execution.
 */
export function useSourceSelection({
  platform,
  resources,
  tierLimits,
  limitField,
  selectedIds,
  originalIds,
  setSelectedIds,
  setOriginalIds,
  reload,
}: UseSourceSelectionProps): UseSourceSelectionReturn {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const limit = (tierLimits?.limits[limitField] as number) || 5;
  const atLimit = selectedIds.size >= limit;
  const hasChanges =
    selectedIds.size !== originalIds.size ||
    !Array.from(selectedIds).every((id) => originalIds.has(id));

  const handleToggle = useCallback(
    (sourceId: string) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        if (next.has(sourceId)) {
          next.delete(sourceId);
        } else if (next.size < limit) {
          next.add(sourceId);
        }
        return next;
      });
    },
    [limit, setSelectedIds]
  );

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);

    try {
      const apiProvider = getApiProvider(platform) as "slack" | "notion" | "github";
      const result = await api.integrations.updateSources(
        apiProvider,
        Array.from(selectedIds)
      );

      if (result.success) {
        const savedIds = new Set(result.selected_sources.map((s) => s.id));
        setSelectedIds(savedIds);
        setOriginalIds(savedIds);
      } else {
        setError(result.message || 'Failed to save changes');
      }
    } catch (err) {
      console.error('Failed to save sources:', err);
      setError(err instanceof Error ? err.message : 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  }, [platform, selectedIds, setSelectedIds, setOriginalIds]);

  const handleDiscard = useCallback(() => {
    setSelectedIds(new Set(originalIds));
  }, [originalIds, setSelectedIds]);

  return {
    hasChanges,
    atLimit,
    limit,
    saving,
    error,
    handleToggle,
    handleSave,
    handleDiscard,
  };
}
