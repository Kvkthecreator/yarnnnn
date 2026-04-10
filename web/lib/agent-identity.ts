/**
 * Agent identity and presentation helpers.
 *
 * Single frontend source of truth for:
 * - canonical agent type resolution
 * - display names and taglines
 * - avatar, badge, and author colors
 * - agent class labels
 * - stable slug generation
 *
 * Backend canonical types live in `api/services/agent_framework.py`.
 * Frontend helpers here must stay aligned with that roster.
 */

type CanonicalAgentRole =
  | 'competitive_intel'
  | 'market_research'
  | 'business_dev'
  | 'operations'
  | 'marketing'
  | 'executive'
  | 'slack_bot'
  | 'notion_bot'
  | 'github_bot'
  | 'thinking_partner';

type AgentClass = 'domain-steward' | 'synthesizer' | 'platform-bot' | 'meta-cognitive';
export type PlatformBotProvider = 'slack' | 'notion' | 'github';

interface RoleMeta {
  displayName: string;
  shortLabel: string;
  tagline: string;
  avatarHex: string;
  badgeClass: string;
  authorClass: string;
  /** Lucide icon name for this role — used by AgentIcon component */
  iconName: string;
}

const LEGACY_ROLE_MAP: Record<string, CanonicalAgentRole> = {
  digest: 'competitive_intel',
  synthesize: 'executive',
  prepare: 'marketing',
  custom: 'competitive_intel',
  briefer: 'competitive_intel',
  monitor: 'operations',
  scout: 'competitive_intel',
  researcher: 'market_research',
  analyst: 'competitive_intel',
  drafter: 'marketing',
  writer: 'marketing',
  planner: 'operations',
  research: 'competitive_intel',
  content: 'marketing',
  crm: 'business_dev',
};

const ROLE_META: Record<CanonicalAgentRole, RoleMeta> = {
  competitive_intel: {
    displayName: 'Competitive Intelligence',
    shortLabel: 'CI',
    tagline: 'Tracks and analyzes competitors',
    avatarHex: '#3b82f6',
    badgeClass: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    authorClass: 'text-blue-600 dark:text-blue-400',
    iconName: 'Crosshair',
  },
  market_research: {
    displayName: 'Market Research',
    shortLabel: 'Market',
    tagline: 'Tracks market trends and opportunities',
    avatarHex: '#0ea5e9',
    badgeClass: 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
    authorClass: 'text-sky-600 dark:text-sky-400',
    iconName: 'TrendingUp',
  },
  business_dev: {
    displayName: 'Business Development',
    shortLabel: 'Biz Dev',
    tagline: 'Manages relationships and deals',
    avatarHex: '#f97316',
    badgeClass: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
    authorClass: 'text-orange-600 dark:text-orange-400',
    iconName: 'Handshake',
  },
  operations: {
    displayName: 'Operations',
    shortLabel: 'Ops',
    tagline: 'Tracks projects and workstreams',
    avatarHex: '#10b981',
    badgeClass: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    authorClass: 'text-emerald-600 dark:text-emerald-400',
    iconName: 'Settings2',
  },
  marketing: {
    displayName: 'Marketing & Creative',
    shortLabel: 'Marketing',
    tagline: 'Creates content and go-to-market materials',
    avatarHex: '#ec4899',
    badgeClass: 'bg-pink-100 text-pink-700 dark:bg-pink-900/40 dark:text-pink-300',
    authorClass: 'text-pink-600 dark:text-pink-400',
    iconName: 'Megaphone',
  },
  executive: {
    displayName: 'Reporting',
    shortLabel: 'Reporting',
    tagline: 'Cross-domain synthesis and reporting',
    avatarHex: '#8b5cf6',
    badgeClass: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
    authorClass: 'text-violet-600 dark:text-violet-400',
    iconName: 'BarChart3',
  },
  slack_bot: {
    displayName: 'Slack Bot',
    shortLabel: 'Slack',
    tagline: 'Captures Slack activity',
    avatarHex: '#14b8a6',
    badgeClass: 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300',
    authorClass: 'text-teal-600 dark:text-teal-400',
    iconName: 'Hash',
  },
  notion_bot: {
    displayName: 'Notion Bot',
    shortLabel: 'Notion',
    tagline: 'Tracks Notion changes',
    avatarHex: '#6366f1',
    badgeClass: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300',
    authorClass: 'text-indigo-600 dark:text-indigo-400',
    iconName: 'BookOpen',
  },
  github_bot: {
    displayName: 'GitHub Bot',
    shortLabel: 'GitHub',
    tagline: 'Tracks GitHub activity',
    avatarHex: '#64748b',
    badgeClass: 'bg-slate-100 text-slate-700 dark:bg-slate-900/40 dark:text-slate-300',
    authorClass: 'text-slate-600 dark:text-slate-400',
    iconName: 'GitBranch',
  },
  thinking_partner: {
    displayName: 'Thinking Partner',
    shortLabel: 'TP',
    tagline: 'Orchestrates your workforce',
    avatarHex: '#1f2937',
    badgeClass: 'bg-gray-800 text-gray-100 dark:bg-gray-700 dark:text-gray-100',
    authorClass: 'text-gray-900 dark:text-gray-100',
    iconName: 'MessageCircle',
  },
};

const CLASS_META: Record<AgentClass, { label: string; description: string }> = {
  'domain-steward': {
    label: 'Specialist',
    description: 'Owns one context domain and accumulates judgment over time.',
  },
  synthesizer: {
    label: 'Reporting',
    description: 'Reads across domains and produces cross-domain synthesis.',
  },
  'platform-bot': {
    label: 'Integration',
    description: 'Bridges one external platform into the workspace.',
  },
  'meta-cognitive': {
    label: 'Thinking Partner',
    description: 'Owns orchestration and back office maintenance.',
  },
};

function isCanonicalRole(role: string): role is CanonicalAgentRole {
  return role in ROLE_META;
}

export function resolveRole(role?: string | null): CanonicalAgentRole | string {
  if (!role) return 'competitive_intel';
  if (isCanonicalRole(role)) return role;
  return LEGACY_ROLE_MAP[role] || role;
}

function getRoleMeta(role?: string | null): RoleMeta | null {
  const resolved = resolveRole(role);
  return isCanonicalRole(resolved) ? ROLE_META[resolved] : null;
}

export function avatarColor(role?: string | null): string {
  return getRoleMeta(role)?.avatarHex || '#6b7280';
}

export function roleBadgeColor(role?: string | null): string {
  return getRoleMeta(role)?.badgeClass || 'bg-muted text-muted-foreground';
}

export function authorColor(role?: string | null): string {
  return getRoleMeta(role)?.authorClass || 'text-muted-foreground/70';
}

export function roleDisplayName(role?: string | null): string {
  return getRoleMeta(role)?.displayName || role || '';
}

export function roleShortLabel(role?: string | null): string {
  return getRoleMeta(role)?.shortLabel || roleDisplayName(role);
}

export function roleTagline(role?: string | null): string {
  return getRoleMeta(role)?.tagline || '';
}

export function agentClassLabel(agentClass?: string | null): string {
  if (!agentClass) return 'Specialist';
  return CLASS_META[agentClass as AgentClass]?.label || agentClass.replace(/-/g, ' ');
}

export function agentClassDescription(agentClass?: string | null): string {
  if (!agentClass) return CLASS_META['domain-steward'].description;
  return CLASS_META[agentClass as AgentClass]?.description || '';
}

export function scopeDisplayName(scope?: string) {
  switch (scope) {
    case 'platform':
      return 'Single platform';
    case 'cross_platform':
      return 'Cross-platform';
    case 'knowledge':
      return 'Knowledge';
    case 'research':
      return 'Research';
    case 'autonomous':
      return 'Autonomous';
    default:
      return scope?.replace(/_/g, ' ') || '';
  }
}

export function statusIndicator(status?: string): { color: string; label: string } {
  switch (status) {
    case 'active':
      return { color: 'bg-green-500', label: 'Active' };
    case 'paused':
      return { color: 'bg-amber-500', label: 'Paused' };
    case 'archived':
      return { color: 'bg-gray-400', label: 'Archived' };
    default:
      return { color: 'bg-green-500', label: 'Active' };
  }
}

export function agentDisplayName(title?: string, slug?: string): string {
  if (title) return title;
  if (slug) return slug.replace(/-/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
  return 'Agent';
}

export function agentInitials(name: string): string {
  return name.split(' ').map((word) => word[0]).join('').slice(0, 2).toUpperCase();
}

export function getAgentSlug(agent: { slug?: string | null; title?: string | null }): string {
  if (agent.slug?.trim()) return agent.slug;
  const title = (agent.title || '').toLowerCase().trim();
  const slug = title.replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  return slug || 'agent';
}

export function roleIconName(role?: string | null): string {
  return getRoleMeta(role)?.iconName || 'Brain';
}

export function platformProviderForRole(role?: string | null): PlatformBotProvider | null {
  switch (resolveRole(role)) {
    case 'slack_bot':
      return 'slack';
    case 'notion_bot':
      return 'notion';
    case 'github_bot':
      return 'github';
    default:
      return null;
  }
}
