import type { DeliverableType } from '@/types';

/** ADR-093: 7 purpose-first type labels, shared across list/detail/settings/dashboard */
export const DELIVERABLE_TYPE_LABELS: Record<DeliverableType, string> = {
  digest: 'Digest',
  brief: 'Brief',
  status: 'Status Update',
  watch: 'Watch',
  deep_research: 'Deep Research',
  coordinator: 'Coordinator',
  custom: 'Custom',
};
