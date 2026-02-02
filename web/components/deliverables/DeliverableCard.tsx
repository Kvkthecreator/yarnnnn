'use client';

/**
 * ADR-018: Deliverable Card
 *
 * Displays a single deliverable in the dashboard grid.
 * - Shows version count as "X outputs" not "vX"
 * - Status labels: Sent, Ready for review, Generating
 * - Simple schedule display
 */

import { useState } from 'react';
import {
  Calendar,
  User,
  Play,
  Pause,
  MoreVertical,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileText,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Deliverable, VersionStatus } from '@/types';

interface DeliverableCardProps {
  deliverable: Deliverable;
  onView: (id: string) => void;
  onReview: (id: string) => void;
  onPause: (id: string) => void;
  onResume: (id: string) => void;
  onRunNow: (id: string) => void;
}

const STATUS_CONFIG: Record<VersionStatus | 'none', { icon: React.ReactNode; label: string; color: string }> = {
  generating: {
    icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
    label: 'Generating...',
    color: 'text-blue-600 bg-blue-50 dark:bg-blue-900/30'
  },
  staged: {
    icon: <AlertCircle className="w-3.5 h-3.5" />,
    label: 'Ready for review',
    color: 'text-amber-600 bg-amber-50 dark:bg-amber-900/30'
  },
  reviewing: {
    icon: <Clock className="w-3.5 h-3.5" />,
    label: 'In review',
    color: 'text-purple-600 bg-purple-50 dark:bg-purple-900/30'
  },
  approved: {
    icon: <CheckCircle2 className="w-3.5 h-3.5" />,
    label: 'Done',
    color: 'text-green-600 bg-green-50 dark:bg-green-900/30'
  },
  rejected: {
    icon: <AlertCircle className="w-3.5 h-3.5" />,
    label: 'Discarded',
    color: 'text-muted-foreground bg-muted'
  },
  none: {
    icon: <FileText className="w-3.5 h-3.5" />,
    label: 'No outputs yet',
    color: 'text-muted-foreground bg-muted'
  },
};

function formatSchedule(schedule: Deliverable['schedule']): string {
  const { frequency, day, time } = schedule;

  if (frequency === 'daily') {
    return 'Daily';
  }
  if (frequency === 'weekly') {
    const dayStr = day ? day.charAt(0).toUpperCase() + day.slice(1, 3) : 'Mon';
    return `Weekly (${dayStr})`;
  }
  if (frequency === 'biweekly') {
    return 'Biweekly';
  }
  if (frequency === 'monthly') {
    return 'Monthly';
  }
  return frequency;
}

function formatNextRun(nextRunAt: string | undefined): string {
  if (!nextRunAt) return 'Not scheduled';

  const next = new Date(nextRunAt);
  const now = new Date();
  const diffMs = next.getTime() - now.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return 'Overdue';
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Tomorrow';
  if (diffDays < 7) return `In ${diffDays} days`;

  return next.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function DeliverableCard({
  deliverable,
  onView,
  onReview,
  onPause,
  onResume,
  onRunNow,
}: DeliverableCardProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  const versionStatus = deliverable.latest_version_status || 'none';
  const statusConfig = STATUS_CONFIG[versionStatus];
  const isPaused = deliverable.status === 'paused';
  const hasStaged = versionStatus === 'staged';
  const outputCount = deliverable.version_count || 0;

  const handleRunNow = async () => {
    setIsRunning(true);
    try {
      await onRunNow(deliverable.id);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div
      className={cn(
        "bg-background border border-border rounded-lg p-4 hover:border-foreground/20 transition-colors cursor-pointer",
        isPaused && "opacity-60"
      )}
      onClick={() => onView(deliverable.id)}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-sm truncate">{deliverable.title}</h3>
        </div>

        {/* Menu */}
        <div className="relative ml-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowMenu(!showMenu);
            }}
            className="p-1 text-muted-foreground hover:text-foreground rounded"
          >
            <MoreVertical className="w-4 h-4" />
          </button>

          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMenu(false);
                }}
              />
              <div className="absolute right-0 top-full mt-1 bg-background border border-border rounded-md shadow-lg py-1 z-20 min-w-[140px]">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowMenu(false);
                    onView(deliverable.id);
                  }}
                  className="w-full px-3 py-1.5 text-left text-sm hover:bg-muted"
                >
                  View details
                </button>
                {!isPaused && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowMenu(false);
                      handleRunNow();
                    }}
                    className="w-full px-3 py-1.5 text-left text-sm hover:bg-muted"
                  >
                    Run now
                  </button>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowMenu(false);
                    isPaused ? onResume(deliverable.id) : onPause(deliverable.id);
                  }}
                  className="w-full px-3 py-1.5 text-left text-sm hover:bg-muted"
                >
                  {isPaused ? 'Resume' : 'Pause'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Meta info */}
      <div className="flex items-center gap-3 text-xs text-muted-foreground mb-3">
        <span className="inline-flex items-center gap-1">
          <Calendar className="w-3.5 h-3.5" />
          {formatSchedule(deliverable.schedule)}
        </span>
        {deliverable.recipient_context?.name && (
          <span className="inline-flex items-center gap-1">
            <User className="w-3.5 h-3.5" />
            {deliverable.recipient_context.name}
          </span>
        )}
      </div>

      {/* Latest status */}
      <div className="flex items-center justify-between mb-3">
        <div className={cn(
          "inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium",
          statusConfig.color
        )}>
          {statusConfig.icon}
          <span>{statusConfig.label}</span>
        </div>

        {outputCount > 0 && (
          <span className="text-xs text-muted-foreground">
            {outputCount} {outputCount === 1 ? 'output' : 'outputs'}
          </span>
        )}
      </div>

      {/* Next run info */}
      {!isPaused && versionStatus !== 'staged' && (
        <div className="text-xs text-muted-foreground mb-3">
          Next: {formatNextRun(deliverable.next_run_at)}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-2 border-t border-border">
        {hasStaged ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onReview(deliverable.id);
            }}
            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 bg-amber-500 text-white text-xs font-medium rounded-md hover:bg-amber-600 transition-colors"
          >
            Review Draft
          </button>
        ) : (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onView(deliverable.id);
            }}
            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 border border-border text-xs font-medium rounded-md hover:bg-muted transition-colors"
          >
            View
          </button>
        )}

        {!isPaused ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onPause(deliverable.id);
            }}
            className="p-1.5 text-muted-foreground hover:text-foreground border border-border rounded-md hover:bg-muted transition-colors"
            title="Pause"
          >
            <Pause className="w-3.5 h-3.5" />
          </button>
        ) : (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onResume(deliverable.id);
            }}
            className="p-1.5 text-muted-foreground hover:text-foreground border border-border rounded-md hover:bg-muted transition-colors"
            title="Resume"
          >
            <Play className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}
