/**
 * Legacy /cadence route — redirects to /recurrence, preserving query params.
 *
 * 2026-06-03: the surface renamed Cadence → Recurrence. The substrate
 * (_recurrences.yaml), hooks (useRecurrenceDetail), and detail logic
 * already spoke "recurrence"; only the surface label/slug/route lagged.
 * The old /cadence URL (and its ?task= / ?agent= deep-links) survives as
 * a bookmark-safety stub. "Cadence" remains a live temporal-classification
 * concept (Recurring vs Reactive grouping) — unrelated to this route.
 *
 * ADR-308 (2026-06-01): pure transport — server redirect(). searchParams
 * arrive as a server-component prop.
 */

import { redirect } from 'next/navigation';

export default function CadenceRedirect({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const qs = new URLSearchParams(searchParams as Record<string, string>).toString();
  redirect(qs ? `/recurrence?${qs}` : '/recurrence');
}
