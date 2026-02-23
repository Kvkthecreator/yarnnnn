'use client';

import {
  AlertCircle,
  AlertTriangle,
  Check,
  Loader2,
  Sparkles,
} from 'lucide-react';
import type { LandscapeResource, TierLimits, PlatformContentItem } from '@/types';
import { ResourceRow } from './ResourceRow';

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

  /** Resource expansion state (from useResourceExpansion) */
  expandedResourceIds: Set<string>;
  resourceContextCache: Record<string, PlatformContentItem[]>;
  loadingResourceContext: Record<string, boolean>;
  resourceContextTotalCount: Record<string, number>;
  loadingMoreContext: Record<string, boolean>;
  onToggleExpand: (resourceId: string) => void;
  onLoadMore: (resourceId: string) => void;

  /** Per-resource metadata renderer (platform-specific) */
  renderMetadata?: (resource: LandscapeResource) => React.ReactNode;
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
  expandedResourceIds,
  resourceContextCache,
  loadingResourceContext,
  resourceContextTotalCount,
  loadingMoreContext,
  onToggleExpand,
  onLoadMore,
  renderMetadata,
}: ResourceListProps) {
  return (
    <section>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold">{resourceLabel}</h2>
            {workspaceName && (
              <span className="text-sm text-muted-foreground">in {workspaceName}</span>
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            Select which {resourceLabel.toLowerCase()} to include as context sources.
            {' '}{selectedIds.size > limit
              ? `${selectedIds.size} selected · ${limit} included on ${tierLimits?.tier || 'free'} plan`
              : `${selectedIds.size} of ${limit} selected`}
          </p>
        </div>
        {hasChanges && (
          <div className="flex items-center gap-2">
            <button
              onClick={onDiscard}
              className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
            >
              Discard
            </button>
            <button
              onClick={onSave}
              disabled={saving}
              className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
            >
              {saving && <Loader2 className="w-3 h-3 animate-spin" />}
              Save changes
            </button>
          </div>
        )}
      </div>

      {/* Import prompt */}
      {showImportPrompt && (
        <div className="mb-4 p-4 bg-primary/5 border border-primary/20 rounded-lg">
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
                    This gives TP immediate context without waiting for the next scheduled sync.
                  </p>
                  <ul className="mt-2 text-xs text-muted-foreground space-y-0.5">
                    <li>• <strong>Import now</strong>: Get context immediately (last 7 days)</li>
                    <li>• <strong>Skip</strong>: Wait for next scheduled sync ({
                      tierLimits?.limits.sync_frequency === 'hourly' ? 'within 1 hour' :
                      tierLimits?.limits.sync_frequency === '4x_daily' ? 'within 6 hours' :
                      'at 8am or 6pm'
                    })</li>
                  </ul>
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
                  Import Now
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
            <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
          </div>
        </div>
      )}

      {/* Limit warning */}
      {atLimit && !hasChanges && (
        <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-amber-800 dark:text-amber-300">
                {resourceLabelSingular} limit reached
              </p>
              <p className="text-amber-700 dark:text-amber-400 mt-0.5">
                Your {tierLimits?.tier || 'free'} plan allows {limit} {resourceLabel.toLowerCase()}.
                {tierLimits?.tier === 'free' && (
                  <button className="ml-1 underline hover:no-underline inline-flex items-center gap-1">
                    <Sparkles className="w-3 h-3" />
                    Upgrade to Pro
                  </button>
                )}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Resource rows */}
      {resources.length === 0 ? (
        <div className="border border-dashed border-border rounded-lg p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No {resourceLabel.toLowerCase()} found in this workspace.
          </p>
        </div>
      ) : (
        <div className="border border-border rounded-lg divide-y divide-border">
          {resources.map((resource) => (
            <ResourceRow
              key={resource.id}
              resource={resource}
              resourceIcon={resourceIcon}
              isSelected={selectedIds.has(resource.id)}
              onToggle={() => onToggle(resource.id)}
              disabled={!selectedIds.has(resource.id) && atLimit}
              isExpanded={expandedResourceIds.has(resource.id)}
              onToggleExpand={() => onToggleExpand(resource.id)}
              contextItems={resourceContextCache[resource.id] || []}
              loadingContext={loadingResourceContext[resource.id] || false}
              totalCount={resourceContextTotalCount[resource.id] || 0}
              loadingMore={loadingMoreContext[resource.id] || false}
              onLoadMore={() => onLoadMore(resource.id)}
              renderMetadata={renderMetadata}
            />
          ))}
        </div>
      )}
    </section>
  );
}
