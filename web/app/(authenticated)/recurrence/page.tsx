/**
 * /recurrence → /notifications redirect stub (ADR-603 D5, executed 2026-08-24).
 *
 * Recurrences are RETIRED (production counted 0 recurrence declarations —
 * retire-clean). The window this route mounted (Schedule + Runs lenses) is
 * deleted; what survives of "runs" is the receipt, and receipts live in
 * Notifications' Activity ledger (`invocation` kind over execution_events) —
 * ADR-603's own sentence: "runs stop being a concept: receipts surface in
 * notifications." Standing work is the standing declaration (strings today),
 * read at its own desk.
 *
 * This stub also keeps /recurrence AUTHENTICATED: middleware derives its
 * protected set from the served roster, and the slug left the roster — the
 * hand-listed LEGACY_AND_STUB_PREFIXES entry is the other half (ADR-592).
 *
 * Pure server transport per ADR-308 — `redirect()`, never a client-side
 * useEffect redirect (which would paint an orphaned frame inside the shell).
 */

import { redirect } from 'next/navigation';

export default function RecurrenceRedirect() {
  redirect('/notifications?notifications.pane=understand');
}
