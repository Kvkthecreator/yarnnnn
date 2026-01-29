"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api/client";
import type { Memory, MemoryCreate, ContextBundle } from "@/types";

export function useProjectMemories(projectId: string | null) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    if (!projectId) {
      setMemories([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await api.projectMemories.list(projectId);
      setMemories(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  const create = useCallback(
    async (data: MemoryCreate) => {
      if (!projectId) throw new Error("No project selected");
      const created = await api.projectMemories.create(projectId, data);
      setMemories((prev) => [...prev, created]);
      return created;
    },
    [projectId]
  );

  const remove = useCallback(async (memoryId: string) => {
    await api.memories.delete(memoryId);
    setMemories((prev) => prev.filter((m) => m.id !== memoryId));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return {
    memories,
    isLoading,
    error,
    reload: load,
    create,
    remove,
  };
}

export function useUserMemories() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.userMemories.list();
      setMemories(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const create = useCallback(async (data: MemoryCreate) => {
    const created = await api.userMemories.create(data);
    setMemories((prev) => [...prev, created]);
    return created;
  }, []);

  const remove = useCallback(async (memoryId: string) => {
    await api.memories.delete(memoryId);
    setMemories((prev) => prev.filter((m) => m.id !== memoryId));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return {
    memories,
    isLoading,
    error,
    reload: load,
    create,
    remove,
  };
}

export function useContextBundle(projectId: string | null) {
  const [bundle, setBundle] = useState<ContextBundle | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    if (!projectId) {
      setBundle(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await api.context.getBundle(projectId);
      setBundle(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  return {
    bundle,
    isLoading,
    error,
    reload: load,
  };
}
