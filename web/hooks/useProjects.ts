"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api/client";
import type { Project, ProjectCreate, ProjectWithCounts } from "@/types";

export function useProjects(workspaceId: string | null) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    if (!workspaceId) {
      setProjects([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await api.projects.list(workspaceId);
      setProjects(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  const create = useCallback(
    async (data: ProjectCreate) => {
      if (!workspaceId) throw new Error("No workspace selected");
      const created = await api.projects.create(workspaceId, data);
      setProjects((prev) => [...prev, created]);
      return created;
    },
    [workspaceId]
  );

  useEffect(() => {
    load();
  }, [load]);

  return {
    projects,
    isLoading,
    error,
    reload: load,
    create,
  };
}

export function useProject(projectId: string | null) {
  const [project, setProject] = useState<ProjectWithCounts | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    if (!projectId) {
      setProject(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await api.projects.get(projectId);
      setProject(data);
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
    project,
    isLoading,
    error,
    reload: load,
  };
}
