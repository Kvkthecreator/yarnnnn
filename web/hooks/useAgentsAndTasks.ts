'use client';

/**
 * useAgentsAndTasks — Shared data loading hook with polling.
 *
 * SURFACE-ARCHITECTURE.md v7: Single data loading pattern replaces
 * three duplicate implementations in Home, Agents, and Context pages.
 *
 * ADR-219 Commit 4: also fetches /api/narrative/by-task and exposes
 * the result as a Map<task_slug, NarrativeByTaskSlice>. WorkListSurface
 * uses this to render recent-activity headlines sourced from the
 * narrative substrate instead of task.last_run_at timestamps.
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api/client';
import type { Agent, Task, NarrativeByTaskSlice } from '@/types';

interface UseAgentsAndTasksOptions {
  /** Polling interval in ms (default: 30000) */
  pollInterval?: number;
  /** Whether to refresh on tab visibility change (default: true) */
  refreshOnFocus?: boolean;
  /**
   * ADR-219 Commit 4: also fetch /api/narrative/by-task and expose
   * the result. Off by default so callers that don't render
   * recent-activity headlines (e.g. agent detail, chat session list)
   * don't incur the extra round-trip every poll. /work opts in.
   */
  includeNarrative?: boolean;
}

interface UseAgentsAndTasksResult {
  agents: Agent[];
  tasks: Task[];
  /** ADR-219 Commit 4: per-task narrative slice keyed by slug. */
  narrativeByTask: Map<string, NarrativeByTaskSlice>;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

export function useAgentsAndTasks(
  options: UseAgentsAndTasksOptions = {}
): UseAgentsAndTasksResult {
  const { pollInterval = 30_000, refreshOnFocus = true, includeNarrative = false } = options;

  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [narrativeByTask, setNarrativeByTask] = useState<Map<string, NarrativeByTaskSlice>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      if (includeNarrative) {
        // ADR-219 Commit 4: narrative is best-effort — if the endpoint
        // fails we still want agents+tasks to render. Wrap it so a
        // narrative fetch failure doesn't blow up the whole surface.
        const narrativePromise = api.narrative
          .byTask()
          .catch(() => ({ window_hours: 24, tasks: [] }));

        const [agentList, taskList, narrativeResp] = await Promise.all([
          api.agents.list(),
          api.tasks.list(),
          narrativePromise,
        ]);
        setAgents(agentList);
        setTasks(taskList);

        const map = new Map<string, NarrativeByTaskSlice>();
        for (const slice of narrativeResp.tasks) {
          map.set(slice.task_slug, slice);
        }
        setNarrativeByTask(map);
      } else {
        const [agentList, taskList] = await Promise.all([
          api.agents.list(),
          api.tasks.list(),
        ]);
        setAgents(agentList);
        setTasks(taskList);
      }

      setError(null);
    } catch {
      setError('Failed to load agents and tasks.');
    } finally {
      setLoading(false);
    }
  }, [includeNarrative]);

  // Initial load
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Polling
  useEffect(() => {
    if (pollInterval <= 0) return;
    const interval = setInterval(loadData, pollInterval);
    return () => clearInterval(interval);
  }, [loadData, pollInterval]);

  // Refresh on tab focus
  useEffect(() => {
    if (!refreshOnFocus) return;
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') loadData();
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [loadData, refreshOnFocus]);

  return { agents, tasks, narrativeByTask, loading, error, reload: loadData };
}
