/**
 * Agent Identity — shared visual identity system for agents.
 *
 * Single source of truth for agent colors, display names, badges, and initials.
 * Used by AgentAvatar, project pages, agent lists, dashboard, and chat attribution.
 *
 * v3 (ADR-140): 6 workforce types (4 agents + 2 bots). Two classes: agent (domain-cognitive) and bot (platform-mechanical).
 * Legacy role names mapped to new types via resolveRole().
 */

// =============================================================================
// Legacy role → new type mapping
// =============================================================================

function resolveRole(role?: string): string {
  if (!role) return 'research';
  switch (role) {
    // Legacy → research
    case 'briefer':    return 'research';
    case 'monitor':    return 'research';
    case 'scout':      return 'research';
    case 'digest':     return 'research';
    case 'researcher': return 'research';
    case 'analyst':    return 'research';
    case 'synthesize': return 'research';
    case 'custom':     return 'research';
    case 'pm':         return 'research'; // fallback
    // Legacy → content
    case 'drafter':    return 'content';
    case 'writer':     return 'content';
    case 'planner':    return 'content';
    case 'prepare':    return 'content';
    // Primary types pass through
    case 'research':   return 'research';
    case 'content':    return 'content';
    case 'marketing':  return 'marketing';
    case 'crm':        return 'crm';
    case 'slack_bot':  return 'slack_bot';
    case 'notion_bot': return 'notion_bot';
    default:           return role;
  }
}

// =============================================================================
// Role → Color mapping
// =============================================================================

/** Avatar background hex color by role — inline styles, immune to Tailwind purge */
export function avatarColor(role?: string): string {
  switch (resolveRole(role)) {
    case 'research':   return '#3b82f6';  // blue-500
    case 'content':    return '#a855f7';  // purple-500
    case 'marketing':  return '#ec4899';  // pink-500
    case 'crm':        return '#f97316';  // orange-500
    case 'slack_bot':  return '#14b8a6';  // teal-500
    case 'notion_bot': return '#6366f1';  // indigo-500
    default:           return '#6b7280';  // gray-500
  }
}

/** Role badge background + text color (light/dark variants) */
export function roleBadgeColor(role?: string): string {
  switch (resolveRole(role)) {
    case 'research':   return 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300';
    case 'content':    return 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300';
    case 'marketing':  return 'bg-pink-100 text-pink-700 dark:bg-pink-900/40 dark:text-pink-300';
    case 'crm':        return 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300';
    case 'slack_bot':  return 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300';
    case 'notion_bot': return 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300';
    default:           return 'bg-muted text-muted-foreground';
  }
}

/** Chat message author accent color */
export function authorColor(authorRole?: string): string {
  switch (resolveRole(authorRole)) {
    case 'research':   return 'text-blue-600 dark:text-blue-400';
    case 'content':    return 'text-purple-600 dark:text-purple-400';
    case 'marketing':  return 'text-pink-600 dark:text-pink-400';
    case 'crm':        return 'text-orange-600 dark:text-orange-400';
    case 'slack_bot':  return 'text-teal-600 dark:text-teal-400';
    case 'notion_bot': return 'text-indigo-600 dark:text-indigo-400';
    default:           return 'text-muted-foreground/70';
  }
}

// =============================================================================
// Display name helpers
// =============================================================================

/** Role → user-facing display name (product name) */
export function roleDisplayName(role?: string): string {
  switch (resolveRole(role)) {
    case 'research':   return 'Research Agent';
    case 'content':    return 'Content Agent';
    case 'marketing':  return 'Marketing Agent';
    case 'crm':        return 'CRM Agent';
    case 'slack_bot':  return 'Slack Bot';
    case 'notion_bot': return 'Notion Bot';
    default:           return role || '';
  }
}

/** Short role label for compact displays */
export function roleShortLabel(role?: string): string {
  switch (resolveRole(role)) {
    case 'slack_bot':  return 'Slack';
    case 'notion_bot': return 'Notion';
    default:           return roleDisplayName(role);
  }
}

/** Role → one-line tagline (what it does for the user) */
export function roleTagline(role?: string): string {
  switch (resolveRole(role)) {
    case 'research':   return 'Investigates and analyzes';
    case 'content':    return 'Creates deliverables';
    case 'marketing':  return 'Handles go-to-market';
    case 'crm':        return 'Manages relationships';
    case 'slack_bot':  return 'Reads and writes Slack';
    case 'notion_bot': return 'Reads and writes Notion';
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
