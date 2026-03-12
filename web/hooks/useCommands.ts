"use client";

/**
 * ADR-025: Slash Commands
 * Hook for fetching available commands for autocomplete/picker
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { api } from "@/lib/api/client";
import type { SlashCommand, CommandTier } from "@/types";

export function useCommands() {
  const [commands, setCommands] = useState<SlashCommand[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.commands.list();
      setCommands(data.commands);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Separate commands by tier for UI grouping
  const commandsByTier = useMemo(() => {
    const grouped: Record<CommandTier, SlashCommand[]> = {
      core: [],
      beta: [],
    };
    for (const cmd of commands) {
      grouped[cmd.tier].push(cmd);
    }
    return grouped;
  }, [commands]);

  // Search/filter commands by query (matches command, name, or trigger patterns)
  const filterCommands = useCallback(
    (query: string): SlashCommand[] => {
      if (!query) return commands;
      const lower = query.toLowerCase().replace(/^\//, ""); // Remove leading slash
      return commands.filter(
        (cmd) =>
          cmd.command.toLowerCase().includes(lower) ||
          cmd.name.toLowerCase().includes(lower) ||
          cmd.description.toLowerCase().includes(lower) ||
          cmd.trigger_patterns.some((pattern) =>
            pattern.toLowerCase().includes(lower)
          )
      );
    },
    [commands]
  );

  return {
    commands,
    commandsByTier,
    isLoading,
    error,
    reload: load,
    filterCommands,
  };
}
