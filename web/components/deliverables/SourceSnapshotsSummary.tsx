'use client';

/**
 * ADR-049: Source Snapshots Summary
 *
 * Displays what sources were used at generation time.
 * Shows platform, resource name, sync timestamp, and item counts.
 */

import { formatDistanceToNow } from 'date-fns';
import { Database, MessageSquare, Mail, FileText, Clock, Package } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SourceSnapshot } from '@/types';

interface SourceSnapshotsSummaryProps {
  snapshots: SourceSnapshot[];
  compact?: boolean;
  className?: string;
}

const platformConfig: Record<string, { icon: React.ComponentType<{ className?: string }>; label: string; color: string }> = {
  slack: { icon: MessageSquare, label: 'Slack', color: 'text-purple-600' },
  gmail: { icon: Mail, label: 'Gmail', color: 'text-red-600' },
  notion: { icon: FileText, label: 'Notion', color: 'text-gray-600' },
  calendar: { icon: Clock, label: 'Calendar', color: 'text-blue-600' },
};

/**
 * Full display of source snapshots with details
 */
export function SourceSnapshotsSummary({
  snapshots,
  compact = false,
  className,
}: SourceSnapshotsSummaryProps) {
  if (!snapshots || snapshots.length === 0) {
    return (
      <div className={cn('text-xs text-muted-foreground', className)}>
        <span className="flex items-center gap-1.5">
          <Package className="w-3 h-3" />
          No source data recorded
        </span>
      </div>
    );
  }

  if (compact) {
    return (
      <div className={cn('flex items-center gap-2 text-xs text-muted-foreground', className)}>
        <Database className="w-3 h-3" />
        <span>
          {snapshots.length} source{snapshots.length !== 1 ? 's' : ''} used
        </span>
        {snapshots.map((s, i) => {
          const config = platformConfig[s.platform] || { icon: Database, label: s.platform, color: 'text-gray-500' };
          const Icon = config.icon;
          return (
            <span key={i} className="inline-flex items-center gap-1" title={`${s.resource_name || s.resource_id}`}>
              <Icon className={cn('w-3 h-3', config.color)} />
            </span>
          );
        })}
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Database className="w-3.5 h-3.5" />
        Sources used at generation
      </div>
      <div className="space-y-1.5">
        {snapshots.map((snapshot, index) => {
          const config = platformConfig[snapshot.platform] || { icon: Database, label: snapshot.platform, color: 'text-gray-500' };
          const Icon = config.icon;
          const syncedAt = snapshot.synced_at ? new Date(snapshot.synced_at) : null;

          return (
            <div
              key={index}
              className="flex items-center justify-between px-3 py-2 bg-muted/50 rounded-md text-xs"
            >
              <div className="flex items-center gap-2">
                <Icon className={cn('w-4 h-4', config.color)} />
                <span className="font-medium">
                  {snapshot.resource_name || snapshot.resource_id}
                </span>
                <span className="text-muted-foreground">
                  ({config.label})
                </span>
              </div>
              <div className="flex items-center gap-3 text-muted-foreground">
                {snapshot.item_count !== undefined && snapshot.item_count > 0 && (
                  <span>{snapshot.item_count} items</span>
                )}
                {syncedAt && (
                  <span title={syncedAt.toLocaleString()}>
                    {formatDistanceToNow(syncedAt, { addSuffix: true })}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Inline badge showing source count
 */
export function SourceSnapshotsBadge({
  snapshots,
  className,
}: {
  snapshots: SourceSnapshot[] | undefined;
  className?: string;
}) {
  if (!snapshots || snapshots.length === 0) {
    return null;
  }

  // Find oldest sync
  const oldestSync = snapshots.reduce((oldest, s) => {
    if (!s.synced_at) return oldest;
    const syncDate = new Date(s.synced_at);
    if (!oldest || syncDate < oldest) return syncDate;
    return oldest;
  }, null as Date | null);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 text-xs text-muted-foreground',
        className
      )}
      title={`Generated with ${snapshots.length} source(s)`}
    >
      <Database className="w-3 h-3" />
      {snapshots.length} source{snapshots.length !== 1 ? 's' : ''}
      {oldestSync && (
        <span className="ml-1">
          • synced {formatDistanceToNow(oldestSync, { addSuffix: true })}
        </span>
      )}
    </span>
  );
}

export default SourceSnapshotsSummary;
