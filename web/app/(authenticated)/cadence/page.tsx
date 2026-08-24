/**
 * Legacy /cadence route — was renamed to /recurrence (2026-06-03), whose
 * window is retired in full (ADR-603 D5, 2026-08-24). Standing work is read
 * in Notifications; "cadence" survives only as a temporal-classification
 * concept, not a route.
 *
 * Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function CadenceRedirect() {
  redirect('/notifications');
}
