"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api/client";
import type { Block, BlockCreate, ContextBundle } from "@/types";

export function useBlocks(projectId: string | null) {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    if (!projectId) {
      setBlocks([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await api.context.listBlocks(projectId);
      setBlocks(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  const create = useCallback(
    async (data: BlockCreate) => {
      if (!projectId) throw new Error("No project selected");
      const created = await api.context.createBlock(projectId, data);
      setBlocks((prev) => [...prev, created]);
      return created;
    },
    [projectId]
  );

  const remove = useCallback(async (blockId: string) => {
    await api.context.deleteBlock(blockId);
    setBlocks((prev) => prev.filter((b) => b.id !== blockId));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return {
    blocks,
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
