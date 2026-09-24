'use client';

/**
 * useRunWords — a run, worded (ADR-666). ONE hook so the roster row, the
 * detail, the cockpit and the tray cannot drift into four spellings of how a
 * run went. Every word is a catalog key; this only chooses which.
 *
 * `outcomeLine` is the three-way refusal renderer the standing row always had
 * (an honest refusal reads as what it is, never as "failed"), re-derived from
 * a RUN's `state` + `outcome` instead of a cost-ledger row's status.
 */

import { useTranslations } from 'next-intl';
import type { Run } from '@/lib/api/client';

/** Outcomes the catalog names; any other failure reads "Run failed — {reason}". */
const NAMED_FAILURES: Record<string, string> = {
  shape_violation: 'shapeViolation',
  no_sources_fetched: 'noSourcesFetched',
  balance_exhausted: 'balanceExhausted',
  output_truncated: 'outputTruncated',
  router_disabled: 'routerDisabled',
  not_started: 'notStarted',
  turn_failed: 'turnFailed',
};

export function useRunWords() {
  const t = useTranslations('supervisor.lastRun');
  const tr = useTranslations('runs');

  /** How an ENDED run went, in one line. */
  const outcomeLine = (r: Run): string => {
    if (r.state === 'stopped') return t('stopped');
    if (r.state === 'done') {
      if (r.outcome === 'no_change') return t('noChange');
      if (r.outcome === 'skipped') return t('sourcesUnchanged');
      return r.kind === 'browser' && !r.topic ? tr('state.done') : t('success');
    }
    if (r.state === 'failed') {
      const key = r.outcome ? NAMED_FAILURES[r.outcome] : undefined;
      if (key) return t(key);
      return r.outcome ? t('failedWithReason', { reason: r.outcome }) : t('failed');
    }
    return tr(`state.${r.state}`);
  };

  /** The run's state word — the badge's label. */
  const stateWord = (r: Run): string => tr(`state.${r.state}`);

  /** Who it runs as, for the viewer: "in Kevin's browser" / "Kevin". */
  const whoLine = (r: Run): string => {
    const name = r.member_name || tr('someone');
    return r.kind === 'browser' ? tr('inBrowserOf', { name }) : tr('byMember', { name });
  };

  return { outcomeLine, stateWord, whoLine };
}
