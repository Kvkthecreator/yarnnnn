/**
 * /backend redirect stub — renamed to /activity (ADR-265), folded into the
 * Recurrence window (ADR-340 D8), retired with it (ADR-603 D5, 2026-08-24).
 * The activity-audit job lives in Notifications' Activity ledger.
 *
 * Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function BackendRedirect() {
  redirect('/notifications?notifications.pane=understand');
}
