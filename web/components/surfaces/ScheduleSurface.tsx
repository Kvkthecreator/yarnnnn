'use client';

/**
 * ADR-017: Unified Work Model
 * Schedule Surface - displays scheduled/recurring work
 *
 * Lists all work (one-time and recurring) with pause/resume/delete actions.
 * Work creation happens through chat (TP tools), this surface is for viewing/managing.
 */

import { useEffect, useState, useCallback } from 'react';
import {
  Calendar,
  Clock,
  Loader2,
  Pause,
  Play,
  Trash2,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { useProjectContext } from '@/contexts/ProjectContext';
import { useSurface } from '@/contexts/SurfaceContext';
import { api } from '@/lib/api/client';
import type { SurfaceData } from '@/types/surfaces';
import type { Work } from '@/types';

interface ScheduleSurfaceProps {
  data: SurfaceData | null;
}

// Status configuration for one-time work
const STATUS_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  pending: { icon: <Clock className="w-3 h-3" />, color: 'text-yellow-600 bg-yellow-50', label: 'Pending' },
  running: { icon: <Loader2 className="w-3 h-3 animate-spin" />, color: 'text-blue-600 bg-blue-50', label: 'Running' },
  completed: { icon: <CheckCircle2 className="w-3 h-3" />, color: 'text-green-600 bg-green-50', label: 'Completed' },
  failed: { icon: <XCircle className="w-3 h-3" />, color: 'text-red-600 bg-red-50', label: 'Failed' },
};

// Agent type badge colors
const AGENT_COLORS: Record<string, string> = {
  research: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  content: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  reporting: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
};

export function ScheduleSurface({ data }: ScheduleSurfaceProps) {
  const { activeProject } = useProjectContext();
  const { openSurface } = useSurface();
  const [workItems, setWorkItems] = useState<Work[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const projectId = data?.projectId || activeProject?.id;

  const loadWork = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch both project-specific work AND ambient (user-level) work
      const [projectResult, ambientResult] = await Promise.all([
        // Project work (if project selected)
        projectId
          ? api.work.listAll({
              projectId: projectId,
              activeOnly: false,
              includeCompleted: true,
              limit: 50,
            })
          : Promise.resolve({ work: [], count: 0, success: true, message: '' }),
        // Ambient work (no project) - always fetch
        api.work.listAll({
          activeOnly: false,
          includeCompleted: true,
          limit: 50,
        }),
      ]);

      // Combine and deduplicate (ambient query returns all user work, filter to ambient only)
      const projectWork = projectResult.work || [];
      const allWork = ambientResult.work || [];

      // Ambient work = work with is_ambient=true (no project)
      const ambientWork = allWork.filter((w) => w.is_ambient);

      // Combine: project work + ambient work (no duplicates since they're mutually exclusive)
      const combined = [...projectWork, ...ambientWork];

      // Sort by created_at descending
      combined.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

      setWorkItems(combined);
    } catch (err) {
      console.error('Failed to load work:', err);
      setError('Failed to load work items');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadWork();
  }, [loadWork]);

  const handleToggle = async (workId: string, currentlyActive: boolean) => {
    setActionLoading(workId);
    try {
      await api.work.update(workId, { is_active: !currentlyActive });
      // Refresh the list
      await loadWork();
    } catch (err) {
      console.error('Failed to toggle work:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (workId: string) => {
    if (!confirm('Delete this work and all its outputs?')) return;

    setActionLoading(workId);
    try {
      await api.work.delete(workId);
      // Remove from list locally for immediate feedback
      setWorkItems((prev) => prev.filter((w) => w.id !== workId));
    } catch (err) {
      console.error('Failed to delete work:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleViewOutput = (work: Work) => {
    openSurface('output', { workId: work.id, projectId: work.is_ambient ? undefined : projectId }, 'half');
  };

  const formatNextRun = (dateStr?: string) => {
    if (!dateStr) return 'Not scheduled';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffMs < 0) return 'Overdue';
    if (diffHours < 1) return 'Less than an hour';
    if (diffHours < 24) return `In ${diffHours} hour${diffHours > 1 ? 's' : ''}`;
    if (diffDays === 1) return 'Tomorrow';
    if (diffDays < 7) return `In ${diffDays} days`;
    return date.toLocaleDateString();
  };

  const formatCreatedAt = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-muted-foreground">
        <AlertCircle className="w-8 h-8 mb-2 text-destructive" />
        <p className="text-sm">{error}</p>
        <button
          onClick={loadWork}
          className="mt-2 text-xs text-primary hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  // Separate recurring and one-time work
  const recurringWork = workItems.filter((w) => w.is_recurring);
  const oneTimeWork = workItems.filter((w) => !w.is_recurring);

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-muted-foreground">
          Work
        </h3>
        <button
          onClick={loadWork}
          className="p-1.5 text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-muted"
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {workItems.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-sm font-medium">No work yet</p>
          <p className="text-xs mt-1">
            Ask your assistant to create work for you.
          </p>
          <p className="text-xs mt-2 text-muted-foreground/70">
            Try: "Research competitors daily" or "Write a weekly status report"
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Recurring Work Section */}
          {recurringWork.length > 0 && (
            <section>
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                Recurring ({recurringWork.length})
              </h4>
              <div className="space-y-2">
                {recurringWork.map((work) => (
                  <WorkCard
                    key={work.id}
                    work={work}
                    onToggle={handleToggle}
                    onDelete={handleDelete}
                    onViewOutput={handleViewOutput}
                    formatNextRun={formatNextRun}
                    actionLoading={actionLoading}
                  />
                ))}
              </div>
            </section>
          )}

          {/* One-time Work Section */}
          {oneTimeWork.length > 0 && (
            <section>
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                One-time ({oneTimeWork.length})
              </h4>
              <div className="space-y-2">
                {oneTimeWork.map((work) => (
                  <WorkCard
                    key={work.id}
                    work={work}
                    onToggle={handleToggle}
                    onDelete={handleDelete}
                    onViewOutput={handleViewOutput}
                    formatCreatedAt={formatCreatedAt}
                    actionLoading={actionLoading}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

interface WorkCardProps {
  work: Work;
  onToggle: (workId: string, currentlyActive: boolean) => void;
  onDelete: (workId: string) => void;
  onViewOutput: (work: Work) => void;
  formatNextRun?: (dateStr?: string) => string;
  formatCreatedAt?: (dateStr: string) => string;
  actionLoading: string | null;
}

function WorkCard({
  work,
  onToggle,
  onDelete,
  onViewOutput,
  formatNextRun,
  formatCreatedAt,
  actionLoading,
}: WorkCardProps) {
  const isLoading = actionLoading === work.id;
  const isPaused = work.is_recurring && work.is_active === false;
  const statusConfig = work.status ? STATUS_CONFIG[work.status] : null;

  return (
    <div
      className={`p-3 border rounded-lg transition-colors group cursor-pointer ${
        isPaused
          ? 'border-border/50 bg-muted/30'
          : 'border-border hover:border-muted-foreground/30 hover:bg-muted/20'
      }`}
      onClick={() => onViewOutput(work)}
    >
      <div className="flex justify-between items-start gap-2">
        <div className="flex-1 min-w-0">
          {/* Task and agent type */}
          <div className="flex items-start gap-2 mb-1">
            <span
              className={`text-sm font-medium line-clamp-2 ${
                isPaused ? 'text-muted-foreground' : ''
              }`}
            >
              {work.task}
            </span>
          </div>

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            {/* Agent type badge */}
            <span
              className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                AGENT_COLORS[work.agent_type] || 'bg-gray-100 text-gray-700'
              }`}
            >
              {work.agent_type}
            </span>

            {/* Project name */}
            <span className="text-muted-foreground/70">
              {work.project_name}
            </span>

            {/* Recurring: frequency and next run */}
            {work.is_recurring ? (
              <>
                <span className="flex items-center gap-1">
                  <RefreshCw className="w-3 h-3" />
                  {work.frequency}
                </span>
                {work.is_active && formatNextRun && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatNextRun(work.next_run)}
                  </span>
                )}
                {isPaused && (
                  <span className="text-yellow-600 dark:text-yellow-400 font-medium">
                    Paused
                  </span>
                )}
              </>
            ) : (
              <>
                {/* One-time: status and created */}
                {statusConfig && (
                  <span
                    className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded ${statusConfig.color}`}
                  >
                    {statusConfig.icon}
                    {statusConfig.label}
                  </span>
                )}
                {formatCreatedAt && (
                  <span>{formatCreatedAt(work.created_at)}</span>
                )}
              </>
            )}
          </div>
        </div>

        {/* Actions */}
        <div
          className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => e.stopPropagation()}
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
          ) : (
            <>
              {work.is_recurring && (
                <button
                  onClick={() => onToggle(work.id, work.is_active ?? true)}
                  className="p-1.5 text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-muted"
                  title={work.is_active ? 'Pause schedule' : 'Resume schedule'}
                >
                  {work.is_active ? (
                    <Pause className="w-4 h-4" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                </button>
              )}
              <button
                onClick={() => onDelete(work.id)}
                className="p-1.5 text-muted-foreground hover:text-destructive transition-colors rounded-md hover:bg-muted"
                title="Delete work"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
