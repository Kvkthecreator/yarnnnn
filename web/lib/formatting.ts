/**
 * Shared formatting utilities — SURFACE-ARCHITECTURE.md v7.
 *
 * Single source of truth for timestamp formatting and freshness classification.
 * Replaces duplicate implementations in AgentContentView, AgentDashboard,
 * ContentViewer, and other components.
 */

/**
 * Relative time string: "just now", "3h ago", "2d ago", "in 1h".
 *
 * With `{ rollToDate: true }`, anything a week or older reads as an absolute
 * short date ("Mar 12") instead of "5w ago" — the recency-then-date grammar
 * that list rows (recent files, revisions, connectors) want.
 */
export function formatRelativeTime(
  value?: string | Date | null,
  opts: { rollToDate?: boolean } = {},
): string {
  if (!value) return '';
  const then = (value instanceof Date ? value : new Date(value)).getTime();
  if (Number.isNaN(then)) return '';
  const diff = Date.now() - then;
  const future = diff < 0;
  const absDiff = Math.abs(diff);
  const mins = Math.floor(absDiff / 60000);
  if (mins < 1) return future ? 'soon' : 'just now';
  if (mins < 60) return future ? `in ${mins}m` : `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return future ? `in ${hours}h` : `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return future ? `in ${days}d` : `${days}d ago`;
  if (opts.rollToDate && !future) {
    return new Date(then).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }
  const weeks = Math.floor(days / 7);
  return future ? `in ${weeks}w` : `${weeks}w ago`;
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

/**
 * Day-separator label for a conversation surface — ALWAYS an explicit date,
 * never a vague "1d ago". Matches the ChatGPT/Claude/Gemini grammar:
 * "Today" / "Yesterday" / a weekday this week / an absolute date otherwise.
 */
export function formatDaySeparator(value?: string | Date | null): string {
  if (!value) return '';
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return '';

  const now = new Date();
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const dayDiff = Math.round((startOfDay(now) - startOfDay(date)) / 86_400_000);

  if (dayDiff === 0) return 'Today';
  if (dayDiff === 1) return 'Yesterday';
  if (dayDiff > 1 && dayDiff < 7) {
    return date.toLocaleDateString(undefined, { weekday: 'long' });
  }
  const sameYear = date.getFullYear() === now.getFullYear();
  return date.toLocaleDateString(
    undefined,
    sameYear
      ? { month: 'short', day: 'numeric' }
      : { month: 'short', day: 'numeric', year: 'numeric' },
  );
}

/** Time-of-day for a single message: "10:44 AM". Locale-aware. */
export function formatMessageTime(value?: string | Date | null): string {
  if (!value) return '';
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
}

/**
 * Full absolute timestamp — "Jun 26, 2026, 10:44 AM". The exact value shown
 * on hover (as a `title=`) on every relative/short/separator label, so the
 * precise time is always one hover away without cluttering the surface.
 */
export function formatAbsolute(value?: string | Date | null): string {
  if (!value) return '';
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

/**
 * Ledger-row timestamp — "Jun 26, 10:44 AM" (no year unless it differs). For
 * log-style surfaces (Activity, Notifications) that show an explicit inline
 * date+time per row rather than the conversation day-separator grammar.
 */
export function formatLedgerTime(value?: string | Date | null): string {
  if (!value) return '';
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const sameYear = date.getFullYear() === new Date().getFullYear();
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    ...(sameYear ? {} : { year: 'numeric' }),
    hour: 'numeric',
    minute: '2-digit',
  });
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
