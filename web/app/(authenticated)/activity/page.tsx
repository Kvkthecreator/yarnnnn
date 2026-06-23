/**
 * /activity → /recurrence?recurrence.pane=activity redirect stub (ADR-340 D8).
 *
 * Machinery consolidation: Activity folded to pane-grade under Recurrence —
 * the Runs (execution) lens inside the Recurrence window, no longer a window
 * of its own. The execution-events body is unchanged (now the shared
 * `web/components/activity/ActivityLog.tsx`); only the surface tier moved.
 * Pure server transport per ADR-308 — preserves a stale `?slug=` bookmark
 * so the deep-link lands pre-filtered on the right recurrence.
 */

import { redirect } from 'next/navigation';

export default function ActivityRedirect({
  searchParams,
}: {
  searchParams: { slug?: string };
}) {
  const slug = searchParams?.slug;
  redirect(slug ? `/recurrence?recurrence.pane=activity&recurrence.slug=${encodeURIComponent(slug)}` : '/recurrence?recurrence.pane=activity');
}
