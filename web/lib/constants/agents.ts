import type { Skill } from '@/types';

/** ADR-109: Skill labels, shared across list/detail/settings/dashboard */
export const SKILL_LABELS: Record<Skill, string> = {
  digest: 'Recap',
  prepare: 'Auto Meeting Prep',
  synthesize: 'Work Summary',
  monitor: 'Watch',
  research: 'Research',
  orchestrate: 'Coordinator',
  act: 'Action',
  custom: 'Custom',
};
