'use client';

/**
 * ADR-072/073: System Page — Operations Status
 *
 * Provides operational visibility into background orchestration:
 * - Integration connectivity state
 * - Manual pipeline execution with poll-based sync completion detection
 * - Background activity summary (from activity_log)
 */

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  RefreshCw,
  Zap,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  Activity,
  Brain,
  ChevronDown,
  ChevronRight,
  Circle,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import { ConnectedIntegrationsSection } from '@/components/settings/ConnectedIntegrationsSection';

// =============================================================================
// Types
// =============================================================================

interface PlatformSyncStatus {
  platform: string;
  connected: boolean;
  last_synced_at: string | null;
}

interface BackgroundJobStatus {
  job_type: string;
  last_run_at: string | null;
  last_run_status: 'success' | 'failed' | 'never_run' | 'unknown';
  last_run_summary: string | null;
  items_processed: number;
}

type PipelineStep =
  | 'idle'
  | 'triggering'
  | 'waiting_for_sync'
  | 'processing_signals'
  | 'complete'
  | 'complete_with_warning';

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

function StepItem({ label, status }: { label: string; status: 'pending' | 'active' | 'done' | 'warning' }) {
  return (
    <div className="flex items-center gap-2.5 text-sm">
      {status === 'active' && <Loader2 className="w-4 h-4 animate-spin text-primary shrink-0" />}
      {status === 'done' && <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />}
      {status === 'warning' && <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />}
      {status === 'pending' && <Circle className="w-4 h-4 text-muted-foreground/40 shrink-0" />}
      <span className={cn(
        status === 'active' && 'text-foreground',
        status === 'done' && 'text-green-700 dark:text-green-400',
        status === 'warning' && 'text-amber-700 dark:text-amber-400',
        status === 'pending' && 'text-muted-foreground/50',
      )}>
        {label}
      </span>
    </div>
  );
}

// Background job grouping: maps backend job_type labels to display groups
const BACKGROUND_JOB_GROUPS = [
  {
    label: 'Platform Sync',
    icon: <RefreshCw className="w-4 h-4 text-green-500" />,
    types: ['Platform Sync'],
  },
  {
    label: 'Signal Processing',
    icon: <Zap className="w-4 h-4 text-amber-500" />,
    types: ['Signal Processing'],
  },
  {
    label: 'Memory & Analysis',
    icon: <Brain className="w-4 h-4 text-purple-500" />,
    types: [
      'Memory Extraction',
      'Session Summaries',
      'Pattern Detection',
      'Conversation Analysis',
      'Deliverable Generation',
      'Content Cleanup',
    ],
  },
];

// =============================================================================
// Main Component
// =============================================================================

export default function SystemPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [platformSync, setPlatformSync] = useState<PlatformSyncStatus[]>([]);
  const [backgroundJobs, setBackgroundJobs] = useState<BackgroundJobStatus[]>([]);
  const [expandedMemoryDetail, setExpandedMemoryDetail] = useState(false);

  // Pipeline action state
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineStep, setPipelineStep] = useState<PipelineStep>('idle');
  const [pipelineResult, setPipelineResult] = useState<{
    synced_platforms: string[];
    signals_detected: number;
    deliverables_created: number;
    existing_triggered: number;
    message: string;
    syncTimedOut?: boolean;
  } | null>(null);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const abortRef = useRef(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const result = await api.system.getStatus();
      setPlatformSync(result.platform_sync);
      setBackgroundJobs(result.background_jobs);
    } catch (err) {
      console.error('Failed to load system status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    return () => { abortRef.current = true; };
  }, []);

  const hasConnectedPlatforms = platformSync.some((p) => p.connected);

  // ---------------------------------------------------------------------------
  // Pipeline: Poll for sync completion
  // ---------------------------------------------------------------------------

  const waitForSyncCompletion = async (
    preSnapshot: Record<string, string | null>,
    timeoutMs: number = 90000,
  ): Promise<{ completed: boolean; timedOut: boolean }> => {
    const startTime = Date.now();
    const POLL_INTERVAL = 3000;

    while (Date.now() - startTime < timeoutMs) {
      if (abortRef.current) return { completed: false, timedOut: false };
      await new Promise((r) => setTimeout(r, POLL_INTERVAL));

      try {
        const { timestamps } = await api.system.getSyncTimestamps();

        // Check if all connected platforms have a newer timestamp
        const connectedPlatforms = platformSync
          .filter((p) => p.connected)
          .map((p) => p.platform);

        const allSynced = connectedPlatforms.every((platform) => {
          const preTime = preSnapshot[platform];
          const newTime = timestamps[platform];

          if (!preTime && !newTime) return false; // never synced and still nothing
          if (!preTime && newTime) return true;    // new sync appeared
          if (!newTime || !preTime) return false;   // still no sync entry
          return new Date(newTime) > new Date(preTime);
        });

        if (allSynced) {
          return { completed: true, timedOut: false };
        }
      } catch {
        // Polling failure — continue trying
      }
    }

    return { completed: false, timedOut: true };
  };

  // ---------------------------------------------------------------------------
  // Pipeline: Refresh Data (full pipeline with proper sequencing)
  // ---------------------------------------------------------------------------

  const handleRefreshData = async () => {
    setPipelineRunning(true);
    setPipelineStep('triggering');
    setPipelineResult(null);
    setPipelineError(null);
    abortRef.current = false;

    try {
      // Snapshot current sync timestamps for comparison
      const preSnapshot: Record<string, string | null> = {};
      platformSync.filter((p) => p.connected).forEach((p) => {
        preSnapshot[p.platform] = p.last_synced_at;
      });

      // Step 1: Trigger sync for all connected platforms
      const syncProviders = Array.from(new Set(
        platformSync
          .filter((p) => p.connected)
          .map((p) => p.platform)
      ));

      await Promise.allSettled(
        syncProviders.map((provider) => api.integrations.syncPlatform(provider))
      );

      // Step 2: Poll for sync completion
      setPipelineStep('waiting_for_sync');
      const syncResult = await waitForSyncCompletion(preSnapshot);

      if (abortRef.current) return;

      // Step 3: Process signals
      setPipelineStep('processing_signals');
      let signalResult = { signals_detected: 0, deliverables_created: 0, existing_triggered: 0, message: '' as string };

      try {
        const result = await api.signalProcessing.trigger('all');
        signalResult = { ...result, message: result.message || '' };
      } catch (err) {
        // Signal processing may fail (free tier, rate limit, etc.)
        // Still show sync success
        const errMsg = err instanceof Error ? err.message : '';
        if (errMsg.includes('tier') || errMsg.includes('403')) {
          signalResult.message = 'Signal processing requires Starter plan or above';
        } else if (errMsg.includes('rate') || errMsg.includes('429')) {
          signalResult.message = 'Signal processing is on cooldown (5 min between runs)';
        } else {
          signalResult.message = 'Signal processing unavailable';
        }
      }

      const finalStep = syncResult.timedOut ? 'complete_with_warning' : 'complete';
      setPipelineStep(finalStep);
      setPipelineResult({
        synced_platforms: syncProviders,
        signals_detected: signalResult.signals_detected,
        deliverables_created: signalResult.deliverables_created,
        existing_triggered: signalResult.existing_triggered,
        message: signalResult.message || 'Pipeline complete',
        syncTimedOut: syncResult.timedOut,
      });

      // Refresh page data
      await loadData();
    } catch (err) {
      setPipelineError(err instanceof Error ? err.message : 'Pipeline failed');
      setPipelineStep('idle');
    } finally {
      setPipelineRunning(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Pipeline: Process signals only (from existing data)
  // ---------------------------------------------------------------------------

  const handleSignalsOnly = async () => {
    setPipelineRunning(true);
    setPipelineStep('processing_signals');
    setPipelineResult(null);
    setPipelineError(null);

    try {
      const signalResult = await api.signalProcessing.trigger('all');

      setPipelineStep('complete');
      setPipelineResult({
        synced_platforms: [],
        signals_detected: signalResult.signals_detected,
        deliverables_created: signalResult.deliverables_created,
        existing_triggered: signalResult.existing_triggered,
        message: signalResult.message || 'Signal processing complete',
      });

      await loadData();
    } catch (err) {
      setPipelineError(err instanceof Error ? err.message : 'Signal processing failed');
      setPipelineStep('idle');
    } finally {
      setPipelineRunning(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Background jobs: group into display rows
  // ---------------------------------------------------------------------------

  const groupedJobs = BACKGROUND_JOB_GROUPS.map((group) => {
    const matchingJobs = backgroundJobs.filter((j) => group.types.includes(j.job_type));

    // For single-type groups, use the job directly
    if (group.types.length === 1) {
      const job = matchingJobs[0];
      return {
        ...group,
        lastRunAt: job?.last_run_at ?? null,
        lastRunStatus: job?.last_run_status ?? 'never_run',
        lastRunSummary: job?.last_run_summary ?? null,
        itemsProcessed: job?.items_processed ?? 0,
        subJobs: [],
      };
    }

    // For multi-type groups, aggregate: most recent run, worst status
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
      subJobs: matchingJobs,
    };
  });

  // ---------------------------------------------------------------------------
  // Step indicator helpers
  // ---------------------------------------------------------------------------

  const getStepStatus = (step: 'triggering' | 'waiting_for_sync' | 'processing_signals') => {
    const order: PipelineStep[] = ['triggering', 'waiting_for_sync', 'processing_signals', 'complete', 'complete_with_warning'];
    const currentIdx = order.indexOf(pipelineStep);
    const stepIdx = order.indexOf(step);

    if (pipelineStep === 'complete' || pipelineStep === 'complete_with_warning') {
      if (step === 'waiting_for_sync' && pipelineStep === 'complete_with_warning') return 'warning';
      return 'done';
    }
    if (currentIdx === stepIdx) return 'active';
    if (currentIdx > stepIdx) return 'done';
    return 'pending';
  };

  // =============================================================================
  // Render
  // =============================================================================

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">System</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Connected platforms, sync status, and background processing
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
            {/* ── Section 1: Integrations ─────────────────────────────────── */}
            <ConnectedIntegrationsSection
              title="Connected Platforms"
              description="Connect platforms to sync context. Manage sources in each platform's context page."
            />

            {/* ── Section 2: Actions ───────────────────────────────────────── */}
            {hasConnectedPlatforms && (
              <section>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">Actions</h2>
                </div>

                <div className="border border-border rounded-lg p-4 space-y-4">
                  {/* Primary action + secondary link */}
                  <div className="flex items-center gap-4">
                    <button
                      onClick={handleRefreshData}
                      disabled={pipelineRunning}
                      className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {pipelineRunning ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <RefreshCw className="w-4 h-4" />
                      )}
                      Refresh Data
                    </button>
                    <button
                      onClick={handleSignalsOnly}
                      disabled={pipelineRunning}
                      className="text-sm text-muted-foreground hover:text-foreground disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      or process signals from existing data
                    </button>
                  </div>

                  {/* Step indicator (shown during pipeline execution) */}
                  {pipelineRunning && pipelineStep !== 'idle' && (
                    <div className="space-y-1.5 py-1">
                      {pipelineStep === 'processing_signals' && !pipelineResult ? (
                        // Signals-only mode: single step
                        <StepItem label="Scanning for signals..." status="active" />
                      ) : (
                        // Full pipeline: 3 steps
                        <>
                          <StepItem
                            label="Syncing platforms..."
                            status={getStepStatus('triggering')}
                          />
                          <StepItem
                            label="Waiting for sync to complete..."
                            status={getStepStatus('waiting_for_sync')}
                          />
                          <StepItem
                            label="Scanning for signals..."
                            status={getStepStatus('processing_signals')}
                          />
                        </>
                      )}
                    </div>
                  )}

                  {/* Result banner */}
                  {pipelineResult && !pipelineRunning && (() => {
                    const hasActions = pipelineResult.deliverables_created > 0 || pipelineResult.existing_triggered > 0;
                    const hasSignals = pipelineResult.signals_detected > 0;
                    const syncTimedOut = pipelineResult.syncTimedOut;

                    const variant = syncTimedOut ? 'amber' : hasActions ? 'green' : hasSignals ? 'green' : 'yellow';
                    const colors = {
                      green: { bg: 'bg-green-50 dark:bg-green-900/20', border: 'border-green-200 dark:border-green-800', title: 'text-green-800 dark:text-green-200', body: 'text-green-700 dark:text-green-300', meta: 'text-green-600 dark:text-green-400', dismiss: 'text-green-600 dark:text-green-400' },
                      yellow: { bg: 'bg-yellow-50 dark:bg-yellow-900/20', border: 'border-yellow-200 dark:border-yellow-800', title: 'text-yellow-800 dark:text-yellow-200', body: 'text-yellow-700 dark:text-yellow-300', meta: 'text-yellow-600 dark:text-yellow-400', dismiss: 'text-yellow-600 dark:text-yellow-400' },
                      amber: { bg: 'bg-amber-50 dark:bg-amber-900/20', border: 'border-amber-200 dark:border-amber-800', title: 'text-amber-800 dark:text-amber-200', body: 'text-amber-700 dark:text-amber-300', meta: 'text-amber-600 dark:text-amber-400', dismiss: 'text-amber-600 dark:text-amber-400' },
                    }[variant];

                    const label = syncTimedOut
                      ? 'Sync is still running in the background'
                      : hasActions
                        ? 'Pipeline Complete — Actions Taken'
                        : hasSignals
                          ? 'Pipeline Complete'
                          : 'Pipeline Complete — No Signals Found';
                    const Icon = syncTimedOut ? AlertTriangle : hasActions ? CheckCircle2 : hasSignals ? CheckCircle2 : AlertTriangle;

                    return (
                      <div className={`rounded-md ${colors.bg} border ${colors.border} p-3 text-sm`}>
                        <div className="flex items-start justify-between">
                          <div className="space-y-1">
                            <div className={`flex items-center gap-1.5 ${colors.title} font-medium`}>
                              <Icon className="w-4 h-4" />
                              {label}
                            </div>
                            <p className={colors.body}>{pipelineResult.message}</p>
                            <div className={`flex gap-4 text-xs ${colors.meta}`}>
                              {pipelineResult.synced_platforms.length > 0 && (
                                <span>{pipelineResult.synced_platforms.length} platform(s) synced</span>
                              )}
                              {pipelineResult.signals_detected > 0 && (
                                <span>{pipelineResult.signals_detected} signal(s) scanned</span>
                              )}
                              {pipelineResult.deliverables_created > 0 && (
                                <span>{pipelineResult.deliverables_created} deliverable(s) created</span>
                              )}
                              {pipelineResult.existing_triggered > 0 && (
                                <span>{pipelineResult.existing_triggered} existing triggered</span>
                              )}
                            </div>
                          </div>
                          <button
                            onClick={() => setPipelineResult(null)}
                            className={`p-1 hover:opacity-70 ${colors.dismiss}`}
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    );
                  })()}

                  {/* Error */}
                  {pipelineError && !pipelineRunning && (
                    <div className="rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-1.5 text-red-800 dark:text-red-200">
                          <XCircle className="w-4 h-4" />
                          <span>{pipelineError}</span>
                        </div>
                        <button
                          onClick={() => setPipelineError(null)}
                          className="p-1 hover:opacity-70 text-red-600 dark:text-red-400"
                        >
                          <XCircle className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )}

                  <p className="text-xs text-muted-foreground">
                    Fetches latest data from all connected platforms, then scans for actionable signals. Signal processing has a 5-minute cooldown.
                  </p>
                </div>
              </section>
            )}

            {/* ── Section 3: Background Activity ──────────────────────────── */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Background Activity</h2>
              </div>

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
                        {/* Expand toggle for Memory & Analysis */}
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

                    {/* Expanded sub-jobs for Memory & Analysis */}
                    {group.subJobs.length > 0 && expandedMemoryDetail && (
                      <div className="border-t border-border bg-muted/30">
                        {group.subJobs.map((job) => (
                          <div
                            key={job.job_type}
                            className="px-4 py-2 pl-12 flex items-center justify-between text-sm border-b border-border/50 last:border-b-0"
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground">{job.job_type}</span>
                              <StatusBadge status={job.last_run_status} />
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
    </div>
  );
}
