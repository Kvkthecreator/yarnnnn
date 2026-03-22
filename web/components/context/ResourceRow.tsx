'use client';

import {
  AlertTriangle,
  Check,
  Lock,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import { categorizeSyncError } from '@/lib/sync-errors';
import type { LandscapeResource } from '@/types';

// =============================================================================
// CoverageBadge
// =============================================================================

export function CoverageBadge({
  state,
  itemsExtracted,
  lastExtractedAt,
  hasError,
}: {
  state: string;
  itemsExtracted?: number;
  lastExtractedAt?: string | null;
  hasError?: boolean;
}) {
  const stateConfig: Record<string, { color: string; bg: string; label: string }> = {
    covered: { color: 'text-muted-foreground', bg: 'bg-muted/40', label: 'Synced' },
    partial: { color: 'text-muted-foreground', bg: 'bg-muted/40', label: 'Synced' },
    stale: { color: 'text-amber-700 dark:text-amber-300', bg: 'bg-amber-50 dark:bg-amber-950/30', label: 'Needs sync' },
    uncovered: { color: 'text-muted-foreground', bg: 'bg-muted/40', label: 'Not synced' },
    excluded: { color: 'text-muted-foreground', bg: 'bg-muted/60', label: 'Excluded' },
    error: { color: 'text-red-700 dark:text-red-300', bg: 'bg-red-50 dark:bg-red-950/30', label: 'Issue' },
  };

  const effectiveState = hasError
    ? 'error'
    : (state === 'uncovered' && ((itemsExtracted && itemsExtracted > 0) || !!lastExtractedAt)) ? 'covered' : state;
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
  /** Platform-specific metadata renderer */
  renderMetadata?: (resource: LandscapeResource) => React.ReactNode;
  /** Whether to show coverage badge */
  showCoverage?: boolean;
}

export function ResourceRow({
  resource,
  resourceIcon,
  isSelected,
  onToggle,
  disabled,
  renderMetadata,
  showCoverage = true,
}: ResourceRowProps) {
  const isPrivate = resource.metadata?.is_private as boolean | undefined;
  const isPrimary = resource.metadata?.primary as boolean | undefined;
  const isDatabase = resource.resource_type === 'database';
  const hasError = !!resource.last_error;

  return (
    <div className={cn(
      'border border-border rounded-lg bg-card overflow-hidden transition-colors',
      isSelected && 'border-primary/35',
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
                <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-muted text-muted-foreground">
                  Primary
                </span>
              )}
              {isDatabase && (
                <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-muted text-muted-foreground">
                  Database
                </span>
              )}
              {isPrivate && (
                <Lock className="w-3 h-3 text-muted-foreground flex-shrink-0" />
              )}
            </div>
            {renderMetadata ? renderMetadata(resource) : (
              (resource.items_extracted > 0 || !!resource.last_extracted_at) && (
                <div className="text-xs text-muted-foreground">
                  {resource.items_extracted > 0 ? `${resource.items_extracted} items` : '0 new items'}
                  {resource.last_extracted_at && (
                    <> synced {formatDistanceToNow(new Date(resource.last_extracted_at), { addSuffix: true })}</>
                  )}
                </div>
              )
            )}
            {hasError && (() => {
              const categorized = categorizeSyncError(resource.last_error);
              const colors = categorized?.severity === 'error'
                ? 'text-red-600 dark:text-red-400'
                : 'text-amber-600 dark:text-amber-400';
              return (
                <div className={cn('text-xs truncate', colors)} title={resource.last_error || ''}>
                  {categorized?.label ?? resource.last_error}
                  {categorized?.hint && (
                    <span className="text-muted-foreground ml-1">— {categorized.hint}</span>
                  )}
                  {resource.last_error_at && (
                    <span className="text-muted-foreground/70 ml-1">
                      ({formatDistanceToNow(new Date(resource.last_error_at), { addSuffix: true })})
                    </span>
                  )}
                </div>
              );
            })()}
          </div>
        </div>

        {/* Right side: Coverage badge + expand button */}
        <div className="flex items-center gap-2 shrink-0">
          {showCoverage && (
            <CoverageBadge
              state={resource.coverage_state}
              itemsExtracted={resource.items_extracted}
              lastExtractedAt={resource.last_extracted_at}
              hasError={hasError}
            />
          )}
        </div>
      </div>
    </div>
  );
}
