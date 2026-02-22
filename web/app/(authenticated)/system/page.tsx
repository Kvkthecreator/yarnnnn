'use client';

/**
 * ADR-072: System Page — Operations Status
 *
 * Provides operational visibility into background orchestration:
 * - Platform sync status (per-platform last/next sync)
 * - Background job status (signal processing, memory extraction, conversation analyst)
 *
 * This is distinct from Activity (audit trail) - System shows operational state,
 * Activity shows historical events.
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
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow, format } from 'date-fns';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

interface PlatformSyncStatus {
  platform: string;
  connected: boolean;
  last_synced_at: string | null;
  next_sync_at: string | null;
  source_count: number;
  status: 'healthy' | 'stale' | 'pending' | 'disconnected' | 'unknown';
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

                  return (
                    <div
                      key={platform.platform}
                      className="px-4 py-3 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3">
                        <span className={config.color}>{config.icon}</span>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{config.label}</span>
                            <StatusBadge status={platform.status} />
                          </div>
                          {platform.connected && (
                            <div className="text-xs text-muted-foreground mt-0.5">
                              {platform.source_count} source{platform.source_count !== 1 ? 's' : ''} selected
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
                            onClick={() => router.push(`/context/${platform.platform}`)}
                            className="text-sm text-primary hover:underline"
                          >
                            Connect
                          </button>
                        )}
                      </div>
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
                    'Signal Processing': <Zap className="w-4 h-4 text-amber-500" />,
                    'Memory Extraction': <Brain className="w-4 h-4 text-purple-500" />,
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
