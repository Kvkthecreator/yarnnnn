import type { Role } from '@/types';

/** ADR-109: Role labels, shared across list/detail/settings/dashboard */
export const ROLE_LABELS: Record<Role, string> = {
  digest: 'Recap',
  prepare: 'Auto Meeting Prep',
  synthesize: 'Work Summary',
  monitor: 'Watch',
  research: 'Research',
  act: 'Action',
  custom: 'Custom',
};
