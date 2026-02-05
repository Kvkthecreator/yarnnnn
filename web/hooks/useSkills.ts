"use client";

/**
 * ADR-025: Skills (Slash Commands)
 * Hook for fetching available skills for autocomplete/picker
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { api } from "@/lib/api/client";
import type { Skill, SkillTier } from "@/types";

export function useSkills() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.skills.list();
      setSkills(data.skills);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Separate skills by tier for UI grouping
  const skillsByTier = useMemo(() => {
    const grouped: Record<SkillTier, Skill[]> = {
      core: [],
      beta: [],
    };
    for (const skill of skills) {
      grouped[skill.tier].push(skill);
    }
    return grouped;
  }, [skills]);

  // Search/filter skills by query (matches command, name, or trigger patterns)
  const filterSkills = useCallback(
    (query: string): Skill[] => {
      if (!query) return skills;
      const lower = query.toLowerCase().replace(/^\//, ""); // Remove leading slash
      return skills.filter(
        (skill) =>
          skill.command.toLowerCase().includes(lower) ||
          skill.name.toLowerCase().includes(lower) ||
          skill.description.toLowerCase().includes(lower) ||
          skill.trigger_patterns.some((pattern) =>
            pattern.toLowerCase().includes(lower)
          )
      );
    },
    [skills]
  );

  return {
    skills,
    skillsByTier,
    isLoading,
    error,
    reload: load,
    filterSkills,
  };
}
