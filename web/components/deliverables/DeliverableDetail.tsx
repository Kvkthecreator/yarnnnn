'use client';

/**
 * ADR-018: Deliverable Detail View
 *
 * Full view of a deliverable with version history, settings, and actions.
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Calendar,
  User,
  Play,
  Pause,
  Settings,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronRight,
  TrendingDown,
  FileText,
  RefreshCw,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { Deliverable, DeliverableVersion, VersionStatus } from '@/types';

interface DeliverableDetailProps {
  deliverableId: string;
  onBack: () => void;
  onReview: (versionId: string) => void;
}

const VERSION_STATUS_CONFIG: Record<VersionStatus, { icon: React.ReactNode; label: string; color: string }> = {
  generating: {
    icon: <Loader2 className="w-4 h-4 animate-spin" />,
    label: 'Generating',
    color: 'text-blue-600 bg-blue-50 dark:bg-blue-900/30',
  },
  staged: {
    icon: <AlertCircle className="w-4 h-4" />,
    label: 'Ready for review',
    color: 'text-amber-600 bg-amber-50 dark:bg-amber-900/30',
  },
  reviewing: {
    icon: <Clock className="w-4 h-4" />,
    label: 'In review',
    color: 'text-purple-600 bg-purple-50 dark:bg-purple-900/30',
  },
  approved: {
    icon: <CheckCircle2 className="w-4 h-4" />,
    label: 'Approved',
    color: 'text-green-600 bg-green-50 dark:bg-green-900/30',
  },
  rejected: {
    icon: <AlertCircle className="w-4 h-4" />,
    label: 'Rejected',
    color: 'text-red-600 bg-red-50 dark:bg-red-900/30',
  },
};

export function DeliverableDetail({
  deliverableId,
  onBack,
  onReview,
}: DeliverableDetailProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [versions, setVersions] = useState<DeliverableVersion[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    loadDeliverable();
  }, [deliverableId]);

  const loadDeliverable = async () => {
    setLoading(true);
    try {
      const detail = await api.deliverables.get(deliverableId);
      setDeliverable(detail.deliverable);
      setVersions(detail.versions);
    } catch (err) {
      console.error('Failed to load deliverable:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunNow = async () => {
    if (!deliverable) return;

    setIsRunning(true);
    try {
      await api.deliverables.run(deliverableId);
      // Reload to get the new version
      await loadDeliverable();
    } catch (err) {
      console.error('Failed to run:', err);
    } finally {
      setIsRunning(false);
    }
  };

  const handlePauseResume = async () => {
    if (!deliverable) return;

    const newStatus = deliverable.status === 'paused' ? 'active' : 'paused';
    try {
      const updated = await api.deliverables.update(deliverableId, { status: newStatus });
      setDeliverable(updated);
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatSchedule = (schedule: Deliverable['schedule']) => {
    const { frequency, day, time } = schedule;
    let str = frequency.charAt(0).toUpperCase() + frequency.slice(1);
    if (day) str += ` on ${day}`;
    if (time) str += ` at ${time}`;
    return str;
  };

  // Calculate quality trend from approved versions
  const approvedVersions = versions.filter(v => v.status === 'approved' && v.edit_distance_score !== undefined);
  const avgEditDistance = approvedVersions.length > 0
    ? approvedVersions.reduce((sum, v) => sum + (v.edit_distance_score || 0), 0) / approvedVersions.length
    : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!deliverable) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <p className="text-muted-foreground mb-4">Deliverable not found</p>
        <button onClick={onBack} className="text-sm text-primary hover:underline">
          Go back
        </button>
      </div>
    );
  }

  const isPaused = deliverable.status === 'paused';

  return (
    <div className="h-full overflow-auto">
      <div className="container mx-auto max-w-4xl px-4 py-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-start gap-4">
            <button
              onClick={onBack}
              className="p-2 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted mt-0.5"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-2xl font-semibold">{deliverable.title}</h1>
              {deliverable.description && (
                <p className="text-muted-foreground mt-1">{deliverable.description}</p>
              )}
              <div className="flex items-center gap-4 mt-3 text-sm text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <Calendar className="w-4 h-4" />
                  {formatSchedule(deliverable.schedule)}
                </span>
                {deliverable.recipient_context?.name && (
                  <span className="inline-flex items-center gap-1.5">
                    <User className="w-4 h-4" />
                    {deliverable.recipient_context.name}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRunNow}
              disabled={isRunning || isPaused}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-50"
            >
              {isRunning ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Run now
            </button>
            <button
              onClick={handlePauseResume}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm border border-border rounded-md hover:bg-muted"
            >
              {isPaused ? (
                <>
                  <Play className="w-4 h-4" />
                  Resume
                </>
              ) : (
                <>
                  <Pause className="w-4 h-4" />
                  Pause
                </>
              )}
            </button>
          </div>
        </div>

        {/* Status banner */}
        {isPaused && (
          <div className="mb-6 px-4 py-3 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">
              This deliverable is paused. It won't run on schedule until resumed.
            </p>
          </div>
        )}

        {/* Quality metrics */}
        {avgEditDistance !== null && (
          <div className="mb-6 p-4 border border-border rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Quality Trend</p>
                <p className="text-xs text-muted-foreground">
                  Average edit distance across {approvedVersions.length} approved versions
                </p>
              </div>
              <div className="flex items-center gap-2">
                <TrendingDown className="w-5 h-5 text-green-600" />
                <span className="text-2xl font-semibold">
                  {Math.round((1 - avgEditDistance) * 100)}%
                </span>
                <span className="text-sm text-muted-foreground">match</span>
              </div>
            </div>
            <div className="mt-3 h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full"
                style={{ width: `${(1 - avgEditDistance) * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Version history */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium">Version History</h2>
            <button
              onClick={loadDeliverable}
              className="p-2 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {versions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No versions yet</p>
              <button
                onClick={handleRunNow}
                disabled={isRunning || isPaused}
                className="mt-4 text-sm text-primary hover:underline"
              >
                Generate first version
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {versions.map((version) => {
                const statusConfig = VERSION_STATUS_CONFIG[version.status];
                const canReview = version.status === 'staged' || version.status === 'reviewing';

                return (
                  <div
                    key={version.id}
                    className={cn(
                      "flex items-center justify-between p-4 border border-border rounded-lg",
                      canReview && "hover:border-primary/50 cursor-pointer"
                    )}
                    onClick={() => canReview && onReview(version.id)}
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-muted rounded-full flex items-center justify-center">
                        <span className="text-sm font-medium">v{version.version_number}</span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className={cn(
                            "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                            statusConfig.color
                          )}>
                            {statusConfig.icon}
                            {statusConfig.label}
                          </span>
                          {version.edit_distance_score !== undefined && (
                            <span className="text-xs text-muted-foreground">
                              {Math.round((1 - version.edit_distance_score) * 100)}% match
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          {version.approved_at
                            ? `Approved ${formatDate(version.approved_at)}`
                            : version.staged_at
                            ? `Staged ${formatDate(version.staged_at)}`
                            : `Created ${formatDate(version.created_at)}`}
                        </p>
                      </div>
                    </div>

                    {canReview && (
                      <ChevronRight className="w-5 h-5 text-muted-foreground" />
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
