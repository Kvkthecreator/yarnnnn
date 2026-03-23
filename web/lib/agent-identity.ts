/**
 * Agent Identity — shared visual identity system for agents.
 *
 * Single source of truth for agent colors, display names, badges, and initials.
 * Used by AgentAvatar, project pages, agent lists, dashboard, and chat attribution.
 */

// =============================================================================
// Role → Color mapping
// =============================================================================

/** Avatar background hex color by role — inline styles, immune to Tailwind purge */
export function avatarColor(role?: string): string {
  switch (role) {
    case 'pm': return '#9333ea';       // purple-600
    case 'digest': return '#3b82f6';   // blue-500
    case 'monitor': return '#f59e0b';  // amber-500
    case 'research': return '#22c55e'; // green-500
    case 'synthesize': return '#14b8a6'; // teal-500
    case 'prepare': return '#6366f1';  // indigo-500
    case 'act': return '#f43f5e';      // rose-500
    default: return '#6b7280';         // gray-500
  }
}

/** Role badge background + text color (light/dark variants) */
export function roleBadgeColor(role?: string): string {
  switch (role) {
    case 'pm': return 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300';
    case 'digest': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300';
    case 'monitor': return 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300';
    case 'research': return 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300';
    case 'synthesize': return 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300';
    case 'prepare': return 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300';
    case 'act': return 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300';
    default: return 'bg-muted text-muted-foreground';
  }
}

/** Chat message author accent color */
export function authorColor(authorRole?: string): string {
  switch (authorRole) {
    case 'pm': return 'text-purple-600 dark:text-purple-400';
    case 'digest': return 'text-blue-600 dark:text-blue-400';
    case 'monitor': return 'text-amber-600 dark:text-amber-400';
    case 'research': return 'text-green-600 dark:text-green-400';
    case 'synthesize': return 'text-teal-600 dark:text-teal-400';
    case 'prepare': return 'text-indigo-600 dark:text-indigo-400';
    default: return 'text-muted-foreground/70';
  }
}

// =============================================================================
// Display name helpers
// =============================================================================

/** Role → user-facing display name */
export function roleDisplayName(role?: string): string {
  switch (role) {
    case 'pm': return 'Project Manager';
    case 'digest': return 'Recap';
    case 'monitor': return 'Monitor';
    case 'research': return 'Researcher';
    case 'synthesize': return 'Synthesizer';
    case 'prepare': return 'Prep';
    case 'act': return 'Operator';
    case 'custom': return 'Custom';
    default: return role || '';
  }
}

/** Short role label for compact displays */
export function roleShortLabel(role?: string): string {
  switch (role) {
    case 'pm': return 'PM';
    default: return roleDisplayName(role);
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
