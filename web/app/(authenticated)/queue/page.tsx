/**
 * /queue → /reach (Leaving) redirect stub (ADR-642 D4).
 *
 * The Queue surface is ABSORBED by Reach: the proposal body mounts on Reach's
 * Leaving pane, filtered to the two families that cross the workspace
 * boundary (external-write · capital), and on Notifications → To do
 * unfiltered (everything awaiting the viewer). One body, three mounts
 * (ADR-346). The `queue` slug left KERNEL_SURFACES, the FE union, the
 * allowlist and the component registry; this route survives as a bookmark-
 * safe stub and is hand-listed in `lib/supabase/middleware.ts` (the ADR-592
 * obligation — a slug leaving the roster leaves the auth gate with it).
 *
 * Pure server transport per ADR-308: server `redirect()`, never a client
 * `useEffect` redirect.
 */

import { redirect } from 'next/navigation';

export default function QueueRedirect() {
  redirect('/reach?reach.pane=leaving');
}
