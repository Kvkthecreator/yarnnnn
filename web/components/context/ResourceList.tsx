'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  BadgeAlert,
  CheckCircle2,
  Loader2,
  Search,
  Sparkles,
} from 'lucide-react';
import type { LandscapeResource, TierLimits } from '@/types';
import { cn } from '@/lib/utils';
import { ResourceRow } from './ResourceRow';

type ListView = 'selected' | 'all' | 'attention';

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
  onToggle: (sourceId: string) => void;
  onSave: () => void;
  onDiscard: () => void;

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
  onToggle,
  onSave,
  onDiscard,
  renderMetadata,
  justConnected,
  platformLabel,
}: ResourceListProps) {
  const [query, setQuery] = useState('');
  const [view, setView] = useState<ListView>('selected');

  const isAttentionResource = (resource: LandscapeResource): boolean => {
    const isSelected = selectedIds.has(resource.id);
    const hasError = !!resource.last_error;
    const needsFirstSync = isSelected && !resource.last_extracted_at;
    const isStale = isSelected && resource.coverage_state === 'stale';
    return isSelected && (hasError || needsFirstSync || isStale);
  };

  const selectedCount = selectedIds.size;
  const syncedCount = useMemo(
    () => resources.filter((resource) => selectedIds.has(resource.id) && !!resource.last_extracted_at).length,
    [resources, selectedIds]
  );
  const attentionCount = useMemo(
    () => resources.filter(isAttentionResource).length,
    [resources, selectedIds]
  );
  const attentionBreakdown = useMemo(() => {
    let errors = 0;
    let needsFirstSync = 0;
    let stale = 0;
    for (const resource of resources) {
      const isSelected = selectedIds.has(resource.id);
      if (!isSelected) continue;

      if (resource.last_error) {
        errors += 1;
      } else if (!resource.last_extracted_at) {
        needsFirstSync += 1;
      } else if (resource.coverage_state === 'stale') {
        stale += 1;
      }
    }
    return { errors, needsFirstSync, stale };
  }, [resources, selectedIds]);

  useEffect(() => {
    // Keep the default view action-oriented: selected first.
    if (selectedCount === 0 && view === 'selected') {
      setView('all');
    }
  }, [selectedCount, view]);

  // Snapshot the selected IDs at mount / after save so sort order stays stable
  // during active editing. The sort only changes when resources change (reload
  // after save) or on first render — never mid-toggle.
  const stableSortIdsRef = useRef<Set<string>>(selectedIds);
  useEffect(() => {
    stableSortIdsRef.current = new Set(selectedIds);
  }, [resources]); // intentionally keyed on resources, not selectedIds

  const sortedResources = useMemo(() => {
    const snapshot = stableSortIdsRef.current;
    return [...resources].sort((a, b) => {
      const aSelected = snapshot.has(a.id) ? 1 : 0;
      const bSelected = snapshot.has(b.id) ? 1 : 0;
      if (aSelected !== bSelected) return bSelected - aSelected;

      const aError = a.last_error ? 1 : 0;
      const bError = b.last_error ? 1 : 0;
      if (aError !== bError) return bError - aError;

      const aSynced = a.last_extracted_at ? 1 : 0;
      const bSynced = b.last_extracted_at ? 1 : 0;
      if (aSynced !== bSynced) return bSynced - aSynced;

      return a.name.localeCompare(b.name);
    });
  }, [resources]);

  const baseItems = useMemo(() => {
    switch (view) {
      case 'selected':
        return sortedResources.filter((resource) => selectedIds.has(resource.id));
      case 'attention':
        return sortedResources.filter(isAttentionResource);
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

  const upgradeTarget = tierLimits?.tier === 'free' ? 'Pro' : null;

  const viewOptions: Array<{ key: ListView; label: string; count: number }> = [
    { key: 'selected', label: 'Selected', count: selectedCount },
    { key: 'all', label: 'All', count: resources.length },
    { key: 'attention', label: 'Attention', count: attentionCount },
  ];

  return (
    <section className="space-y-3">
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
          {hasChanges && (
            <div className="flex items-center gap-3">
              <button
                onClick={onDiscard}
                disabled={saving}
                className="text-sm text-muted-foreground hover:text-foreground disabled:opacity-50"
              >
                Reset
              </button>
              <button
                onClick={onSave}
                disabled={saving}
                className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
              >
                {saving && <Loader2 className="w-3 h-3 animate-spin" />}
                Save
              </button>
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-muted-foreground">
          <span>
            <span className="text-foreground font-medium">{selectedCount}/{limit}</span> selected
          </span>
          <span>·</span>
          <span>
            <span className="text-foreground font-medium">{syncedCount}</span> synced
          </span>
          <span>·</span>
          <span>
            <span className={cn('font-medium', attentionCount > 0 ? 'text-amber-700 dark:text-amber-300' : 'text-foreground')}>
              {attentionCount}
            </span>{' '}
            attention
          </span>
          {hasChanges && (
            <>
              <span>·</span>
              <span className="text-foreground">Unsaved source changes</span>
            </>
          )}
        </div>

        {attentionCount > 0 && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <BadgeAlert className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
            <span>
              {attentionBreakdown.errors > 0 && `${attentionBreakdown.errors} error${attentionBreakdown.errors === 1 ? '' : 's'}`}
              {attentionBreakdown.errors > 0 && (attentionBreakdown.needsFirstSync > 0 || attentionBreakdown.stale > 0) && ' · '}
              {attentionBreakdown.needsFirstSync > 0 && `${attentionBreakdown.needsFirstSync} pending first sync`}
              {attentionBreakdown.needsFirstSync > 0 && attentionBreakdown.stale > 0 && ' · '}
              {attentionBreakdown.stale > 0 && `${attentionBreakdown.stale} stale`}
            </span>
          </div>
        )}

        {/* ADR-153/156: Import prompt removed. Platform data flows through task execution. */}

        <div className="flex flex-wrap gap-2 items-center pt-1">
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
                  'px-2.5 py-1 text-xs rounded-md transition-colors whitespace-nowrap',
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

        <div className="pt-1">
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
        </div>
      </div>

    </section>
  );
}
