'use client';

/**
 * System section for Settings page.
 *
 * Shows:
 * - Background job status (Platform Sync, Memory & Analysis)
 * - Sync schedule observability
 *
 * ADR-133: Connected platforms moved to Connectors tab.
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  Activity,
  Brain,
  HeartPulse,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
// (ConnectedIntegrationsSection moved to Connectors tab — ADR-133)

// =============================================================================
// Types
// =============================================================================

interface BackgroundJobStatus {
  job_type: string;
  last_run_at: string | null;
  last_run_status: 'success' | 'failed' | 'never_run' | 'unknown';
  last_run_summary: string | null;
  items_processed: number;
  schedule_description: string | null;
}

interface ScheduleWindow {
  time: string;
  time_utc: string;
  status: 'completed' | 'failed' | 'missed' | 'upcoming' | 'active';
}

interface SyncSchedule {
  timezone: string;
  sync_frequency_label: string;
  todays_windows: ScheduleWindow[];
  next_sync_at: string | null;
}

// =============================================================================
// Sub-Components
// =============================================================================

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    healthy: {
      bg: 'bg-green-100 dark:bg-green-900/30',
      text: 'text-green-700 dark:text-green-400',
      icon: <CheckCircle2 className="w-3 h-3" />,
    },
    fresh: {
      bg: 'bg-green-100 dark:bg-green-900/30',
      text: 'text-green-700 dark:text-green-400',
      icon: <CheckCircle2 className="w-3 h-3" />,
    },
    recent: {
      bg: 'bg-blue-100 dark:bg-blue-900/30',
      text: 'text-blue-700 dark:text-blue-400',
      icon: <Clock className="w-3 h-3" />,
    },
    stale: {
      bg: 'bg-amber-100 dark:bg-amber-900/30',
      text: 'text-amber-700 dark:text-amber-400',
      icon: <AlertTriangle className="w-3 h-3" />,
    },
    pending: {
      bg: 'bg-blue-100 dark:bg-blue-900/30',
      text: 'text-blue-700 dark:text-blue-400',
      icon: <Clock className="w-3 h-3" />,
    },
    disconnected: {
      bg: 'bg-gray-100 dark:bg-gray-800',
      text: 'text-gray-500 dark:text-gray-400',
      icon: <XCircle className="w-3 h-3" />,
    },
    success: {
      bg: 'bg-green-100 dark:bg-green-900/30',
      text: 'text-green-700 dark:text-green-400',
      icon: <CheckCircle2 className="w-3 h-3" />,
    },
    failed: {
      bg: 'bg-red-100 dark:bg-red-900/30',
      text: 'text-red-700 dark:text-red-400',
      icon: <XCircle className="w-3 h-3" />,
    },
    never_run: {
      bg: 'bg-gray-100 dark:bg-gray-800',
      text: 'text-gray-500 dark:text-gray-400',
      icon: <Clock className="w-3 h-3" />,
    },
    never_synced: {
      bg: 'bg-gray-100 dark:bg-gray-800',
      text: 'text-gray-500 dark:text-gray-400',
      icon: <XCircle className="w-3 h-3" />,
    },
    unknown: {
      bg: 'bg-gray-100 dark:bg-gray-800',
      text: 'text-gray-500 dark:text-gray-400',
      icon: <AlertTriangle className="w-3 h-3" />,
    },
  };

  const { bg, text, icon } = config[status] || config.unknown;

  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium', bg, text)}>
      {icon}
      <span className="capitalize">{status.replace(/_/g, ' ')}</span>
    </span>
  );
}

const BACKGROUND_JOB_GROUPS = [
  {
    label: 'Platform Sync',
    icon: <RefreshCw className="w-4 h-4 text-green-500" />,
    types: ['Platform Sync'],
  },
  {
    label: 'Task Execution',
    icon: <HeartPulse className="w-4 h-4 text-cyan-500" />,
    types: ['Task Execution'],
  },
  {
    label: 'Memory & Analysis',
    icon: <Brain className="w-4 h-4 text-purple-500" />,
    types: [
      'Memory Extraction',
      'Session Summaries',
      'Composer Heartbeat',
      'Content Cleanup',
    ],
  },
];

// =============================================================================
// Main Exported Component
// =============================================================================

export function SystemSection() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [backgroundJobs, setBackgroundJobs] = useState<BackgroundJobStatus[]>([]);
  const [syncSchedule, setSyncSchedule] = useState<SyncSchedule | null>(null);
  const [expandedMemoryDetail, setExpandedMemoryDetail] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const result = await api.system.getStatus();
      setBackgroundJobs(result.background_jobs);
      setSyncSchedule(result.sync_schedule ?? null);
    } catch (err) {
      console.error('Failed to load system status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const groupedJobs = BACKGROUND_JOB_GROUPS.map((group) => {
    const matchingJobs = backgroundJobs.filter((j) => group.types.includes(j.job_type));

    if (group.types.length === 1) {
      const job = matchingJobs[0];
      return {
        ...group,
        lastRunAt: job?.last_run_at ?? null,
        lastRunStatus: job?.last_run_status ?? 'never_run',
        lastRunSummary: job?.last_run_summary ?? null,
        itemsProcessed: job?.items_processed ?? 0,
        scheduleDescription: job?.schedule_description ?? null,
        subJobs: [],
      };
    }

    const withTimestamps = matchingJobs.filter((j) => j.last_run_at);
    const mostRecent = withTimestamps.sort(
      (a, b) => new Date(b.last_run_at!).getTime() - new Date(a.last_run_at!).getTime()
    )[0];
    const hasFailed = matchingJobs.some((j) => j.last_run_status === 'failed');
    const allNeverRun = matchingJobs.every((j) => j.last_run_status === 'never_run');

    return {
      ...group,
      lastRunAt: mostRecent?.last_run_at ?? null,
      lastRunStatus: allNeverRun ? 'never_run' : hasFailed ? 'failed' : 'success',
      lastRunSummary: mostRecent?.last_run_summary ?? null,
      itemsProcessed: matchingJobs.reduce((sum, j) => sum + j.items_processed, 0),
      scheduleDescription: null,
      subJobs: matchingJobs,
    };
  });

  return (
    <div className="space-y-6">
      {/* Header with refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">System</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Sync status and background processing.
          </p>
        </div>
        <button
          onClick={() => loadData()}
          disabled={loading}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-8">
          {/* ADR-133: Connected Platforms moved to Connectors tab */}

          {/* Background Activity */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold">Background Activity</h3>
            </div>

            {/* Sync schedule */}
            {syncSchedule && (
              <div className="border border-border rounded-lg p-4 mb-3 space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-muted text-xs font-medium text-muted-foreground">
                      <Clock className="w-3 h-3" />
                      {syncSchedule.timezone}
                    </span>
                    <span className="text-muted-foreground">
                      {syncSchedule.sync_frequency_label} sync
                    </span>
                  </div>
                  {syncSchedule.next_sync_at && (
                    <span className="text-xs text-muted-foreground">
                      Next: {formatDistanceToNow(new Date(syncSchedule.next_sync_at), { addSuffix: true })}
                    </span>
                  )}
                </div>
                {/* Window pills */}
                {syncSchedule.todays_windows.length <= 8 ? (
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {syncSchedule.todays_windows.map((w) => {
                      const colors: Record<string, string> = {
                        completed: 'bg-green-500',
                        failed: 'bg-amber-500',
                        missed: 'bg-red-500',
                        upcoming: 'bg-gray-300 dark:bg-gray-600',
                        active: 'bg-blue-500 animate-pulse',
                      };
                      return (
                        <div key={w.time} className="flex flex-col items-center gap-0.5" title={`${w.time} — ${w.status}`}>
                          <div className={cn('w-2.5 h-2.5 rounded-full', colors[w.status] || colors.upcoming)} />
                          <span className="text-[10px] text-muted-foreground leading-none">{w.time}</span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-xs text-muted-foreground">
                    {syncSchedule.todays_windows.filter((w) => w.status === 'completed').length}/
                    {syncSchedule.todays_windows.length} windows completed today
                    {syncSchedule.todays_windows.some((w) => w.status === 'failed') && (
                      <span className="text-amber-500 ml-2">
                        ({syncSchedule.todays_windows.filter((w) => w.status === 'failed').length} failed)
                      </span>
                    )}
                    {syncSchedule.todays_windows.some((w) => w.status === 'missed') && (
                      <span className="text-red-500 ml-2">
                        ({syncSchedule.todays_windows.filter((w) => w.status === 'missed').length} missed)
                      </span>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Job groups */}
            <div className="border border-border rounded-lg divide-y divide-border">
              {groupedJobs.map((group) => (
                <div key={group.label}>
                  <div className="px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {group.icon}
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{group.label}</span>
                          <StatusBadge status={group.lastRunStatus} />
                        </div>
                        {group.lastRunSummary && (
                          <div className="text-xs text-muted-foreground mt-0.5">
                            {group.lastRunSummary}
                          </div>
                        )}
                        {group.scheduleDescription && (
                          <div className="text-[11px] text-muted-foreground/70 mt-0.5">
                            {group.scheduleDescription}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-right text-sm text-muted-foreground">
                        {group.lastRunAt ? (
                          <>
                            {formatDistanceToNow(new Date(group.lastRunAt), { addSuffix: true })}
                            {group.itemsProcessed > 0 && (
                              <span className="text-xs ml-1">
                                ({group.itemsProcessed} items)
                              </span>
                            )}
                          </>
                        ) : (
                          <span className="text-xs">Never run</span>
                        )}
                      </div>
                      {group.subJobs.length > 0 && (
                        <button
                          onClick={() => setExpandedMemoryDetail((prev) => !prev)}
                          className="text-muted-foreground hover:text-foreground"
                        >
                          {expandedMemoryDetail
                            ? <ChevronDown className="w-4 h-4" />
                            : <ChevronRight className="w-4 h-4" />
                          }
                        </button>
                      )}
                    </div>
                  </div>

                  {group.subJobs.length > 0 && expandedMemoryDetail && (
                    <div className="border-t border-border bg-muted/30">
                      {group.subJobs.map((job) => (
                        <div
                          key={job.job_type}
                          className="px-4 py-2 pl-12 flex items-center justify-between text-sm border-b border-border/50 last:border-b-0"
                        >
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground">{job.job_type}</span>
                              <StatusBadge status={job.last_run_status} />
                            </div>
                            {job.schedule_description && (
                              <div className="text-[11px] text-muted-foreground/70 mt-0.5">
                                {job.schedule_description}
                              </div>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {job.last_run_at
                              ? formatDistanceToNow(new Date(job.last_run_at), { addSuffix: true })
                              : 'Never run'
                            }
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* Link to Activity */}
          <div className="pt-4 border-t border-border">
            <button
              onClick={() => router.push('/activity')}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
            >
              <Activity className="w-4 h-4" />
              View full activity history
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
