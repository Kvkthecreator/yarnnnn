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
