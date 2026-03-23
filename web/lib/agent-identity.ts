/**
 * Agent Identity — shared visual identity system for agents.
 *
 * Single source of truth for agent colors, display names, badges, and initials.
 * Used by AgentAvatar, project pages, agent lists, dashboard, and chat attribution.
 *
 * v2 (ADR-130): 8 user-facing types + PM. Types are product offerings.
 * Legacy role names (digest, synthesize, research, prepare, custom) mapped to new types.
 */

// =============================================================================
// Legacy role → new type mapping
// =============================================================================

function resolveRole(role?: string): string {
  if (!role) return 'briefer';
  switch (role) {
    case 'digest': return 'briefer';
    case 'synthesize': return 'analyst';
    case 'research': return 'researcher';
    case 'prepare': return 'planner';
    case 'custom': return 'briefer';
    default: return role;
  }
}

// =============================================================================
// Role → Color mapping
// =============================================================================

/** Avatar background hex color by role — inline styles, immune to Tailwind purge */
export function avatarColor(role?: string): string {
  switch (resolveRole(role)) {
    case 'pm':         return '#9333ea';  // purple-600
    case 'briefer':    return '#3b82f6';  // blue-500
    case 'monitor':    return '#f59e0b';  // amber-500
    case 'researcher': return '#22c55e';  // green-500
    case 'drafter':    return '#6366f1';  // indigo-500
    case 'analyst':    return '#14b8a6';  // teal-500
    case 'writer':     return '#ec4899';  // pink-500
    case 'planner':    return '#8b5cf6';  // violet-500
    case 'scout':      return '#f97316';  // orange-500
    default:           return '#6b7280';  // gray-500
  }
}

/** Role badge background + text color (light/dark variants) */
export function roleBadgeColor(role?: string): string {
  switch (resolveRole(role)) {
    case 'pm':         return 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300';
    case 'briefer':    return 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300';
    case 'monitor':    return 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300';
    case 'researcher': return 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300';
    case 'drafter':    return 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300';
    case 'analyst':    return 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300';
    case 'writer':     return 'bg-pink-100 text-pink-700 dark:bg-pink-900/40 dark:text-pink-300';
    case 'planner':    return 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300';
    case 'scout':      return 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300';
    default:           return 'bg-muted text-muted-foreground';
  }
}

/** Chat message author accent color */
export function authorColor(authorRole?: string): string {
  switch (resolveRole(authorRole)) {
    case 'pm':         return 'text-purple-600 dark:text-purple-400';
    case 'briefer':    return 'text-blue-600 dark:text-blue-400';
    case 'monitor':    return 'text-amber-600 dark:text-amber-400';
    case 'researcher': return 'text-green-600 dark:text-green-400';
    case 'drafter':    return 'text-indigo-600 dark:text-indigo-400';
    case 'analyst':    return 'text-teal-600 dark:text-teal-400';
    case 'writer':     return 'text-pink-600 dark:text-pink-400';
    case 'planner':    return 'text-violet-600 dark:text-violet-400';
    case 'scout':      return 'text-orange-600 dark:text-orange-400';
    default:           return 'text-muted-foreground/70';
  }
}

// =============================================================================
// Display name helpers
// =============================================================================

/** Role → user-facing display name (product name) */
export function roleDisplayName(role?: string): string {
  switch (resolveRole(role)) {
    case 'pm':         return 'Project Manager';
    case 'briefer':    return 'Briefer';
    case 'monitor':    return 'Monitor';
    case 'researcher': return 'Researcher';
    case 'drafter':    return 'Drafter';
    case 'analyst':    return 'Analyst';
    case 'writer':     return 'Writer';
    case 'planner':    return 'Planner';
    case 'scout':      return 'Scout';
    default:           return role || '';
  }
}

/** Short role label for compact displays */
export function roleShortLabel(role?: string): string {
  switch (resolveRole(role)) {
    case 'pm': return 'PM';
    default: return roleDisplayName(role);
  }
}

/** Role → one-line tagline (what it does for the user) */
export function roleTagline(role?: string): string {
  switch (resolveRole(role)) {
    case 'briefer':    return 'Keeps you briefed on what\'s happening';
    case 'monitor':    return 'Watches for what matters and alerts you';
    case 'researcher': return 'Investigates topics and produces analysis';
    case 'drafter':    return 'Produces deliverables and documents for you';
    case 'analyst':    return 'Tracks metrics and surfaces patterns';
    case 'writer':     return 'Crafts communications and content';
    case 'planner':    return 'Prepares plans, agendas, and follow-ups';
    case 'scout':      return 'Tracks competitors and market movements';
    case 'pm':         return 'Coordinates your project team';
    default:           return '';
  }
}

/** Scope → user-facing display name */
export function scopeDisplayName(scope?: string): string {
  switch (scope) {
    case 'platform': return 'Single platform';
    case 'cross_platform': return 'Cross-platform';
    case 'knowledge': return 'Knowledge';
    case 'research': return 'Research';
    case 'autonomous': return 'Autonomous';
    default: return scope?.replace(/_/g, ' ') || '';
  }
}

// =============================================================================
// Status helpers
// =============================================================================

/** Status → color + label */
export function statusIndicator(status?: string): { color: string; label: string } {
  switch (status) {
    case 'active': return { color: 'bg-green-500', label: 'Active' };
    case 'paused': return { color: 'bg-amber-500', label: 'Paused' };
    case 'archived': return { color: 'bg-gray-400', label: 'Archived' };
    default: return { color: 'bg-green-500', label: 'Active' };
  }
}

// =============================================================================
// Name + initials
// =============================================================================

/** Display name from title or slug */
export function agentDisplayName(title?: string, slug?: string): string {
  if (title) return title;
  if (slug) return slug.replace(/-/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase());
  return 'Agent';
}

/** Extract 1-2 letter initials from a display name */
export function agentInitials(name: string): string {
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
}
