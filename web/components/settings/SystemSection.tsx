'use client';

/**
 * System section for Settings page.
 *
 * Shows background job status: Task Execution + Scheduler Heartbeat.
 *
 * ADR-141/153/156: Platform sync cron, memory extraction, session summaries,
 * Composer heartbeat, and content cleanup are all deleted. The scheduler now
 * only does task execution, workspace cleanup, and lifecycle hygiene.
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
  HeartPulse,
  Cpu,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';

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

// =============================================================================
// Sub-Components
// =============================================================================

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
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

const BACKGROUND_JOBS: Array<{
  label: string;
  icon: React.ReactNode;
  type: string;
}> = [
  {
    label: 'Task Execution',
    icon: <HeartPulse className="w-4 h-4 text-cyan-500" />,
    type: 'Task Execution',
  },
  {
    label: 'Scheduler Heartbeat',
    icon: <Cpu className="w-4 h-4 text-gray-400" />,
    type: 'Scheduler Heartbeat',
  },
];

// =============================================================================
// Main Exported Component
// =============================================================================

export function SystemSection() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [backgroundJobs, setBackgroundJobs] = useState<BackgroundJobStatus[]>([]);

  const loadData = async () => {
    setLoading(true);
    try {
      const result = await api.system.getStatus();
      setBackgroundJobs(result.background_jobs);
    } catch (err) {
      console.error('Failed to load system status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const jobDisplays = BACKGROUND_JOBS.map((def) => {
    const job = backgroundJobs.find((j) => j.job_type === def.type);
    return {
      ...def,
      lastRunAt: job?.last_run_at ?? null,
      lastRunStatus: job?.last_run_status ?? 'never_run',
      lastRunSummary: job?.last_run_summary ?? null,
      itemsProcessed: job?.items_processed ?? 0,
      scheduleDescription: job?.schedule_description ?? null,
    };
  });

  return (
    <div className="space-y-6">
      {/* Header with refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">System</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Background processing and scheduler status.
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
          {/* Background Activity */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold">Background Activity</h3>
            </div>

            {/* Job rows */}
            <div className="border border-border rounded-lg divide-y divide-border">
              {jobDisplays.map((job) => (
                <div key={job.label} className="px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {job.icon}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{job.label}</span>
                        <StatusBadge status={job.lastRunStatus} />
                      </div>
                      {job.lastRunSummary && (
                        <div className="text-xs text-muted-foreground mt-0.5">
                          {job.lastRunSummary}
                        </div>
                      )}
                      {job.scheduleDescription && (
                        <div className="text-[11px] text-muted-foreground/70 mt-0.5">
                          {job.scheduleDescription}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="text-right text-sm text-muted-foreground">
                    {job.lastRunAt ? (
                      <>
                        {formatDistanceToNow(new Date(job.lastRunAt), { addSuffix: true })}
                        {job.itemsProcessed > 0 && (
                          <span className="text-xs ml-1">
                            ({job.itemsProcessed} items)
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="text-xs">Never run</span>
                    )}
                  </div>
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
