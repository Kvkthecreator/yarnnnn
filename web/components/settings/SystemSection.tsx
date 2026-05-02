'use client';

/**
 * System section for Settings page.
 *
 * Shows scheduler heartbeat status only. All other back-office work runs as
 * recurrences visible on /work (ADR-231, ADR-206). Workspace Cleanup and
 * Agent Hygiene removed — neither had a creation trigger and no ephemeral
 * files exist in prod (audited 2026-05-02).
 */

import { useState, useEffect } from 'react';
import {
  Loader2,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
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

// =============================================================================
// Main Exported Component
// =============================================================================

export function SystemSection() {
  const [loading, setLoading] = useState(true);
  const [heartbeat, setHeartbeat] = useState<BackgroundJobStatus | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const result = await api.system.getStatus();
      const hb = result.background_jobs.find((j) => j.job_type === 'Scheduler Heartbeat') ?? null;
      setHeartbeat(hb);
    } catch (err) {
      console.error('Failed to load system status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header with refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">System</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Scheduler status. Back-office recurrences are visible on{' '}
            <a href="/work" className="underline underline-offset-2 hover:text-foreground">/work</a>.
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
        <div className="border border-border rounded-lg">
          <div className="px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Cpu className="w-4 h-4 text-gray-400" />
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">Scheduler Heartbeat</span>
                  <StatusBadge status={heartbeat?.last_run_status ?? 'never_run'} />
                </div>
                {heartbeat?.last_run_summary && (
                  <div className="text-xs text-muted-foreground mt-0.5">
                    {heartbeat.last_run_summary}
                  </div>
                )}
                <div className="text-[11px] text-muted-foreground/70 mt-0.5">Hourly</div>
              </div>
            </div>
            <div className="text-right text-sm text-muted-foreground">
              {heartbeat?.last_run_at ? (
                formatDistanceToNow(new Date(heartbeat.last_run_at), { addSuffix: true })
              ) : (
                <span className="text-xs">Never run</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
