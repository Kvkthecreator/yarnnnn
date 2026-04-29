'use client';

import { useState, useEffect, useCallback } from 'react';
import { APIError, api } from '@/lib/api/client';
import type { RecurrenceDetail } from '@/types';

interface UseRecurrenceDetailResult {
  task: RecurrenceDetail | null;
  loading: boolean;
  error: string | null;
  notFound: boolean;
  reload: () => Promise<void>;
}

export function useRecurrenceDetail(taskSlug: string | null): UseRecurrenceDetailResult {
  const [task, setTask] = useState<RecurrenceDetail | null>(null);
  const [loading, setLoading] = useState(Boolean(taskSlug));
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const loadTask = useCallback(async () => {
    if (!taskSlug) {
      setTask(null);
      setLoading(false);
      setError(null);
      setNotFound(false);
      return;
    }

    setLoading(true);
    setError(null);
    setNotFound(false);

    try {
      const detail = await api.recurrences.get(taskSlug);
      setTask(detail);
    } catch (err) {
      setTask(null);
      if (err instanceof APIError && err.status === 404) {
        setNotFound(true);
      } else if (err instanceof Error && err.message.trim()) {
        setError(err.message);
      } else {
        setError('Failed to load task detail.');
      }
    } finally {
      setLoading(false);
    }
  }, [taskSlug]);

  useEffect(() => {
    loadTask();
  }, [loadTask]);

  return { task, loading, error, notFound, reload: loadTask };
}
