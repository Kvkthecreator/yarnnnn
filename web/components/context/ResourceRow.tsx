'use client';

import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  Lock,
  Loader2,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import type { LandscapeResource, PlatformContentItem } from '@/types';

// =============================================================================
// CoverageBadge
// =============================================================================

export function CoverageBadge({
  state,
  itemsExtracted,
  hasError,
}: {
  state: string;
  itemsExtracted?: number;
  hasError?: boolean;
}) {
  const stateConfig: Record<string, { color: string; bg: string; label: string }> = {
    covered: { color: 'text-emerald-700 dark:text-emerald-300', bg: 'bg-emerald-50 dark:bg-emerald-950/30', label: 'On track' },
    partial: { color: 'text-emerald-700 dark:text-emerald-300', bg: 'bg-emerald-50 dark:bg-emerald-950/30', label: 'On track' },
    stale: { color: 'text-amber-700 dark:text-amber-300', bg: 'bg-amber-50 dark:bg-amber-950/30', label: 'Needs sync' },
    uncovered: { color: 'text-muted-foreground', bg: 'bg-muted', label: 'Not synced' },
    excluded: { color: 'text-muted-foreground', bg: 'bg-muted/60', label: 'Excluded' },
    error: { color: 'text-red-700 dark:text-red-300', bg: 'bg-red-50 dark:bg-red-950/30', label: 'Issue' },
  };

  const effectiveState = hasError
    ? 'error'
    : (state === 'uncovered' && itemsExtracted && itemsExtracted > 0) ? 'covered' : state;
  const { color, bg, label } = stateConfig[effectiveState] || stateConfig.uncovered;

  return (
    <span className={cn('px-2 py-0.5 rounded text-xs font-medium', color, bg)}>
      {hasError && <AlertTriangle className="w-3 h-3 inline mr-1 -mt-0.5" />}
      {label}
    </span>
  );
}

// =============================================================================
// ResourceRow
// =============================================================================

interface ResourceRowProps {
  resource: LandscapeResource;
  resourceIcon: React.ReactNode;
  isSelected: boolean;
  onToggle: () => void;
  disabled: boolean;
  isExpanded: boolean;
  onToggleExpand: () => void;
  contextItems: PlatformContentItem[];
  loadingContext: boolean;
  totalCount: number;
  loadingMore: boolean;
  onLoadMore: () => void;
  /** Platform-specific metadata renderer */
  renderMetadata?: (resource: LandscapeResource) => React.ReactNode;
  /** Whether to show coverage badge and expand (false for calendar) */
  showCoverage?: boolean;
}

export function ResourceRow({
  resource,
  resourceIcon,
  isSelected,
  onToggle,
  disabled,
  isExpanded,
  onToggleExpand,
  contextItems,
  loadingContext,
  totalCount,
  loadingMore,
  onLoadMore,
  renderMetadata,
  showCoverage = true,
}: ResourceRowProps) {
  const isPrivate = resource.metadata?.is_private as boolean | undefined;
  const isPrimary = resource.metadata?.primary as boolean | undefined;
  const isDatabase = resource.resource_type === 'database';
  const hasSyncedContent = resource.coverage_state === 'covered' || resource.coverage_state === 'partial' || resource.items_extracted > 0;
  const hasError = !!resource.last_error;

  return (
    <div className={cn(
      'border border-border rounded-lg bg-card overflow-hidden transition-colors',
      isSelected && 'border-primary/40 bg-primary/[0.04]',
      !disabled && 'hover:bg-muted/[0.35]'
    )}>
      {/* Main row */}
      <div
        className={cn(
          'w-full px-4 py-3 flex items-center justify-between',
          disabled ? 'opacity-50' : ''
        )}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Checkbox */}
          <button
            onClick={onToggle}
            disabled={disabled}
            className={cn(
              'w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0',
              isSelected
                ? 'bg-primary border-primary text-primary-foreground'
                : 'border-muted-foreground/30',
              disabled && !isSelected ? 'cursor-not-allowed' : 'cursor-pointer'
            )}
          >
            {isSelected && <Check className="w-3 h-3" />}
          </button>

          {/* Icon */}
          <span className="text-muted-foreground flex-shrink-0">{resourceIcon}</span>

          {/* Name and metadata */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium truncate">{resource.name}</span>
              {isPrimary && (
                <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                  Primary
                </span>
              )}
              {isDatabase && (
                <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                  Database
                </span>
              )}
              {isPrivate && (
                <Lock className="w-3 h-3 text-muted-foreground flex-shrink-0" />
              )}
            </div>
            {renderMetadata ? renderMetadata(resource) : (
              resource.items_extracted > 0 && (
                <div className="text-xs text-muted-foreground">
                  {resource.items_extracted} items
                  {resource.last_extracted_at && (
                    <> synced {formatDistanceToNow(new Date(resource.last_extracted_at), { addSuffix: true })}</>
                  )}
                </div>
              )
            )}
            {hasError && (
              <div className="text-xs text-red-600 dark:text-red-400 truncate" title={resource.last_error || ''}>
                {resource.last_error}
                {resource.last_error_at && (
                  <span className="text-red-500/70 ml-1">
                    ({formatDistanceToNow(new Date(resource.last_error_at), { addSuffix: true })})
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right side: Coverage badge + expand button */}
        <div className="flex items-center gap-2 shrink-0">
          {showCoverage && (
            <CoverageBadge
              state={resource.coverage_state}
              itemsExtracted={resource.items_extracted}
              hasError={hasError}
            />
          )}
          {showCoverage && hasSyncedContent && (
            <button
              onClick={onToggleExpand}
              className="p-1 hover:bg-muted rounded transition-colors"
              title={isExpanded ? 'Hide context' : 'Show context'}
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Expanded context section */}
      {isExpanded && showCoverage && hasSyncedContent && (
        <div className="px-4 pb-3 pl-12 border-t border-border bg-muted/[0.2]">
          {loadingContext ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Loading context...</span>
            </div>
          ) : contextItems.length === 0 ? (
            <div className="text-xs text-muted-foreground py-2">
              No synced content found for this resource.
            </div>
          ) : (
            <div className="space-y-1.5">
              {contextItems.map((item) => (
                <div
                  key={item.id}
                  className={cn(
                    "flex items-start gap-2 text-xs py-1.5 px-2 rounded",
                    item.retained ? "bg-green-50 dark:bg-green-950/20" : "bg-muted/50"
                  )}
                >
                  <span className="text-muted-foreground shrink-0">└─</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <p className="text-foreground/80 line-clamp-2 flex-1">{item.content}</p>
                      {item.retained && (
                        <span className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                          Retained
                        </span>
                      )}
                    </div>
                    <p className="text-muted-foreground mt-0.5">
                      {item.source_timestamp && formatDistanceToNow(new Date(item.source_timestamp), { addSuffix: true })}
                    </p>
                  </div>
                </div>
              ))}

              {contextItems.length > 0 && (
                <div className="flex items-center justify-between ml-6 pt-2">
                  <span className="text-xs text-muted-foreground">
                    Showing {contextItems.length} of {totalCount} items
                  </span>
                  {contextItems.length < totalCount && (
                    <button
                      onClick={onLoadMore}
                      disabled={loadingMore}
                      className="text-xs text-primary hover:text-primary/80 disabled:opacity-50 flex items-center gap-1"
                    >
                      {loadingMore ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Loading...
                        </>
                      ) : (
                        <>Load more</>
                      )}
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
