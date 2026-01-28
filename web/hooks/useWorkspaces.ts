"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api/client";
import type { Workspace, WorkspaceCreate } from "@/types";

export function useWorkspaces() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.workspaces.list();
      setWorkspaces(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const create = useCallback(async (data: WorkspaceCreate) => {
    const created = await api.workspaces.create(data);
    setWorkspaces((prev) => [...prev, created]);
    return created;
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return {
    workspaces,
    isLoading,
    error,
    reload: load,
    create,
  };
}
