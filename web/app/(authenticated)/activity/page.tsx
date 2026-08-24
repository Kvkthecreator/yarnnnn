/**
 * /activity → /notifications redirect stub (ADR-603 D5, executed 2026-08-24).
 *
 * The Runs lens (pane_of recurrence) is deleted with its parent window. Run
 * receipts live in Notifications' Activity ledger — the `invocation` filter
 * over the same execution_events the lens read.
 *
 * Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function ActivityRedirect() {
  redirect('/notifications?notifications.pane=understand');
}
