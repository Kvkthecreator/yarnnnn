import type { Role } from '@/types';

/** ADR-176 v5: Universal specialist roster labels, shared across list/detail/settings/dashboard */
export const ROLE_LABELS: Partial<Record<Role, string>> = {
  // v5 canonical specialists (ADR-176)
  researcher: 'Researcher',
  analyst: 'Analyst',
  writer: 'Writer',
  tracker: 'Tracker',
  designer: 'Designer',
  executive: 'Reporting',
  slack_bot: 'Slack Bot',
  notion_bot: 'Notion Bot',
  github_bot: 'GitHub Bot',
  thinking_partner: 'Thinking Partner',
  // v4 ICP legacy (backward-compat display)
  competitive_intel: 'Competitive Intelligence',
  market_research: 'Market Research',
  business_dev: 'Business Development',
  operations: 'Operations',
  marketing: 'Marketing & Creative',
  // older legacy
  digest: 'Recap',
  prepare: 'Auto Meeting Prep',
  synthesize: 'Work Summary',
  monitor: 'Watch',
  research: 'Research',
  act: 'Action',
  custom: 'Custom',
};
