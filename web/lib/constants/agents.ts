import type { Role } from '@/types';

/** ADR-176 v5: Universal specialist roster labels, shared across list/detail/settings/dashboard */
export const ROLE_LABELS: Partial<Record<Role, string>> = {
  // v5 canonical specialists (ADR-176 — current model, 9 agents at signup)
  researcher: 'Researcher',
  analyst: 'Analyst',
  writer: 'Writer',
  tracker: 'Tracker',
  designer: 'Designer',
  slack_bot: 'Slack Bot',
  notion_bot: 'Notion Bot',
  github_bot: 'GitHub Bot',
  thinking_partner: 'System Agent',  // ADR-251: cockpit entity label
  // v4 ICP legacy — kept for backward-compat display of pre-ADR-176 workspaces only.
  // These role values exist in the DB for users created before ADR-176 migration.
  // Remove after Phase 5 clean-slate migration wipes old role values.
  competitive_intel: 'Competitive Intelligence',
  market_research: 'Market Research',
  business_dev: 'Business Development',
  operations: 'Operations',
  marketing: 'Marketing & Creative',
  executive: 'Reporting',
  // older legacy (pre-ADR-109 role enum — remove when no DB rows remain)
  digest: 'Recap',
  prepare: 'Auto Meeting Prep',
  synthesize: 'Work Summary',
  monitor: 'Watch',
  research: 'Research',
  act: 'Action',
  custom: 'Custom',
};
