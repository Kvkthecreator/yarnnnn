'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Database,
  History,
  Loader2,
  RefreshCw,
  RotateCw,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';

type PlatformKey = 'slack' | 'gmail' | 'notion' | 'calendar';

interface SyncResource {
  resource_id: string;
  resource_name: string | null;
  last_synced: string | null;
  freshness_status: 'fresh' | 'recent' | 'stale' | 'unknown';
  items_synced: number;
}

interface SyncStatusResponse {
  platform: string;
  synced_resources: SyncResource[];
  stale_count: number;
}

interface PlatformSyncEvent {
  id: string;
  summary: string;
  created_at: string;
  metadata: Record<string, unknown> | null;
}

interface PlatformSyncActivityProps {
  platform: PlatformKey;
  syncFrequency?: string;
  nextSync?: string | null;
  liveQueryMode?: boolean;
}

const PLATFORM_ACCENTS: Record<PlatformKey, { border: string; bg: string; text: string }> = {
  slack: {
    border: 'border-purple-200 dark:border-purple-900/60',
    bg: 'bg-purple-50/80 dark:bg-purple-950/20',
    text: 'text-purple-700 dark:text-purple-300',
  },
  gmail: {
    border: 'border-red-200 dark:border-red-900/60',
    bg: 'bg-red-50/80 dark:bg-red-950/20',
    text: 'text-red-700 dark:text-red-300',
  },
  notion: {
    border: 'border-neutral-300 dark:border-neutral-700',
    bg: 'bg-neutral-100/70 dark:bg-neutral-900/40',
    text: 'text-neutral-700 dark:text-neutral-300',
  },
  calendar: {
    border: 'border-blue-200 dark:border-blue-900/60',
    bg: 'bg-blue-50/80 dark:bg-blue-950/20',
    text: 'text-blue-700 dark:text-blue-300',
  },
};

function formatSyncFrequency(syncFrequency?: string): string | null {
  if (!syncFrequency) return null;

  const labels: Record<string, string> = {
    '1x_daily': 'Daily',
    '2x_daily': '2x daily',
    '4x_daily': '4x daily',
    hourly: 'Hourly',
  };

  return labels[syncFrequency] || syncFrequency;
}

function extractItemsSynced(event: PlatformSyncEvent | null): number {
  if (!event?.metadata) return 0;
  const raw = event.metadata.items_synced;
  if (typeof raw === 'number') return raw;
  if (typeof raw === 'string') {
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function isSyncError(event: PlatformSyncEvent): boolean {
  const hasErrorMeta = Boolean(event.metadata && event.metadata.error);
  return hasErrorMeta || event.summary.toLowerCase().includes('(error)');
}

export function PlatformSyncActivity({
  platform,
  syncFrequency,
  nextSync,
  liveQueryMode = false,
}: PlatformSyncActivityProps) {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [runningSync, setRunningSync] = useState(false);
  const [syncStatus, setSyncStatus] = useState<SyncStatusResponse | null>(null);
  const [events, setEvents] = useState<PlatformSyncEvent[]>([]);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadData = useCallback(async (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    setActionMessage(null);

    try {
      const [statusResult, activityResult] = await Promise.all([
        api.integrations.getSyncStatus(platform).catch(() => null),
        api.activity.list({ eventType: 'platform_synced', limit: 200, days: 30 }).catch(() => ({ activities: [] })),
      ]);

      const platformEvents = (activityResult.activities || [])
        .filter((event) => {
          const metadata = (event.metadata || {}) as Record<string, unknown>;
          const eventPlatform = String(metadata.platform || metadata.provider || '').toLowerCase();
          return eventPlatform === platform;
        })
        .slice(0, 8)
        .map((event) => ({
          id: event.id,
          summary: event.summary,
          created_at: event.created_at,
          metadata: event.metadata as Record<string, unknown> | null,
        }));

      setSyncStatus(statusResult as SyncStatusResponse | null);
      setEvents(platformEvents);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [platform]);

  useEffect(() => {
    loadData(true);
  }, [loadData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData(false);
  };

  const handleRunSync = async () => {
    setRunningSync(true);
    setActionMessage(null);
    try {
      const result = await api.integrations.syncPlatform(platform);
      setActionMessage(result.message || 'Sync started.');
      await loadData(false);
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Failed to trigger sync.');
    } finally {
      setRunningSync(false);
    }
  };

  const latestEvent = events[0] || null;
  const resourceCount = syncStatus?.synced_resources.length || 0;
  const staleCount = syncStatus?.stale_count || 0;
  const healthyCount = Math.max(resourceCount - staleCount, 0);
  const latestItemsSynced = extractItemsSynced(latestEvent);

  const topResources = useMemo(() => {
    const rows = [...(syncStatus?.synced_resources || [])];
    return rows
      .sort((a, b) => {
        const rank: Record<SyncResource['freshness_status'], number> = {
          stale: 0,
          unknown: 1,
          recent: 2,
          fresh: 3,
        };
        return rank[a.freshness_status] - rank[b.freshness_status];
      })
      .slice(0, 6);
  }, [syncStatus]);

  const accent = PLATFORM_ACCENTS[platform];
  const frequencyLabel = formatSyncFrequency(syncFrequency);

  return (
    <section className="rounded-xl border border-border bg-card overflow-hidden">
      <div className={cn('px-4 md:px-5 py-3 border-b', accent.bg, accent.border)}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">Sync Activity</h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              {liveQueryMode
                ? 'Calendar is live-first. Sync records appear when refresh jobs run.'
                : 'Platform freshness, recent sync runs, and source-level status.'}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {frequencyLabel && (
              <span className={cn('hidden md:inline-flex px-2 py-1 rounded-md text-xs font-medium border', accent.bg, accent.border, accent.text)}>
                {frequencyLabel}
              </span>
            )}
            <button
              onClick={handleRefresh}
              disabled={refreshing || loading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted disabled:opacity-50"
            >
              <RefreshCw className={cn('w-3 h-3', refreshing && 'animate-spin')} />
              Refresh
            </button>
            {!liveQueryMode && (
              <button
                onClick={handleRunSync}
                disabled={runningSync}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
              >
                {runningSync ? <Loader2 className="w-3 h-3 animate-spin" /> : <RotateCw className="w-3 h-3" />}
                Run sync
              </button>
            )}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="px-4 md:px-5 py-8 flex items-center justify-center">
          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="px-4 md:px-5 py-4 space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <div className="rounded-lg border border-border bg-muted/30 p-3">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Tracked sources</p>
              <p className="text-lg font-semibold mt-1">{resourceCount}</p>
            </div>
            <div className="rounded-lg border border-border bg-muted/30 p-3">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Healthy</p>
              <p className="text-lg font-semibold mt-1 text-green-600 dark:text-green-400">{healthyCount}</p>
            </div>
            <div className="rounded-lg border border-border bg-muted/30 p-3">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Stale</p>
              <p className="text-lg font-semibold mt-1 text-amber-600 dark:text-amber-400">{staleCount}</p>
            </div>
            <div className="rounded-lg border border-border bg-muted/30 p-3">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Latest items</p>
              <p className="text-lg font-semibold mt-1">{latestItemsSynced}</p>
            </div>
          </div>

          {(frequencyLabel || nextSync) && (
            <div className="rounded-lg border border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground flex flex-wrap items-center gap-x-4 gap-y-1">
              {frequencyLabel && (
                <span className="inline-flex items-center gap-1">
                  <Clock3 className="w-3 h-3" />
                  Frequency: <span className="font-medium text-foreground">{frequencyLabel}</span>
                </span>
              )}
              {nextSync && (
                <span className="inline-flex items-center gap-1">
                  <History className="w-3 h-3" />
                  Next sync {formatDistanceToNow(new Date(nextSync), { addSuffix: true })}
                </span>
              )}
            </div>
          )}

          {actionMessage && (
            <div className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
              {actionMessage}
            </div>
          )}

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
            <div className="rounded-lg border border-border overflow-hidden">
              <div className="px-3 py-2 border-b border-border bg-muted/20">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Resource freshness</p>
              </div>
              {topResources.length === 0 ? (
                <div className="px-3 py-4 text-sm text-muted-foreground">
                  No synced resources yet.
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {topResources.map((resource) => (
                    <div key={resource.resource_id} className="px-3 py-2.5 flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{resource.resource_name || resource.resource_id}</p>
                        <p className="text-xs text-muted-foreground">
                          {resource.last_synced
                            ? `Last synced ${formatDistanceToNow(new Date(resource.last_synced), { addSuffix: true })}`
                            : 'No sync timestamp yet'}
                        </p>
                      </div>
                      <span className={cn(
                        'px-2 py-0.5 rounded text-xs font-medium capitalize',
                        resource.freshness_status === 'fresh' && 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
                        resource.freshness_status === 'recent' && 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
                        resource.freshness_status === 'stale' && 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
                        resource.freshness_status === 'unknown' && 'bg-muted text-muted-foreground'
                      )}>
                        {resource.freshness_status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-lg border border-border overflow-hidden">
              <div className="px-3 py-2 border-b border-border bg-muted/20">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Recent sync runs</p>
              </div>
              {events.length === 0 ? (
                <div className="px-3 py-4 text-sm text-muted-foreground">
                  No sync activity in the last 30 days.
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {events.slice(0, 6).map((event) => {
                    const errored = isSyncError(event);
                    return (
                      <div key={event.id} className="px-3 py-2.5 flex items-start gap-2.5">
                        {errored ? (
                          <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                        ) : (
                          <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="text-sm truncate">{event.summary}</p>
                          <p className="text-xs text-muted-foreground mt-0.5 inline-flex items-center gap-1">
                            <Database className="w-3 h-3" />
                            {formatDistanceToNow(new Date(event.created_at), { addSuffix: true })}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
