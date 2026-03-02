'use client';

import {
  AlertTriangle,
  Check,
  Lock,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import type { LandscapeResource } from '@/types';

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
  /** Platform-specific metadata renderer */
  renderMetadata?: (resource: LandscapeResource) => React.ReactNode;
  /** Whether to show coverage badge (false for calendar) */
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
        </div>
      </div>
    </div>
  );
}
