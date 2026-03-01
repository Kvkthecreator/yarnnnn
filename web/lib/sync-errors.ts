/**
 * Sync error categorization (ADR-086).
 *
 * Maps raw error strings from sync_registry.last_error
 * to user-friendly messages.
 */

interface SyncErrorCategory {
  label: string;
  description: string;
  actionable: boolean;
  action?: string;
}

const ERROR_PATTERNS: Array<{ test: RegExp; category: SyncErrorCategory }> = [
  {
    test: /token.refresh.fail|invalid_grant|401|unauthorized/i,
    category: {
      label: 'Reconnect needed',
      description: 'The connection credentials have expired.',
      actionable: true,
      action: 'reconnect',
    },
  },
  {
    test: /rate.limit|429|too.many.requests|ratelimit/i,
    category: {
      label: 'Temporarily limited',
      description: 'The platform is rate-limiting requests. Will auto-resolve.',
      actionable: false,
    },
  },
  {
    test: /timeout|timed?.out|connect(ion)?.error|network|ECONNREFUSED|ENOTFOUND/i,
    category: {
      label: 'Sync interrupted',
      description: 'A network issue interrupted the sync. Will retry automatically.',
      actionable: false,
    },
  },
  {
    test: /not_in_channel|channel_not_found|missing_scope|forbidden|403/i,
    category: {
      label: 'Access denied',
      description: 'The app no longer has access to this source.',
      actionable: true,
      action: 'reconnect',
    },
  },
];

const FALLBACK_CATEGORY: SyncErrorCategory = {
  label: 'Sync error',
  description: 'An unexpected error occurred. Will retry on next sync.',
  actionable: false,
};

export function categorizeSyncError(rawError: string | null): SyncErrorCategory | null {
  if (!rawError) return null;

  for (const { test, category } of ERROR_PATTERNS) {
    if (test.test(rawError)) return category;
  }

  return FALLBACK_CATEGORY;
}
