'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api/client';
import type { TaskOutput } from '@/types';

interface UseTaskOutputsOptions {
  includeLatest?: boolean;
  historyLimit?: number;
  refreshKey?: number;
}

interface UseTaskOutputsResult {
  latest: TaskOutput | null;
  history: TaskOutput[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

export function useTaskOutputs(
  taskSlug: string,
  {
    includeLatest = true,
    historyLimit,
    refreshKey = 0,
  }: UseTaskOutputsOptions = {},
): UseTaskOutputsResult {
  const [latest, setLatest] = useState<TaskOutput | null>(null);
  const [history, setHistory] = useState<TaskOutput[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadOutputs = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [latestOutput, historyResponse] = await Promise.all([
        includeLatest ? api.recurrences.getLatestOutput(taskSlug) : Promise.resolve(null),
        historyLimit ? api.recurrences.listOutputs(taskSlug, historyLimit) : Promise.resolve({ outputs: [] as TaskOutput[], total: 0 }),
      ]);

      setLatest(latestOutput);
      setHistory(historyResponse.outputs ?? []);
    } catch (err) {
      setLatest(null);
      setHistory([]);
      if (err instanceof Error && err.message.trim()) {
        setError(err.message);
      } else {
        setError('Failed to load task outputs.');
      }
    } finally {
      setLoading(false);
    }
  }, [includeLatest, historyLimit, taskSlug]);

  useEffect(() => {
    loadOutputs();
  }, [loadOutputs, refreshKey]);

  return { latest, history, loading, error, reload: loadOutputs };
}
