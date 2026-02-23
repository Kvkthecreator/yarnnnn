'use client';

/**
 * ADR-072/073: System Page — Operations Status
 *
 * Provides operational visibility into background orchestration:
 * - Platform sync status with per-resource detail (from sync_registry)
 * - Content accumulation counts (from platform_content)
 * - Background job status (from activity_log)
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  RefreshCw,
  Zap,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Slack,
  Mail,
  FileCode,
  Calendar,
  ArrowRight,
  Activity,
  Brain,
  MessageSquare,
  ChevronDown,
  ChevronRight,
  Database,
  Repeat,
  Gauge,
  Play,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow, format } from 'date-fns';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

interface ResourceSyncStatus {
  resource_id: string;
  resource_name: string | null;
  last_synced_at: string | null;
  item_count: number;
  has_cursor: boolean;
  status: 'fresh' | 'recent' | 'stale' | 'never_synced' | 'unknown';
}

interface PlatformContentSummary {
  total_items: number;
  retained_items: number;
  ephemeral_items: number;
  freshest_at: string | null;
}

interface PlatformSyncStatus {
  platform: string;
  connected: boolean;
  last_synced_at: string | null;
  next_sync_at: string | null;
  source_count: number;
  status: 'healthy' | 'stale' | 'pending' | 'disconnected' | 'unknown';
  resources: ResourceSyncStatus[];
  content: PlatformContentSummary | null;
}

interface BackgroundJobStatus {
  job_type: string;
  last_run_at: string | null;
  last_run_status: 'success' | 'failed' | 'never_run' | 'unknown';
  last_run_summary: string | null;
  items_processed: number;
}

// =============================================================================
// Platform Configuration
// =============================================================================

const PLATFORM_CONFIG: Record<string, {
  icon: React.ReactNode;
  label: string;
  color: string;
}> = {
  slack: {
    icon: <Slack className="w-4 h-4" />,
    label: 'Slack',
    color: 'text-purple-500',
  },
  gmail: {
    icon: <Mail className="w-4 h-4" />,
    label: 'Gmail',
    color: 'text-red-500',
  },
  notion: {
    icon: <FileCode className="w-4 h-4" />,
    label: 'Notion',
    color: 'text-gray-700 dark:text-gray-300',
  },
  calendar: {
    icon: <Calendar className="w-4 h-4" />,
    label: 'Calendar',
    color: 'text-blue-500',
  },
};

const SYNC_FREQUENCY_LABELS: Record<string, string> = {
  '2x_daily': '2x daily',
  '4x_daily': '4x daily',
  'hourly': 'Hourly',
};

// =============================================================================
// Status Badge Component
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

// =============================================================================
// Main Component
// =============================================================================

export default function SystemPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [platformSync, setPlatformSync] = useState<PlatformSyncStatus[]>([]);
  const [backgroundJobs, setBackgroundJobs] = useState<BackgroundJobStatus[]>([]);
  const [tier, setTier] = useState('free');
  const [syncFrequency, setSyncFrequency] = useState('2x_daily');
  const [expandedPlatforms, setExpandedPlatforms] = useState<Set<string>>(new Set());

  // Pipeline action state
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineStep, setPipelineStep] = useState<'idle' | 'syncing' | 'processing' | 'complete'>('idle');
  const [pipelineResult, setPipelineResult] = useState<{
    synced_platforms: string[];
    signals_detected: number;
    deliverables_created: number;
    existing_triggered: number;
    message: string;
  } | null>(null);
  const [pipelineError, setPipelineError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const result = await api.system.getStatus();
      setPlatformSync(result.platform_sync);
      setBackgroundJobs(result.background_jobs);
      setTier(result.tier);
      setSyncFrequency(result.sync_frequency);
    } catch (err) {
      console.error('Failed to load system status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const togglePlatform = (platform: string) => {
    setExpandedPlatforms((prev) => {
      const next = new Set(prev);
      if (next.has(platform)) {
        next.delete(platform);
      } else {
        next.add(platform);
      }
      return next;
    });
  };

  const formatNextSync = (isoString: string | null) => {
    if (!isoString) return null;
    try {
      const date = new Date(isoString);
      const now = new Date();
      const diffMs = date.getTime() - now.getTime();

      if (diffMs < 0) return 'Soon';

      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

      if (diffHours === 0) {
        return `in ${diffMins}m`;
      } else if (diffHours < 24) {
        return `in ${diffHours}h ${diffMins}m`;
      } else {
        return format(date, 'EEE h:mm a');
      }
    } catch {
      return null;
    }
  };

  const hasConnectedPlatforms = platformSync.some((p) => p.connected);

  const handleRunPipeline = async () => {
    setPipelineRunning(true);
    setPipelineStep('syncing');
    setPipelineResult(null);
    setPipelineError(null);

    try {
      // Step 1: Sync all connected platforms
      const syncProviders = Array.from(new Set(
        platformSync
          .filter((p) => p.connected)
          .map((p) => (p.platform === 'gmail' || p.platform === 'calendar') ? 'google' : p.platform)
      ));

      const syncResults = await Promise.allSettled(
        syncProviders.map((provider) => api.integrations.syncPlatform(provider))
      );

      const syncedPlatforms = syncProviders.filter(
        (_, i) => syncResults[i].status === 'fulfilled'
      );

      // Step 2: Process signals
      setPipelineStep('processing');
      const signalResult = await api.signalProcessing.trigger('all');

      setPipelineStep('complete');
      setPipelineResult({
        synced_platforms: syncedPlatforms,
        signals_detected: signalResult.signals_detected,
        deliverables_created: signalResult.deliverables_created,
        existing_triggered: signalResult.existing_triggered,
        message: signalResult.message || 'Pipeline complete',
      });

      // Refresh after worker has time to complete (sync is async via RQ)
      await delayedRefresh();
    } catch (err) {
      setPipelineError(err instanceof Error ? err.message : 'Pipeline failed');
      setPipelineStep('idle');
    } finally {
      setPipelineRunning(false);
    }
  };

  const handleSyncOnly = async () => {
    setPipelineRunning(true);
    setPipelineStep('syncing');
    setPipelineResult(null);
    setPipelineError(null);

    try {
      const syncProviders = Array.from(new Set(
        platformSync
          .filter((p) => p.connected)
          .map((p) => (p.platform === 'gmail' || p.platform === 'calendar') ? 'google' : p.platform)
      ));

      await Promise.allSettled(
        syncProviders.map((provider) => api.integrations.syncPlatform(provider))
      );

      setPipelineStep('complete');
      setPipelineResult({
        synced_platforms: syncProviders,
        signals_detected: 0,
        deliverables_created: 0,
        existing_triggered: 0,
        message: `Synced ${syncProviders.length} platform(s)`,
      });

      await delayedRefresh();
    } catch (err) {
      setPipelineError(err instanceof Error ? err.message : 'Sync failed');
      setPipelineStep('idle');
    } finally {
      setPipelineRunning(false);
    }
  };

  const handleSignalsOnly = async () => {
    setPipelineRunning(true);
    setPipelineStep('processing');
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

      // Signal processing is synchronous — refresh immediately then again after delay
      await loadData();
      setTimeout(() => loadData(), 5000);
    } catch (err) {
      setPipelineError(err instanceof Error ? err.message : 'Signal processing failed');
      setPipelineStep('idle');
    } finally {
      setPipelineRunning(false);
    }
  };

  // Sync triggers are async (RQ worker) — wait before refreshing, then poll once more
  const delayedRefresh = async () => {
    await new Promise((r) => setTimeout(r, 5000));
    await loadData();
    setTimeout(() => loadData(), 10000);
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">System</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Platform syncs and background processing
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
            {/* Platform Sync Status */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Platform Sync</h2>
                <span className="text-sm text-muted-foreground">
                  {SYNC_FREQUENCY_LABELS[syncFrequency] || syncFrequency} ({tier} tier)
                </span>
              </div>

              <div className="border border-border rounded-lg divide-y divide-border">
                {platformSync.map((platform) => {
                  const config = PLATFORM_CONFIG[platform.platform] || {
                    icon: <RefreshCw className="w-4 h-4" />,
                    label: platform.platform,
                    color: 'text-gray-500',
                  };

                  const isExpanded = expandedPlatforms.has(platform.platform);
                  const hasResources = platform.connected && platform.resources.length > 0;
                  const contentTotal = platform.content?.total_items ?? 0;

                  return (
                    <div key={platform.platform}>
                      {/* Platform Header Row */}
                      <div
                        className={cn(
                          "px-4 py-3 flex items-center justify-between",
                          hasResources && "cursor-pointer hover:bg-muted/50"
                        )}
                        onClick={() => hasResources && togglePlatform(platform.platform)}
                      >
                        <div className="flex items-center gap-3">
                          {hasResources ? (
                            isExpanded
                              ? <ChevronDown className="w-4 h-4 text-muted-foreground" />
                              : <ChevronRight className="w-4 h-4 text-muted-foreground" />
                          ) : (
                            <span className={config.color}>{config.icon}</span>
                          )}
                          <div>
                            <div className="flex items-center gap-2">
                              {hasResources && <span className={config.color}>{config.icon}</span>}
                              <span className="font-medium">{config.label}</span>
                              <StatusBadge status={platform.status} />
                            </div>
                            {platform.connected && (
                              <div className="text-xs text-muted-foreground mt-0.5">
                                {platform.source_count} source{platform.source_count !== 1 ? 's' : ''} selected
                                {contentTotal > 0 && (
                                  <> · {contentTotal} item{contentTotal !== 1 ? 's' : ''} stored</>
                                )}
                                {platform.last_synced_at && (
                                  <> · Last synced {formatDistanceToNow(new Date(platform.last_synced_at), { addSuffix: true })}</>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="text-right">
                          {platform.connected && platform.next_sync_at && (
                            <span className="text-sm text-muted-foreground">
                              Next {formatNextSync(platform.next_sync_at)}
                            </span>
                          )}
                          {!platform.connected && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                router.push(`/context/${platform.platform}`);
                              }}
                              className="text-sm text-primary hover:underline"
                            >
                              Connect
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Expandable Resource Detail */}
                      {isExpanded && hasResources && (
                        <div className="border-t border-border bg-muted/30">
                          {platform.resources.map((resource) => (
                            <div
                              key={resource.resource_id}
                              className="px-4 py-2 pl-12 flex items-center justify-between text-sm border-b border-border/50 last:border-b-0"
                            >
                              <div className="flex items-center gap-2 min-w-0">
                                <span className="truncate text-muted-foreground">
                                  {resource.resource_name || resource.resource_id}
                                </span>
                                <StatusBadge status={resource.status} />
                                {resource.has_cursor && (
                                  <span
                                    className="inline-flex items-center gap-0.5 text-xs text-muted-foreground"
                                    title="Incremental sync active"
                                  >
                                    <Repeat className="w-3 h-3" />
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
                                {resource.item_count > 0 && (
                                  <span>{resource.item_count} items</span>
                                )}
                                {resource.last_synced_at && (
                                  <span>
                                    {formatDistanceToNow(new Date(resource.last_synced_at), { addSuffix: true })}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                          {/* Content summary */}
                          {platform.content && platform.content.total_items > 0 && (
                            <div className="px-4 py-2 pl-12 text-xs text-muted-foreground flex items-center gap-1.5">
                              <Database className="w-3 h-3" />
                              {platform.content.total_items} items stored
                              {platform.content.retained_items > 0 && (
                                <> ({platform.content.retained_items} retained, {platform.content.ephemeral_items} ephemeral)</>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Pipeline Actions */}
            {hasConnectedPlatforms && (
              <section>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">Pipeline Actions</h2>
                </div>

                <div className="border border-border rounded-lg p-4 space-y-4">
                  {/* Action buttons */}
                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleRunPipeline}
                      disabled={pipelineRunning}
                      className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {pipelineRunning ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Play className="w-4 h-4" />
                      )}
                      Run Pipeline
                    </button>
                    <button
                      onClick={handleSyncOnly}
                      disabled={pipelineRunning}
                      className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground border border-border rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      Sync Only
                    </button>
                    <button
                      onClick={handleSignalsOnly}
                      disabled={pipelineRunning}
                      className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground border border-border rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Zap className="w-3.5 h-3.5" />
                      Signals Only
                    </button>
                  </div>

                  {/* Step indicator */}
                  {pipelineRunning && (
                    <div className="flex items-center gap-2 text-sm">
                      <Loader2 className="w-4 h-4 animate-spin text-primary" />
                      <span className="text-muted-foreground">
                        {pipelineStep === 'syncing' && 'Syncing platforms...'}
                        {pipelineStep === 'processing' && 'Processing signals...'}
                      </span>
                    </div>
                  )}

                  {/* Result */}
                  {pipelineResult && !pipelineRunning && (() => {
                    const hasActions = pipelineResult.deliverables_created > 0 || pipelineResult.existing_triggered > 0;
                    const hasSignals = pipelineResult.signals_detected > 0;
                    // Green: actions taken. Yellow: ran but no signals. Blue: synced only.
                    const variant = hasActions ? 'green' : hasSignals ? 'green' : 'yellow';
                    const colors = {
                      green: { bg: 'bg-green-50 dark:bg-green-900/20', border: 'border-green-200 dark:border-green-800', title: 'text-green-800 dark:text-green-200', body: 'text-green-700 dark:text-green-300', meta: 'text-green-600 dark:text-green-400', dismiss: 'text-green-600 dark:text-green-400' },
                      yellow: { bg: 'bg-yellow-50 dark:bg-yellow-900/20', border: 'border-yellow-200 dark:border-yellow-800', title: 'text-yellow-800 dark:text-yellow-200', body: 'text-yellow-700 dark:text-yellow-300', meta: 'text-yellow-600 dark:text-yellow-400', dismiss: 'text-yellow-600 dark:text-yellow-400' },
                    }[variant];
                    const label = hasActions ? 'Pipeline Complete — Actions Taken' : hasSignals ? 'Pipeline Complete' : 'Pipeline Ran — No Signals Found';
                    const Icon = hasActions ? CheckCircle2 : AlertTriangle;

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
                    Run Pipeline syncs all connected platforms then processes signals. Signal processing has a 5-minute cooldown.
                  </p>
                </div>
              </section>
            )}

            {/* Background Jobs */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Background Processing</h2>
              </div>

              <div className="border border-border rounded-lg divide-y divide-border">
                {backgroundJobs.map((job) => {
                  const iconMap: Record<string, React.ReactNode> = {
                    'Platform Sync': <RefreshCw className="w-4 h-4 text-green-500" />,
                    'Signal Processing': <Zap className="w-4 h-4 text-amber-500" />,
                    'Memory Extraction': <Brain className="w-4 h-4 text-purple-500" />,
                    'Deliverable Scheduler': <Gauge className="w-4 h-4 text-indigo-500" />,
                    'Scheduler Heartbeat': <Activity className="w-4 h-4 text-gray-500" />,
                    'Conversation Analyst': <MessageSquare className="w-4 h-4 text-blue-500" />,
                  };

                  return (
                    <div
                      key={job.job_type}
                      className="px-4 py-3 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3">
                        {iconMap[job.job_type] || <Activity className="w-4 h-4 text-gray-500" />}
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{job.job_type}</span>
                            <StatusBadge status={job.last_run_status} />
                          </div>
                          {job.last_run_summary && (
                            <div className="text-xs text-muted-foreground mt-0.5">
                              {job.last_run_summary}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="text-right text-sm text-muted-foreground">
                        {job.last_run_at ? (
                          <>
                            {formatDistanceToNow(new Date(job.last_run_at), { addSuffix: true })}
                            {job.items_processed > 0 && (
                              <span className="text-xs ml-1">
                                ({job.items_processed} items)
                              </span>
                            )}
                          </>
                        ) : (
                          <span className="text-xs">Never run</span>
                        )}
                      </div>
                    </div>
                  );
                })}
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
