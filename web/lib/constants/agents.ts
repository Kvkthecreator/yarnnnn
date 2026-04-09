import type { Role } from '@/types';

/** ADR-109: Role labels, shared across list/detail/settings/dashboard */
export const ROLE_LABELS: Partial<Record<Role, string>> = {
  competitive_intel: 'Competitive Intelligence',
  market_research: 'Market Research',
  business_dev: 'Business Development',
  operations: 'Operations',
  marketing: 'Marketing & Creative',
  executive: 'Reporting',
  slack_bot: 'Slack Bot',
  notion_bot: 'Notion Bot',
  github_bot: 'GitHub Bot',
  thinking_partner: 'Thinking Partner',
  digest: 'Recap',
  prepare: 'Auto Meeting Prep',
  synthesize: 'Work Summary',
  monitor: 'Watch',
  research: 'Research',
  act: 'Action',
  custom: 'Custom',
};
