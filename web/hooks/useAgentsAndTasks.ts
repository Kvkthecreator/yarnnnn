'use client';

/**
 * useAgentsAndTasks — Shared data loading hook with polling.
 *
 * SURFACE-ARCHITECTURE.md v7: Single data loading pattern replaces
 * three duplicate implementations in Home, Agents, and Context pages.
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api/client';
import type { Agent, Task } from '@/types';

interface UseAgentsAndTasksOptions {
  /** Polling interval in ms (default: 30000) */
  pollInterval?: number;
  /** Whether to refresh on tab visibility change (default: true) */
  refreshOnFocus?: boolean;
}

interface UseAgentsAndTasksResult {
  agents: Agent[];
  tasks: Task[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

export function useAgentsAndTasks(
  options: UseAgentsAndTasksOptions = {}
): UseAgentsAndTasksResult {
  const { pollInterval = 30_000, refreshOnFocus = true } = options;

  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [agentList, taskList] = await Promise.all([
        api.agents.list(),
        api.tasks.list(),
      ]);
      setAgents(agentList);
      setTasks(taskList);
      setError(null);
    } catch {
      setError('Failed to load agents and tasks.');
    } finally {
      setLoading(false);
    }
  }, []);

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

  return { agents, tasks, loading, error, reload: loadData };
}
