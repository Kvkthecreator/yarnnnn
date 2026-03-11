import type { AgentType } from '@/types';

/** ADR-093: 7 purpose-first type labels, shared across list/detail/settings/dashboard */
export const DELIVERABLE_TYPE_LABELS: Record<AgentType, string> = {
  digest: 'Recap',
  brief: 'Auto Meeting Prep',
  status: 'Work Summary',
  watch: 'Watch',
  deep_research: 'Proactive Insights',
  coordinator: 'Coordinator',
  custom: 'Custom',
};
