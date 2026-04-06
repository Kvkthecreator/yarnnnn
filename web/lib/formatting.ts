/**
 * Shared formatting utilities — SURFACE-ARCHITECTURE.md v7.
 *
 * Single source of truth for timestamp formatting and freshness classification.
 * Replaces duplicate implementations in AgentContentView, AgentDashboard,
 * ContentViewer, and other components.
 */

/** Relative time string: "just now", "3h ago", "2d ago", "in 1h" */
export function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const future = diff < 0;
  const absDiff = Math.abs(diff);
  const mins = Math.floor(absDiff / 60000);
  if (mins < 1) return future ? 'soon' : 'just now';
  if (mins < 60) return future ? `in ${mins}m` : `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return future ? `in ${hours}h` : `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return future ? `in ${days}d` : `${days}d ago`;
  const weeks = Math.floor(days / 7);
  return future ? `in ${weeks}w` : `${weeks}w ago`;
}

/** Short relative: "just now", "3h ago", "2d ago", "1w ago" */
export function formatShort(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return 'just now';
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return `${Math.floor(days / 7)}w ago`;
}

/** Detailed timestamp for file viewers: "Apr 6, 2026, 3:45 PM" or relative */
export function formatTimestamp(value?: string, detailed = false): string {
  if (!value) return '\u2014';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  if (detailed) {
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  }

  // Relative for recent, absolute for old
  const diff = Date.now() - date.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `${weeks}w ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

/** Freshness classification for visual indicators */
export type Freshness = 'new' | 'recent' | 'stale';

export function getFreshness(updatedAt?: string): Freshness {
  if (!updatedAt) return 'stale';
  const hours = (Date.now() - new Date(updatedAt).getTime()) / 3600000;
  if (hours < 1) return 'new';
  if (hours < 24) return 'recent';
  return 'stale';
}
