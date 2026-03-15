/**
 * ADR-086: Sync error categorization.
 *
 * Translates raw backend error strings into user-friendly labels and
 * actionable guidance. Used by ResourceRow to display sync errors.
 */

export interface CategorizedError {
  /** Short user-facing label (e.g. "Token expired") */
  label: string;
  /** One-line guidance on how to fix */
  hint: string;
  /** Severity drives visual treatment */
  severity: 'warning' | 'error';
}

interface ErrorPattern {
  test: (raw: string) => boolean;
  result: CategorizedError;
}

const ERROR_PATTERNS: ErrorPattern[] = [
  {
    test: (s) => /token.*(expired|revoked|invalid)|401|unauthorized/i.test(s),
    result: {
      label: 'Token expired',
      hint: 'Reconnect the platform to refresh access.',
      severity: 'error',
    },
  },
  {
    test: (s) => /rate.?limit|429|too many requests|retry.?after/i.test(s),
    result: {
      label: 'Rate limited',
      hint: 'Will retry automatically on next sync cycle.',
      severity: 'warning',
    },
  },
  {
    test: (s) => /forbidden|403|access.?denied|not.?allowed|permission/i.test(s),
    result: {
      label: 'Access denied',
      hint: 'Check that the integration has permission to this source.',
      severity: 'error',
    },
  },
  {
    test: (s) => /not.?found|404|deleted|archived/i.test(s),
    result: {
      label: 'Source not found',
      hint: 'The source may have been deleted or archived.',
      severity: 'warning',
    },
  },
  {
    test: (s) => /timeout|timed?.?out|deadline|ETIMEDOUT|ECONNRESET/i.test(s),
    result: {
      label: 'Timeout',
      hint: 'Will retry automatically on next sync cycle.',
      severity: 'warning',
    },
  },
  {
    test: (s) => /network|connect|ENOTFOUND|ECONNREFUSED|fetch failed/i.test(s),
    result: {
      label: 'Connection failed',
      hint: 'Platform may be temporarily unavailable.',
      severity: 'warning',
    },
  },
  {
    test: (s) => /500|502|503|504|internal.?server|service.?unavailable/i.test(s),
    result: {
      label: 'Platform error',
      hint: 'The platform returned a server error. Will retry.',
      severity: 'warning',
    },
  },
];

const FALLBACK: CategorizedError = {
  label: 'Sync error',
  hint: 'Will retry on next sync cycle.',
  severity: 'warning',
};

/**
 * Categorize a raw sync error string into a user-friendly label + hint.
 */
export function categorizeSyncError(raw: string | null | undefined): CategorizedError | null {
  if (!raw) return null;
  const match = ERROR_PATTERNS.find((p) => p.test(raw));
  return match ? match.result : FALLBACK;
}
