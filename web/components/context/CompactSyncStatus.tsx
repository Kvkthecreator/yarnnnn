'use client';

import { useState } from 'react';
import { Loader2, RotateCw, Sparkles, Zap } from 'lucide-react';
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

type HealthColor = 'green' | 'amber' | 'red' | 'blue' | 'gray';

function computeHealth(opts: {
  selectedCount: number;
  syncedCount: number;
  errorCount: number;
  lastSyncedAt?: string | null;
  syncFrequency: string;
  liveQueryMode?: boolean;
}): { color: HealthColor; label: string } {
  if (opts.liveQueryMode) return { color: 'blue', label: 'Live calendar access' };
  if (opts.selectedCount === 0 && opts.syncedCount === 0) return { color: 'gray', label: 'No sources selected' };
  if (opts.selectedCount > 0 && opts.syncedCount === 0) return { color: 'gray', label: `${opts.selectedCount} selected — awaiting first sync` };
  if (opts.errorCount > 0) return { color: 'red', label: `${opts.errorCount} source${opts.errorCount !== 1 ? 's' : ''} with errors` };

  if (opts.lastSyncedAt) {
    const elapsedHours = (Date.now() - new Date(opts.lastSyncedAt).getTime()) / (1000 * 60 * 60);
    if (elapsedHours > getExpectedIntervalHours(opts.syncFrequency) * 2) {
      return { color: 'amber', label: 'Sync behind schedule' };
    }
  }

  return { color: 'green', label: `Syncing ${opts.selectedCount} source${opts.selectedCount !== 1 ? 's' : ''}` };
}

const DOT_CLASSES: Record<HealthColor, string> = {
  green: 'bg-emerald-500',
  amber: 'bg-amber-500',
  red: 'bg-red-500',
  blue: 'bg-blue-500',
  gray: 'bg-muted-foreground/40',
};

const BAR_CLASSES: Record<HealthColor, string> = {
  green: 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900/60',
  amber: 'bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/60',
  red: 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900/60',
  blue: 'bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900/60',
  gray: 'bg-muted/50 border-border',
};

interface CompactSyncStatusProps {
  platform: 'slack' | 'gmail' | 'notion' | 'calendar';
  tier: string;
  syncFrequency: string;
  nextSync?: string | null;
  selectedCount: number;
  syncedCount: number;
  lastSyncedAt?: string | null;
  errorCount?: number;
  liveQueryMode?: boolean;
}

export function CompactSyncStatus({
  platform,
  tier,
  syncFrequency,
  selectedCount,
  syncedCount,
  lastSyncedAt,
  errorCount = 0,
  liveQueryMode = false,
}: CompactSyncStatusProps) {
  const [runningSync, setRunningSync] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const { color, label } = computeHealth({
    selectedCount,
    syncedCount,
    errorCount,
    lastSyncedAt,
    syncFrequency,
    liveQueryMode,
  });

  const frequencyLabel = FREQUENCY_LABELS[syncFrequency] || syncFrequency;

  const handleRunSync = async () => {
    setRunningSync(true);
    setActionMessage(null);
    try {
      const result = await api.integrations.syncPlatform(platform);
      setActionMessage(result.message || 'Sync started.');
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Failed to trigger sync.');
    } finally {
      setRunningSync(false);
    }
  };

  const upgradeHint = tier === 'free'
    ? <><Sparkles className="w-3 h-3 inline" /> Upgrade for faster sync</>
    : tier === 'starter'
      ? <><Zap className="w-3 h-3 inline" /> Pro: hourly sync</>
      : null;

  return (
    <div className={cn('rounded-lg border px-4 py-2.5 flex items-center gap-3 flex-wrap', BAR_CLASSES[color])}>
      <span className={cn('w-2 h-2 rounded-full shrink-0', DOT_CLASSES[color])} />

      <span className="text-sm font-medium">{label}</span>

      {!liveQueryMode && color !== 'gray' && (
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
        {upgradeHint && (
          <span className="text-xs text-muted-foreground hidden md:inline">{upgradeHint}</span>
        )}

        {!liveQueryMode && (
          <button
            onClick={handleRunSync}
            disabled={runningSync}
            className="inline-flex items-center gap-1.5 px-3 py-1 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
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
