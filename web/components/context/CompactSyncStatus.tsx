'use client';

import { useEffect, useRef, useState } from 'react';
import { Loader2, RotateCw } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';

const FREQUENCY_LABELS: Record<string, string> = {
  hourly: 'Hourly',
  '4x_daily': 'Every 6h',
  '2x_daily': 'Twice daily',
  '1x_daily': 'Daily',
};

function getExpectedIntervalHours(syncFrequency: string): number {
  const intervals: Record<string, number> = {
    hourly: 1,
    '4x_daily': 6,
    '2x_daily': 12,
    '1x_daily': 24,
  };
  return intervals[syncFrequency] ?? 12;
}

type HealthTone = 'neutral' | 'amber' | 'red';

function computeHealth(opts: {
  selectedCount: number;
  syncedCount: number;
  errorCount: number;
  lastSyncedAt?: string | null;
  syncFrequency: string;
  liveQueryMode?: boolean;
}): { tone: HealthTone; label: string } {
  if (opts.liveQueryMode) return { tone: 'neutral', label: 'Live calendar access' };
  if (opts.errorCount > 0) return { tone: 'red', label: `${opts.errorCount} source${opts.errorCount !== 1 ? 's' : ''} with errors` };
  if (opts.selectedCount === 0) return { tone: 'neutral', label: 'No sources selected' };
  if (opts.syncedCount === 0) return { tone: 'neutral', label: `${opts.selectedCount} selected · awaiting first sync` };

  if (opts.lastSyncedAt) {
    const elapsedHours = (Date.now() - new Date(opts.lastSyncedAt).getTime()) / (1000 * 60 * 60);
    if (elapsedHours > getExpectedIntervalHours(opts.syncFrequency) * 2) {
      return { tone: 'amber', label: 'Sync behind schedule' };
    }
  }

  if (opts.syncedCount < opts.selectedCount) {
    return { tone: 'neutral', label: `${opts.syncedCount}/${opts.selectedCount} sources synced` };
  }

  return { tone: 'neutral', label: `${opts.selectedCount} source${opts.selectedCount !== 1 ? 's' : ''} synced` };
}

const DOT_CLASSES: Record<HealthTone, string> = {
  neutral: 'bg-muted-foreground/45',
  amber: 'bg-amber-500',
  red: 'bg-red-500',
};

const BAR_CLASSES: Record<HealthTone, string> = {
  neutral: 'bg-card border-border',
  amber: 'bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/60',
  red: 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900/60',
};

interface CompactSyncStatusProps {
  platform: 'slack' | 'gmail' | 'notion' | 'calendar' | 'yarnnn';
  tier: string;
  syncFrequency: string;
  selectedCount: number;
  syncedCount: number;
  lastSyncedAt?: string | null;
  errorCount?: number;
  liveQueryMode?: boolean;
  selectedResourceIds?: string[];
  onSyncTriggered?: () => Promise<void> | void;
}

function toEpochMs(value?: string | null): number {
  if (!value) return 0;
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function matchesSelectedResource(resourceId: string | null | undefined, selectedIds: Set<string>): boolean {
  if (!resourceId || selectedIds.size === 0) return true;
  if (selectedIds.has(resourceId)) return true;

  if (resourceId.startsWith('label:')) {
    const plainId = resourceId.slice('label:'.length);
    if (selectedIds.has(plainId)) return true;
  } else if (selectedIds.has(`label:${resourceId}`)) {
    return true;
  }

  return false;
}

export function CompactSyncStatus({
  platform,
  tier: _tier,
  syncFrequency,
  selectedCount,
  syncedCount,
  lastSyncedAt,
  errorCount = 0,
  liveQueryMode = false,
  selectedResourceIds = [],
  onSyncTriggered,
}: CompactSyncStatusProps) {
  const [runningSync, setRunningSync] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const { tone, label } = computeHealth({
    selectedCount,
    syncedCount,
    errorCount,
    lastSyncedAt,
    syncFrequency,
    liveQueryMode,
  });

  const frequencyLabel = FREQUENCY_LABELS[syncFrequency] || syncFrequency;

  const handleRunSync = async () => {
    const baselineSyncedAt = toEpochMs(lastSyncedAt);
    const selectedIdSet = new Set(selectedResourceIds);

    setRunningSync(true);
    setActionMessage(null);

    try {
      const result = await api.integrations.syncPlatform(platform);
      setActionMessage(result.message || 'Sync started.');

      if (!result.success) {
        return;
      }

      const maxPolls = 30; // ~60 seconds
      for (let attempt = 1; attempt <= maxPolls; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 2000));
        if (!isMountedRef.current) return;

        const status = await api.integrations.getSyncStatus(platform);
        const scopedResources = status.synced_resources.filter((entry) =>
          matchesSelectedResource(entry.resource_id, selectedIdSet)
        );
        const syncedScopedCount = scopedResources.filter((entry) => !!entry.last_synced).length;
        const newestSyncMs = scopedResources.reduce((latest, entry) => {
          const entryTs = toEpochMs(entry.last_synced);
          return entryTs > latest ? entryTs : latest;
        }, 0);

        setActionMessage(`Sync in progress… ${syncedScopedCount}/${selectedCount} sources acknowledged`);

        const hasAdvancedSync = newestSyncMs > baselineSyncedAt;
        const hasFirstSync = baselineSyncedAt === 0 && syncedScopedCount > 0;
        if (hasAdvancedSync || hasFirstSync || status.error_count > 0) {
          if (onSyncTriggered) {
            await Promise.resolve(onSyncTriggered());
          }
          if (!isMountedRef.current) return;

          if (status.error_count > 0) {
            setActionMessage(`Sync finished with ${status.error_count} source error${status.error_count === 1 ? '' : 's'}.`);
          } else {
            setActionMessage('Sync complete. Status updated.');
          }
          return;
        }
      }

      if (onSyncTriggered) {
        await Promise.resolve(onSyncTriggered());
      }
      if (isMountedRef.current) {
        setActionMessage('Sync is still running. Status will update shortly.');
      }
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Failed to trigger sync.');
    } finally {
      if (isMountedRef.current) {
        setRunningSync(false);
      }
    }
  };

  return (
    <div className={cn('rounded-lg border px-4 py-2.5 flex items-center gap-3 flex-wrap', BAR_CLASSES[tone])}>
      <span className={cn('w-2 h-2 rounded-full shrink-0', DOT_CLASSES[tone])} />

      <span className="text-sm font-medium">{label}</span>

      {!liveQueryMode && (
        <>
          <span className="text-sm text-muted-foreground">·</span>
          <span className="text-sm text-muted-foreground">{frequencyLabel}</span>
        </>
      )}

      {lastSyncedAt && (
        <>
          <span className="text-sm text-muted-foreground">·</span>
          <span className="text-sm text-muted-foreground">
            Last {formatDistanceToNow(new Date(lastSyncedAt), { addSuffix: true })}
          </span>
        </>
      )}

      {liveQueryMode && (
        <>
          <span className="text-sm text-muted-foreground">·</span>
          <span className="text-sm text-muted-foreground">Events queried on demand</span>
        </>
      )}

      <div className="flex items-center gap-2 ml-auto">
        {!liveQueryMode && (
          <button
            onClick={handleRunSync}
            disabled={runningSync}
            className="inline-flex items-center gap-1.5 px-3 py-1 text-xs rounded-md border border-border bg-background text-foreground hover:bg-muted disabled:opacity-50"
          >
            {runningSync ? <Loader2 className="w-3 h-3 animate-spin" /> : <RotateCw className="w-3 h-3" />}
            Run sync
          </button>
        )}
      </div>

      {actionMessage && (
        <div className="w-full text-xs text-muted-foreground mt-1">
          {actionMessage}
        </div>
      )}
    </div>
  );
}
