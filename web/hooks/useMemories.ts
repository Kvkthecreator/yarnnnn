"use client";

/**
 * Memory hooks for context management
 *
 * ADR-034: Context v2 - Domain-based scoping
 * ADR-059: User context entries
 *
 * - useDomainMemories: Fetch memories for a specific domain
 * - useUserMemories: Fetch user-scoped context entries
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api/client";
import type { Memory, MemoryCreate, UserContextEntry } from "@/types";

/**
 * Hook to fetch and manage memories for a domain.
 * ADR-034: Context v2
 */
export function useDomainMemories(domainId: string | null) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    if (!domainId) {
      setMemories([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await api.domains.memories.list(domainId);
      setMemories(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, [domainId]);

  const create = useCallback(
    async (data: MemoryCreate) => {
      if (!domainId) throw new Error("No domain selected");
      const created = await api.domains.memories.create(domainId, data);
      setMemories((prev) => [...prev, created]);
      return created;
    },
    [domainId]
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

/**
 * Hook to fetch and manage user-scoped context entries.
 * ADR-059: User context entries (key-value pairs)
 */
export function useUserMemories() {
  const [entries, setEntries] = useState<UserContextEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.userMemories.list();
      setEntries(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const create = useCallback(async (data: { content: string; entry_type?: string }) => {
    const created = await api.userMemories.create(data);
    setEntries((prev) => [...prev, created]);
    return created;
  }, []);

  const remove = useCallback(async (entryId: string) => {
    await api.memories.delete(entryId);
    setEntries((prev) => prev.filter((e) => e.id !== entryId));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return {
    entries,
    // Alias for backwards compatibility
    memories: entries,
    isLoading,
    error,
    reload: load,
    create,
    remove,
  };
}
