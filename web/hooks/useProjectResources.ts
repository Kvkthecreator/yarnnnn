"use client";

/**
 * ADR-031 Phase 6: Project Resources Hook
 *
 * Manages platform resources linked to projects for cross-platform synthesizers.
 * Resources can be Slack channels, Gmail labels, Notion pages, or calendars.
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api/client";
import type {
  ProjectResource,
  ProjectResourceCreate,
  ResourceSuggestion,
  ContextSummaryItem,
} from "@/types";

interface UseProjectResourcesOptions {
  projectId: string | null;
  platform?: string;
  autoLoad?: boolean;
}

export function useProjectResources({
  projectId,
  platform,
  autoLoad = true,
}: UseProjectResourcesOptions) {
  const [resources, setResources] = useState<ProjectResource[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    if (!projectId) {
      setResources([]);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await api.projects.resources.list(projectId, platform);
      setResources(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, platform]);

  const addResource = useCallback(
    async (data: ProjectResourceCreate) => {
      if (!projectId) throw new Error("No project selected");

      const created = await api.projects.resources.create(projectId, data);
      setResources((prev) => [...prev, created]);
      return created;
    },
    [projectId]
  );

  const removeResource = useCallback(
    async (resourceId: string) => {
      if (!projectId) throw new Error("No project selected");

      await api.projects.resources.delete(projectId, resourceId);
      setResources((prev) => prev.filter((r) => r.id !== resourceId));
    },
    [projectId]
  );

  useEffect(() => {
    if (autoLoad) {
      load();
    }
  }, [load, autoLoad]);

  return {
    resources,
    isLoading,
    error,
    reload: load,
    addResource,
    removeResource,
  };
}

interface UseResourceSuggestionsOptions {
  projectId: string | null;
  autoLoad?: boolean;
}

export function useResourceSuggestions({
  projectId,
  autoLoad = false,
}: UseResourceSuggestionsOptions) {
  const [suggestions, setSuggestions] = useState<ResourceSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    if (!projectId) {
      setSuggestions([]);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await api.projects.resources.suggest(projectId);
      setSuggestions(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (autoLoad && projectId) {
      load();
    }
  }, [load, autoLoad, projectId]);

  return {
    suggestions,
    isLoading,
    error,
    refresh: load,
  };
}

interface UseContextSummaryOptions {
  projectId: string | null;
  days?: number;
  autoLoad?: boolean;
}

export function useContextSummary({
  projectId,
  days = 7,
  autoLoad = true,
}: UseContextSummaryOptions) {
  const [summary, setSummary] = useState<ContextSummaryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    if (!projectId) {
      setSummary([]);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await api.projects.resources.contextSummary(projectId, days);
      setSummary(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, days]);

  // Compute aggregate stats
  const stats = {
    totalItems: summary.reduce((sum, item) => sum + item.item_count, 0),
    platformCount: new Set(summary.map((item) => item.platform)).size,
    resourceCount: summary.length,
    hasData: summary.some((item) => item.item_count > 0),
  };

  useEffect(() => {
    if (autoLoad && projectId) {
      load();
    }
  }, [load, autoLoad, projectId]);

  return {
    summary,
    stats,
    isLoading,
    error,
    refresh: load,
  };
}
