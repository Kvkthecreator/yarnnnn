/**
 * /strings → /notifications (Standing work) redirect stub (ADR-639).
 *
 * The Strings app is DELETED (ADR-569 → ADR-639) — its surface, router,
 * service module and the Supervisor agent are gone. Standing work is a
 * kernel lane: the declaration lives beside the kept file, the run is a
 * daemon, the craft is a skill, and the roster + the two direct switches
 * (Run now · Pause) live in the Notifications window's "Standing work" pane.
 *
 * This stub preserves bookmarks and, more importantly, keeps the path
 * AUTHENTICATED: middleware derives its protected set from the served
 * surface roster, so a slug that leaves the roster leaves the gate with it,
 * and a route that still rendered would serve 200 to logged-out visitors
 * (the defect repaired 2026-08-20). Hand-listed in lib/supabase/middleware.ts.
 *
 * Pure server transport per ADR-308 — `redirect()`, never a client-side
 * useEffect redirect (which would paint an orphaned frame inside the shell).
 */

import { redirect } from 'next/navigation';

export default function StringsRedirect() {
  redirect('/notifications?notifications.pane=standing');
}
