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
  showImportPrompt: boolean;
  importing: boolean;
  importProgress: { phase: string; current: number; total: number } | null;
  newlySelectedIds: string[];
  handleToggle: (sourceId: string) => void;
  handleSave: () => Promise<void>;
  handleDiscard: () => void;
  handleImport: () => Promise<void>;
  handleSkipImport: () => void;
}

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
  const [showImportPrompt, setShowImportPrompt] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importProgress, setImportProgress] = useState<{
    phase: string;
    current: number;
    total: number;
  } | null>(null);
  const [newlySelectedIds, setNewlySelectedIds] = useState<string[]>([]);

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
      const addedIds = Array.from(selectedIds).filter((id) => !originalIds.has(id));
      const apiProvider = getApiProvider(platform);
      const result = await api.integrations.updateSources(
        apiProvider,
        Array.from(selectedIds)
      );

      if (result.success) {
        const savedIds = new Set(result.selected_sources.map((s) => s.id));
        setSelectedIds(savedIds);
        setOriginalIds(savedIds);

        // Check if any newly added sources haven't been imported yet
        const uncoveredNewIds = addedIds.filter((id) => {
          const resource = resources.find((r) => r.id === id);
          return resource && resource.coverage_state === 'uncovered';
        });

        if (uncoveredNewIds.length > 0) {
          setNewlySelectedIds(uncoveredNewIds);
          setShowImportPrompt(true);
        }
      } else {
        setError(result.message || 'Failed to save changes');
      }
    } catch (err) {
      console.error('Failed to save sources:', err);
      setError(err instanceof Error ? err.message : 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  }, [platform, resources, selectedIds, originalIds, setSelectedIds, setOriginalIds]);

  const handleDiscard = useCallback(() => {
    setSelectedIds(new Set(originalIds));
  }, [originalIds, setSelectedIds]);

  const handleImport = useCallback(async () => {
    if (newlySelectedIds.length === 0) return;

    setImporting(true);
    setImportProgress({ phase: 'Starting...', current: 0, total: newlySelectedIds.length });

    try {
      for (let i = 0; i < newlySelectedIds.length; i++) {
        const sourceId = newlySelectedIds[i];
        const resource = resources.find((r) => r.id === sourceId);

        setImportProgress({
          phase: `Importing ${resource?.name || sourceId}...`,
          current: i,
          total: newlySelectedIds.length,
        });

        const apiProvider = getApiProvider(platform);
        // Gmail labels need label: prefix for backend processing
        const resourceIdForImport = platform === 'gmail' ? `label:${sourceId}` : sourceId;
        const job = await api.integrations.startImport(apiProvider, {
          resource_id: resourceIdForImport,
          resource_name: resource?.name,
          scope: { recency_days: 7, max_items: 100 },
        });

        // Poll for completion
        let status = job.status;
        while (status === 'pending' || status === 'fetching' || status === 'processing') {
          await new Promise((resolve) => setTimeout(resolve, 2000));
          const updated = await api.integrations.getImportJob(job.id);
          status = updated.status;
        }
      }

      setImportProgress({
        phase: 'Complete!',
        current: newlySelectedIds.length,
        total: newlySelectedIds.length,
      });

      await reload();

      setTimeout(() => {
        setShowImportPrompt(false);
        setImporting(false);
        setImportProgress(null);
        setNewlySelectedIds([]);
      }, 1500);
    } catch (err) {
      console.error('Failed to import sources:', err);
      setError(err instanceof Error ? err.message : 'Failed to import sources');
      setImporting(false);
      setImportProgress(null);
    }
  }, [newlySelectedIds, resources, platform, reload]);

  const handleSkipImport = useCallback(() => {
    setShowImportPrompt(false);
    setNewlySelectedIds([]);
  }, []);

  return {
    hasChanges,
    atLimit,
    limit,
    saving,
    error,
    showImportPrompt,
    importing,
    importProgress,
    newlySelectedIds,
    handleToggle,
    handleSave,
    handleDiscard,
    handleImport,
    handleSkipImport,
  };
}
