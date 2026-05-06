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
 *
 * v5 (ADR-176): Universal specialist model — 6 specialists + 1 synthesizer + 3 bots.
 * ICP domain-steward roles (competitive_intel, market_research, business_dev,
 * operations, marketing) removed from canonical set; mapped via LEGACY_ROLE_MAP.
 */

type CanonicalAgentRole =
  | 'researcher'
  | 'analyst'
  | 'writer'
  | 'tracker'
  | 'designer'
  | 'executive'
  | 'slack_bot'
  | 'notion_bot'
  | 'github_bot'
  | 'thinking_partner'
  | 'reviewer';

type AgentClass = 'specialist' | 'synthesizer' | 'platform-bot' | 'meta-cognitive' | 'reviewer';
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
  // v1 legacy
  digest: 'researcher',
  synthesize: 'executive',
  prepare: 'writer',
  custom: 'researcher',
  // v2 legacy (ADR-130)
  briefer: 'writer',
  monitor: 'tracker',
  scout: 'tracker',
  drafter: 'writer',
  planner: 'analyst',
  // v3 legacy
  research: 'researcher',
  content: 'writer',
  crm: 'tracker',
  // v4 ICP domain-steward roles (ADR-140 → superseded by ADR-176)
  competitive_intel: 'researcher',
  market_research: 'researcher',
  business_dev: 'tracker',
  operations: 'tracker',
  marketing: 'writer',
};

const ROLE_META: Record<CanonicalAgentRole, RoleMeta> = {
  researcher: {
    displayName: 'Researcher',
    shortLabel: 'Research',
    tagline: 'Finds, investigates, and builds knowledge',
    avatarHex: '#3b82f6',
    badgeClass: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    authorClass: 'text-blue-600 dark:text-blue-400',
    iconName: 'Search',
  },
  analyst: {
    displayName: 'Analyst',
    shortLabel: 'Analysis',
    tagline: 'Reads accumulated context and finds patterns',
    avatarHex: '#0ea5e9',
    badgeClass: 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
    authorClass: 'text-sky-600 dark:text-sky-400',
    iconName: 'LineChart',
  },
  writer: {
    displayName: 'Writer',
    shortLabel: 'Writing',
    tagline: 'Drafts polished deliverables from context',
    avatarHex: '#f97316',
    badgeClass: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
    authorClass: 'text-orange-600 dark:text-orange-400',
    iconName: 'PenLine',
  },
  tracker: {
    displayName: 'Tracker',
    shortLabel: 'Tracking',
    tagline: 'Monitors signals and maintains entity profiles',
    avatarHex: '#10b981',
    badgeClass: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    authorClass: 'text-emerald-600 dark:text-emerald-400',
    iconName: 'Activity',
  },
  designer: {
    displayName: 'Designer',
    shortLabel: 'Design',
    tagline: 'Creates visual assets — charts, diagrams, images',
    avatarHex: '#ec4899',
    badgeClass: 'bg-pink-100 text-pink-700 dark:bg-pink-900/40 dark:text-pink-300',
    authorClass: 'text-pink-600 dark:text-pink-400',
    iconName: 'Palette',
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
  // ADR-251: cockpit entity label "System Agent". In chat speaks as "YARNNN" (brand).
  // Internal role slug `thinking_partner` is a data-compat exception (never user-facing).
  thinking_partner: {
    displayName: 'System Agent',
    shortLabel: 'System',
    tagline: 'Executes declared work. Narrates what happened.',
    avatarHex: '#1f2937',
    badgeClass: 'bg-gray-800 text-gray-100 dark:bg-gray-700 dark:text-gray-100',
    authorClass: 'text-gray-900 dark:text-gray-100',
    iconName: 'MessageCircle',
  },
  // ADR-214 + ADR-251: Reviewer as first-class surface. Substrate at /workspace/review/
  // per ADR-194 v2. Autonomy + Principles + heartbeat cadence housed here (ADR-251 D4).
  reviewer: {
    displayName: 'Reviewer',
    shortLabel: 'Reviewer',
    tagline: 'Your judgment seat — independent verdicts on proposed actions',
    avatarHex: '#e11d48',
    badgeClass: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
    authorClass: 'text-rose-600 dark:text-rose-400',
    iconName: 'ShieldCheck',
  },
};

const CLASS_META: Record<AgentClass, { label: string; description: string }> = {
  // NB: the enum key "specialist" is retained as a data-compatibility
  // exception (Python `PRODUCTION_ROLES[*]["class"]` + API + ADR-209
  // revision records). The human-readable label here is sharpened to
  // "Production Role" per LAYER-MAPPING.md (ADR-212).
  specialist: {
    label: 'Production Role',
    description: 'Orchestration capability bundle — research, analysis, writing, tracking, or design.',
  },
  synthesizer: {
    label: 'Reporting',
    description: 'Reads across domains and produces cross-domain synthesis.',
  },
  // NB: the enum key "platform-bot" is retained as a data-compatibility
  // exception. Under LAYER-MAPPING.md, what was called "Platform Bot" is
  // now "platform integration" — a capability bundle, not an Agent.
  'platform-bot': {
    label: 'Platform Integration',
    description: 'Platform-API capability bundle — activates when the platform is connected.',
  },
  // NB: enum key "meta-cognitive" is a data-compat exception (GLOSSARY).
  // Maps to "System Agent" at display layer per ADR-251.
  'meta-cognitive': {
    label: 'System Agent',
    description: 'System surface — executes declared work, narrates what happened.',
  },
  reviewer: {
    label: 'Reviewer',
    description: 'Judgment seat — independent verdicts on proposed actions (ADR-194 / ADR-251).',
  },
};

function isCanonicalRole(role: string): role is CanonicalAgentRole {
  return role in ROLE_META;
}

export function resolveRole(role?: string | null): CanonicalAgentRole | string {
  if (!role) return 'researcher';
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
  if (!agentClass) return 'Production Role';
  // backward compat: 'domain-steward' from old DB rows maps to 'specialist' enum
  if (agentClass === 'domain-steward') return 'Production Role';
  return CLASS_META[agentClass as AgentClass]?.label || agentClass.replace(/-/g, ' ');
}

export function agentClassDescription(agentClass?: string | null): string {
  if (!agentClass) return CLASS_META['specialist'].description;
  if (agentClass === 'domain-steward') return CLASS_META['specialist'].description;
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
