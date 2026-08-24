/**
 * /overview — redirect stub (ADR-205 F2; re-pointed 2026-08-24).
 *
 * The Overview surface dissolved into /work (ADR-205 F2), which /recurrence
 * absorbed (ADR-297) and ADR-603 D5 retired. The bookmark's nearest live
 * answer to "what is this workspace doing" is Notifications.
 *
 * Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function OverviewRedirect() {
  redirect('/notifications');
}
