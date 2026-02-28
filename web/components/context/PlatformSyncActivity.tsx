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
type HealthState = 'on_track' | 'needs_sync' | 'not_synced';
type CadenceState = 'on_schedule' | 'delayed' | 'behind' | 'unknown' | 'live_mode';

interface SyncResource {
  resource_id: string;
  resource_name: string | null;
  last_synced: string | null;
  freshness_status: 'fresh' | 'recent' | 'stale' | 'unknown';
  items_synced: number;
}

interface SyncStatusResponse {
  synced_resources: SyncResource[];
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

function formatSyncFrequency(syncFrequency?: string): string | null {
  if (!syncFrequency) return null;
  const labels: Record<string, string> = {
    hourly: 'Hourly',
    '4x_daily': 'Every 6 hours',
    '2x_daily': 'Twice daily',
    '1x_daily': 'Daily',
  };
  return labels[syncFrequency] || syncFrequency;
}

function expectedCadenceHours(syncFrequency?: string): number | null {
  if (!syncFrequency) return null;
  const hours: Record<string, number> = {
    hourly: 1,
    '4x_daily': 6,
    '2x_daily': 12,
    '1x_daily': 24,
  };
  return hours[syncFrequency] ?? null;
}

function resourceHealth(resource: SyncResource): HealthState {
  if (resource.freshness_status === 'stale') return 'needs_sync';
  if (resource.freshness_status === 'unknown') return 'not_synced';
  return 'on_track';
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

function cadenceState(
  lastRunAt: string | null,
  syncFrequency?: string,
  liveQueryMode?: boolean
): CadenceState {
  if (liveQueryMode) return 'live_mode';
  if (!lastRunAt) return 'unknown';

  const cadenceHours = expectedCadenceHours(syncFrequency);
  if (!cadenceHours) return 'unknown';

  const elapsedHours = (Date.now() - new Date(lastRunAt).getTime()) / (1000 * 60 * 60);
  if (elapsedHours <= cadenceHours * 1.5) return 'on_schedule';
  if (elapsedHours <= cadenceHours * 3) return 'delayed';
  return 'behind';
}

function statusClasses(state: CadenceState): { box: string; text: string } {
  switch (state) {
    case 'on_schedule':
      return {
        box: 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900/60',
        text: 'text-emerald-800 dark:text-emerald-300',
      };
    case 'delayed':
    case 'behind':
      return {
        box: 'bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/60',
        text: 'text-amber-800 dark:text-amber-300',
      };
    case 'live_mode':
      return {
        box: 'bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900/60',
        text: 'text-blue-800 dark:text-blue-300',
      };
    default:
      return {
        box: 'bg-muted/50 border-border',
        text: 'text-foreground',
      };
  }
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
  const resources = syncStatus?.synced_resources || [];
  const resourceCount = resources.length;
  const onTrackCount = resources.filter((r) => resourceHealth(r) === 'on_track').length;
  const needsSyncCount = resources.filter((r) => resourceHealth(r) === 'needs_sync').length;
  const notSyncedCount = resources.filter((r) => resourceHealth(r) === 'not_synced').length;
  const latestItemsSynced = extractItemsSynced(latestEvent);
  const frequencyLabel = formatSyncFrequency(syncFrequency);

  const lastRunAt = latestEvent?.created_at || resources.reduce((latest, r) => {
    if (!r.last_synced) return latest;
    if (!latest) return r.last_synced;
    return new Date(r.last_synced) > new Date(latest) ? r.last_synced : latest;
  }, null as string | null);

  const cadence = cadenceState(lastRunAt, syncFrequency, liveQueryMode);
  const style = statusClasses(cadence);

  const summaryTitle = (() => {
    if (cadence === 'live_mode') return 'Live calendar access';
    if (cadence === 'on_schedule') return 'Sync is on schedule';
    if (cadence === 'delayed') return 'Sync is delayed';
    if (cadence === 'behind') return 'Sync is behind';
    return 'Sync status unavailable';
  })();

  const summaryBody = (() => {
    if (cadence === 'live_mode') {
      return 'Calendar events are queried live. Background sync runs are supplemental.';
    }
    if (cadence === 'unknown') {
      return 'No recent sync run detected yet. Select sources and run a sync to initialize status.';
    }
    const cadenceText = frequencyLabel ? `Expected cadence: ${frequencyLabel.toLowerCase()}.` : '';
    const lastRunText = lastRunAt
      ? `Last run ${formatDistanceToNow(new Date(lastRunAt), { addSuffix: true })}.`
      : '';
    return `${lastRunText} ${cadenceText}`.trim();
  })();

  const attentionResources = useMemo(() => {
    return [...resources]
      .sort((a, b) => {
        const rank: Record<HealthState, number> = {
          needs_sync: 0,
          not_synced: 1,
          on_track: 2,
        };
        return rank[resourceHealth(a)] - rank[resourceHealth(b)];
      })
      .slice(0, 6);
  }, [resources]);

  return (
    <section className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="px-4 md:px-5 py-3 border-b border-border bg-muted/20">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">Sync status</h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              Clear view of cadence, source health, and recent runs.
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
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
          <div className={cn('rounded-lg border px-3 py-2.5', style.box)}>
            <div className="flex items-start gap-2">
              {cadence === 'on_schedule' ? (
                <CheckCircle2 className={cn('w-4 h-4 mt-0.5', style.text)} />
              ) : (
                <AlertTriangle className={cn('w-4 h-4 mt-0.5', style.text)} />
              )}
              <div>
                <p className={cn('text-sm font-medium', style.text)}>{summaryTitle}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{summaryBody}</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <div className="rounded-lg border border-border bg-background p-3">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Sources tracked</p>
              <p className="text-lg font-semibold mt-1">{resourceCount}</p>
            </div>
            <div className="rounded-lg border border-border bg-background p-3">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">On track</p>
              <p className="text-lg font-semibold mt-1 text-emerald-600 dark:text-emerald-400">{onTrackCount}</p>
            </div>
            <div className="rounded-lg border border-border bg-background p-3">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Need sync</p>
              <p className="text-lg font-semibold mt-1 text-amber-600 dark:text-amber-400">{needsSyncCount}</p>
            </div>
            <div className="rounded-lg border border-border bg-background p-3">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Last run items</p>
              <p className="text-lg font-semibold mt-1">{latestItemsSynced}</p>
            </div>
          </div>

          {(frequencyLabel || nextSync || notSyncedCount > 0) && (
            <div className="rounded-lg border border-border bg-background px-3 py-2 text-xs text-muted-foreground flex flex-wrap items-center gap-x-4 gap-y-1">
              {frequencyLabel && (
                <span className="inline-flex items-center gap-1">
                  <Clock3 className="w-3 h-3" />
                  Cadence: <span className="font-medium text-foreground">{frequencyLabel}</span>
                </span>
              )}
              {nextSync && (
                <span className="inline-flex items-center gap-1">
                  <History className="w-3 h-3" />
                  Next sync {formatDistanceToNow(new Date(nextSync), { addSuffix: true })}
                </span>
              )}
              {notSyncedCount > 0 && (
                <span>{notSyncedCount} source{notSyncedCount > 1 ? 's' : ''} not synced yet</span>
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
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Source health
                </p>
              </div>
              {attentionResources.length === 0 ? (
                <div className="px-3 py-4 text-sm text-muted-foreground">
                  No synced sources yet.
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {attentionResources.map((resource) => {
                    const health = resourceHealth(resource);
                    return (
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
                          'px-2 py-0.5 rounded text-xs font-medium',
                          health === 'on_track' && 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300',
                          health === 'needs_sync' && 'bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300',
                          health === 'not_synced' && 'bg-muted text-muted-foreground'
                        )}>
                          {health === 'on_track' ? 'On track' : health === 'needs_sync' ? 'Needs sync' : 'Not synced'}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="rounded-lg border border-border overflow-hidden">
              <div className="px-3 py-2 border-b border-border bg-muted/20">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Recent sync runs</p>
              </div>
              {events.length === 0 ? (
                <div className="px-3 py-4 text-sm text-muted-foreground">
                  No sync runs in the last 30 days.
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {events.slice(0, 6).map((event) => {
                    const errored = Boolean(event.metadata?.error) || event.summary.toLowerCase().includes('(error)');
                    return (
                      <div key={event.id} className="px-3 py-2.5 flex items-start gap-2.5">
                        {errored ? (
                          <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                        ) : (
                          <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
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
