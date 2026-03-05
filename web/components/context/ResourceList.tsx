'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Check,
  CheckCircle2,
  Loader2,
  Search,
  Sparkles,
} from 'lucide-react';
import type { LandscapeResource, TierLimits } from '@/types';
import { cn } from '@/lib/utils';
import { ResourceRow } from './ResourceRow';

type ListView = 'selected' | 'recommended' | 'all' | 'attention';

interface ResourceListProps {
  /** Platform-specific config */
  resourceLabel: string;
  resourceLabelSingular: string;
  resourceIcon: React.ReactNode;
  workspaceName: string | null;

  /** Data */
  resources: LandscapeResource[];
  tierLimits: TierLimits | null;

  /** Source selection state (from useSourceSelection) */
  selectedIds: Set<string>;
  hasChanges: boolean;
  atLimit: boolean;
  limit: number;
  saving: boolean;
  error: string | null;
  showImportPrompt: boolean;
  importing: boolean;
  importProgress: { phase: string; current: number; total: number } | null;
  newlySelectedIds: string[];
  onToggle: (sourceId: string) => void;
  onSave: () => void;
  onDiscard: () => void;
  onImport: () => void;
  onSkipImport: () => void;

  /** Per-resource metadata renderer (platform-specific) */
  renderMetadata?: (resource: LandscapeResource) => React.ReactNode;

  /** Whether this is a first-connect flow (OAuth just completed) */
  justConnected?: boolean;
  platformLabel?: string;
}

export function ResourceList({
  resourceLabel,
  resourceLabelSingular,
  resourceIcon,
  workspaceName,
  resources,
  tierLimits,
  selectedIds,
  hasChanges,
  atLimit,
  limit,
  saving,
  error,
  showImportPrompt,
  importing,
  importProgress,
  newlySelectedIds,
  onToggle,
  onSave,
  onDiscard,
  onImport,
  onSkipImport,
  renderMetadata,
  justConnected,
  platformLabel,
}: ResourceListProps) {
  const [query, setQuery] = useState('');
  const [view, setView] = useState<ListView>('selected');

  const selectedCount = selectedIds.size;
  const syncedCount = useMemo(
    () => resources.filter((resource) => !!resource.last_extracted_at).length,
    [resources]
  );
  const recommendedCount = useMemo(
    () => resources.filter((resource) => resource.recommended).length,
    [resources]
  );
  const attentionCount = useMemo(
    () => resources.filter((resource) => !!resource.last_error).length,
    [resources]
  );

  useEffect(() => {
    // Keep the default view action-oriented: selected first, then recommended.
    if (selectedCount === 0 && view === 'selected') {
      setView(recommendedCount > 0 ? 'recommended' : 'all');
    }
  }, [selectedCount, recommendedCount, view]);

  const sortedResources = useMemo(() => {
    return [...resources].sort((a, b) => {
      const aSelected = selectedIds.has(a.id) ? 1 : 0;
      const bSelected = selectedIds.has(b.id) ? 1 : 0;
      if (aSelected !== bSelected) return bSelected - aSelected;

      const aError = a.last_error ? 1 : 0;
      const bError = b.last_error ? 1 : 0;
      if (aError !== bError) return bError - aError;

      const aSynced = a.last_extracted_at ? 1 : 0;
      const bSynced = b.last_extracted_at ? 1 : 0;
      if (aSynced !== bSynced) return bSynced - aSynced;

      return a.name.localeCompare(b.name);
    });
  }, [resources, selectedIds]);

  const baseItems = useMemo(() => {
    switch (view) {
      case 'selected':
        return sortedResources.filter((resource) => selectedIds.has(resource.id));
      case 'recommended':
        return sortedResources.filter((resource) => resource.recommended);
      case 'attention':
        return sortedResources.filter((resource) => !!resource.last_error);
      case 'all':
      default:
        return sortedResources;
    }
  }, [view, sortedResources, selectedIds]);

  const filteredItems = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return baseItems;
    return baseItems.filter((resource) => {
      const nameMatch = resource.name.toLowerCase().includes(q);
      const typeMatch = resource.resource_type.toLowerCase().includes(q);
      return nameMatch || typeMatch;
    });
  }, [baseItems, query]);

  const renderResourceRow = (resource: LandscapeResource) => (
    <ResourceRow
      key={resource.id}
      resource={resource}
      resourceIcon={resourceIcon}
      isSelected={selectedIds.has(resource.id)}
      onToggle={() => onToggle(resource.id)}
      disabled={!selectedIds.has(resource.id) && atLimit}
      renderMetadata={renderMetadata}
    />
  );

  const upgradeTarget = tierLimits?.tier === 'free' ? 'Starter' : tierLimits?.tier === 'starter' ? 'Pro' : null;
  const normalizedLimit = Math.max(limit, 1);
  const selectedRatio = Math.min(selectedCount / normalizedLimit, 1);

  const viewOptions: Array<{ key: ListView; label: string; count: number }> = [
    { key: 'selected', label: 'Selected', count: selectedCount },
    { key: 'recommended', label: 'Recommended', count: recommendedCount },
    { key: 'all', label: 'All', count: resources.length },
    { key: 'attention', label: 'Issues', count: attentionCount },
  ];

  return (
    <section className="space-y-4">
      {justConnected && (
        <div className="p-4 bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-800 rounded-lg">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-green-800 dark:text-green-300">
                {platformLabel || resourceLabel} Connected
              </p>
              <p className="text-sm text-green-700 dark:text-green-400 mt-0.5">
                Choose high-signal sources first, then run sync to start usable context.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="border border-border rounded-xl bg-card p-4 md:p-5 space-y-4">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold">{resourceLabel}</h2>
              {workspaceName && (
                <span className="text-sm text-muted-foreground">in {workspaceName}</span>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              Step 1: select the {resourceLabel.toLowerCase()} that should feed context.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onDiscard}
              disabled={!hasChanges || saving}
              className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground disabled:opacity-50"
            >
              Discard
            </button>
            <button
              onClick={onSave}
              disabled={!hasChanges || saving}
              className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
            >
              {saving && <Loader2 className="w-3 h-3 animate-spin" />}
              Save changes
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <StatCard
            label="Selected"
            value={`${selectedCount}/${limit}`}
            tone={selectedCount >= limit ? 'amber' : 'default'}
          />
          <StatCard
            label="Synced"
            value={`${syncedCount}`}
            tone={syncedCount > 0 ? 'green' : 'default'}
          />
          <StatCard
            label="Needs Attention"
            value={`${attentionCount}`}
            tone={attentionCount > 0 ? 'red' : 'default'}
          />
        </div>

        <div className="h-2 rounded-full bg-muted overflow-hidden">
          <div
            className={cn(
              'h-full transition-all',
              selectedCount >= limit ? 'bg-amber-500' : 'bg-primary'
            )}
            style={{ width: `${selectedRatio * 100}%` }}
          />
        </div>

        <div className="flex flex-wrap gap-2 items-center">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={`Search ${resourceLabel.toLowerCase()}...`}
              className="w-full h-9 pl-9 pr-3 text-sm bg-background border border-border rounded-md outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div className="flex items-center gap-1 p-1 border border-border rounded-md bg-muted/20">
            {viewOptions.map((option) => (
              <button
                key={option.key}
                onClick={() => setView(option.key)}
                className={cn(
                  'px-2.5 py-1 text-xs rounded-md transition-colors',
                  view === option.key
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {option.label} ({option.count})
              </button>
            ))}
          </div>
        </div>
      </div>

      {showImportPrompt && (
        <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
          {importing ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                <span className="text-sm font-medium">{importProgress?.phase}</span>
              </div>
              {importProgress && importProgress.total > 1 && (
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all"
                    style={{ width: `${(importProgress.current / importProgress.total) * 100}%` }}
                  />
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Sources saved successfully</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Import recent context from {newlySelectedIds.length === 1 ? 'this source' : `these ${newlySelectedIds.length} sources`}?
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Import now gives immediate context. Skip waits for scheduled sync.
                  </p>
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-4">
                <button
                  onClick={onSkipImport}
                  className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
                >
                  Wait for sync
                </button>
                <button
                  onClick={onImport}
                  className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
                >
                  Import now
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
            <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
          </div>
        </div>
      )}

      {atLimit && !hasChanges && (
        <div className="p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-amber-800 dark:text-amber-300">
                {resourceLabelSingular} limit reached
              </p>
              <p className="text-amber-700 dark:text-amber-400 mt-0.5">
                Your {tierLimits?.tier || 'free'} plan allows {limit} {resourceLabel.toLowerCase()}.
                {upgradeTarget && (
                  <button className="ml-1 underline hover:no-underline inline-flex items-center gap-1">
                    <Sparkles className="w-3 h-3" />
                    Upgrade to {upgradeTarget}
                  </button>
                )}
              </p>
            </div>
          </div>
        </div>
      )}

      {resources.length === 0 ? (
        <div className="border border-dashed border-border rounded-lg p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No {resourceLabel.toLowerCase()} found in this workspace.
          </p>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="border border-dashed border-border rounded-lg p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No {resourceLabel.toLowerCase()} match this view.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredItems.map(renderResourceRow)}
        </div>
      )}
    </section>
  );
}

function StatCard({
  label,
  value,
  tone = 'default',
}: {
  label: string;
  value: string;
  tone?: 'default' | 'green' | 'amber' | 'red';
}) {
  const toneClasses: Record<string, string> = {
    default: 'border-border bg-muted/20 text-foreground',
    green: 'border-emerald-200 dark:border-emerald-900/60 bg-emerald-50 dark:bg-emerald-950/20 text-emerald-800 dark:text-emerald-300',
    amber: 'border-amber-200 dark:border-amber-900/60 bg-amber-50 dark:bg-amber-950/20 text-amber-800 dark:text-amber-300',
    red: 'border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/20 text-red-800 dark:text-red-300',
  };

  return (
    <div className={cn('rounded-md border px-3 py-2', toneClasses[tone])}>
      <p className="text-[11px] uppercase tracking-wide opacity-80">{label}</p>
      <p className="text-sm font-semibold mt-0.5">{value}</p>
    </div>
  );
}
